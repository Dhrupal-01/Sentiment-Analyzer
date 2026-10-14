import { useEffect, useMemo, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { apiClient } from '../api/client';
import type { HeadlineItem } from '../api/types';
import { useAsync } from '../lib/data';
import { asLabel, formatDate, formatScore, modelDisplayName } from '../lib/sentiment';
import { Notice, Segmented, SentimentLabel, Skeleton, ValenceMarker } from './primitives';
import {
  METHOD_OPTIONS,
  MarkupLegend,
  TokenMarkup,
  WeightList,
  methodNote,
  type Method,
} from './TokenMarkup';

/**
 * Side panel for one headline: every stored model score, then an explanation drawn on the
 * headline's own words. Explanations are requested with the article id so the API can cache them.
 */
export function HeadlineDrawer({
  headline,
  registeredModels,
  preferredModel,
  onClose,
}: {
  headline: HeadlineItem;
  registeredModels: string[];
  preferredModel?: string;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const predictions = useMemo(
    () =>
      [...(headline.predictions ?? [])].sort((a, b) => a.model_name.localeCompare(b.model_name)),
    [headline]
  );

  const explainable = useMemo(() => {
    const scored = predictions.map((p) => p.model_name).filter((m) => registeredModels.includes(m));
    return scored.length > 0 ? scored : registeredModels;
  }, [predictions, registeredModels]);

  const [model, setModel] = useState<string>(() =>
    preferredModel && explainable.includes(preferredModel)
      ? preferredModel
      : (explainable[0] ?? 'vader')
  );
  const [method, setMethod] = useState<Method>('occlusion');

  const explanation = useAsync(
    () => apiClient.explain({ text: headline.title, model, method, article_id: headline.id }),
    [headline.id, headline.title, model, method]
  );

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
      previous?.focus?.();
    };
  }, [onClose]);

  const hasLink = /^https?:\/\//.test(headline.url) && !/\.internal\//.test(headline.url);

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <div className="drawer__top">
          <span>Headline {headline.id}</span>
          <button
            ref={closeRef}
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close headline"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div className="drawer__body">
          <h2 id="drawer-title" className="drawer__title">
            {headline.title}
          </h2>
          <div className="drawer__meta">
            <span>{headline.outlet ?? 'Unknown outlet'}</span>
            <span>{formatDate(headline.published_at)}</span>
            <span>Collected via {headline.provider}</span>
            {hasLink ? (
              <a href={headline.url} target="_blank" rel="noopener noreferrer">
                Open article
              </a>
            ) : null}
          </div>

          <section className="drawer__section">
            <h3>How each model scored it</h3>
            <p className="drawer__lede">
              Scores run from −1 (most negative) to +1 (most positive).
            </p>
            {predictions.length === 0 ? (
              <Notice title="Not scored yet">
                No model has scored this headline. Run <code>newsent analyze --model vader</code> to
                add scores.
              </Notice>
            ) : (
              <ul className="model-scores">
                {predictions.map((p) => {
                  const label = asLabel(p.label);
                  return (
                    <li key={p.model_name}>
                      <span className="model-scores__name">{modelDisplayName(p.model_name)}</span>
                      <SentimentLabel label={label} />
                      <ValenceMarker score={p.score} label={label} width={170} />
                      <span className="num" style={{ textAlign: 'right' }}>
                        {formatScore(p.score)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section className="drawer__section">
            <h3>Why the model gave this score</h3>
            <p className="drawer__lede">Each word is shaded by how much it moved the score.</p>
            <div className="explain-controls">
              <label className="field">
                Model
                <select className="select" value={model} onChange={(e) => setModel(e.target.value)}>
                  {explainable.map((name) => (
                    <option key={name} value={name}>
                      {modelDisplayName(name)}
                    </option>
                  ))}
                </select>
              </label>
              <div className="field">
                Method
                <Segmented
                  label="Explanation method"
                  options={METHOD_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
                  value={method}
                  onChange={setMethod}
                />
              </div>
            </div>

            {explanation.loading ? (
              <div style={{ display: 'grid', gap: 10 }}>
                <Skeleton height={30} />
                <Skeleton height={30} width="70%" />
              </div>
            ) : explanation.error ? (
              <Notice
                tone="error"
                title={`${modelDisplayName(model)} could not explain this headline`}
              >
                {explanation.error} This usually means the model is not installed on the API server.
              </Notice>
            ) : explanation.data ? (
              <>
                <TokenMarkup text={headline.title} attributions={explanation.data.attributions} />
                <MarkupLegend />
                <WeightList attributions={explanation.data.attributions} />
                <p className="method-note">
                  {methodNote(method, model)} Model score for this headline:{' '}
                  <span className="num">{formatScore(explanation.data.prediction_score)}</span>.
                </p>
              </>
            ) : null}
          </section>
        </div>
      </aside>
    </>
  );
}
