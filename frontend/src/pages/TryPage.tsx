import { useEffect, useRef, useState, type FormEvent } from 'react';
import { apiClient } from '../api/client';
import type { ExplainResponse, ModelPredictionItem } from '../api/types';
import {
  Notice,
  Segmented,
  SentimentLabel,
  Skeleton,
  ValenceMarker,
} from '../components/primitives';
import {
  METHOD_OPTIONS,
  MarkupLegend,
  TokenMarkup,
  WeightList,
  methodNote,
  type Method,
} from '../components/TokenMarkup';
import { errorMessage } from '../lib/data';
import { LABELS, LABEL_TEXT, asLabel, formatScore, modelDisplayName } from '../lib/sentiment';

/** Headlines chosen to show where models tend to disagree: negation, jargon, mixed news. */
export const EXAMPLES = [
  'Not a bad quarter for the regional bank',
  'Bond yields climb as traders price in another rate hike',
  'Airline cuts 2,000 jobs despite record summer bookings',
  'Death toll rises to 40 after floods hit coastal province',
  'Chipmaker shares soar after it beats revenue forecasts',
];

interface Reading {
  model: string;
  status: 'loading' | 'done' | 'failed';
  prediction?: ModelPredictionItem;
  explanation?: ExplainResponse;
  explanationError?: string;
  error?: string;
}

export default function TryPage({ registeredModels }: { registeredModels: string[] }) {
  const [text, setText] = useState('');
  const [selected, setSelected] = useState<string[]>(registeredModels);
  const [method, setMethod] = useState<Method>('occlusion');
  const [readings, setReadings] = useState<Reading[]>([]);
  const [analyzedText, setAnalyzedText] = useState('');
  const runId = useRef(0);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setSelected((current) => (current.length === 0 ? registeredModels : current));
  }, [registeredModels]);

  useEffect(() => {
    const element = inputRef.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = `${element.scrollHeight}px`;
  }, [text]);

  const explainAll = async (headline: string, models: string[], how: Method, id: number) => {
    await Promise.all(
      models.map(async (model) => {
        try {
          const explanation = await apiClient.explain({ text: headline, model, method: how });
          if (id !== runId.current) return;
          setReadings((rows) =>
            rows.map((r) =>
              r.model === model ? { ...r, explanation, explanationError: undefined } : r
            )
          );
        } catch (err) {
          if (id !== runId.current) return;
          setReadings((rows) =>
            rows.map((r) => (r.model === model ? { ...r, explanationError: errorMessage(err) } : r))
          );
        }
      })
    );
  };

  const analyze = async (headline: string) => {
    const trimmed = headline.trim();
    if (!trimmed || selected.length === 0) return;
    const id = ++runId.current;
    const models = registeredModels.filter((m) => selected.includes(m));
    setAnalyzedText(trimmed);
    setReadings(models.map((model) => ({ model, status: 'loading' })));

    // One request per model, so a model the server cannot run does not hide the others.
    const working: string[] = [];
    await Promise.all(
      models.map(async (model) => {
        try {
          const response = await apiClient.analyze({ texts: [trimmed], models: [model] });
          const prediction = response.results[0]?.predictions[model];
          if (id !== runId.current) return;
          if (!prediction) throw new Error(`The API returned no score for ${model}.`);
          working.push(model);
          setReadings((rows) =>
            rows.map((r) => (r.model === model ? { ...r, status: 'done', prediction } : r))
          );
        } catch (err) {
          if (id !== runId.current) return;
          setReadings((rows) =>
            rows.map((r) =>
              r.model === model ? { ...r, status: 'failed', error: errorMessage(err) } : r
            )
          );
        }
      })
    );
    if (id === runId.current && working.length > 0) {
      await explainAll(trimmed, working, method, id);
    }
  };

  const changeMethod = (next: Method) => {
    setMethod(next);
    if (!analyzedText) return;
    const id = ++runId.current;
    const working = readings.filter((r) => r.status === 'done').map((r) => r.model);
    setReadings((rows) =>
      rows.map((r) => ({ ...r, explanation: undefined, explanationError: undefined }))
    );
    void explainAll(analyzedText, working, next, id);
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void analyze(text);
  };

  const toggle = (model: string) =>
    setSelected((current) =>
      current.includes(model) ? current.filter((m) => m !== model) : [...current, model]
    );

  const failed = readings.filter((r) => r.status === 'failed');
  const shown = readings.filter((r) => r.status !== 'failed');

  return (
    <div className="page">
      <header className="page-head">
        <h1>Try a headline</h1>
        <p>
          Type any headline and see how each model scores it, and which words pushed the score up or
          down.
        </p>
      </header>

      <form className="composer" onSubmit={onSubmit}>
        <label htmlFor="headline-input" className="visually-hidden">
          Headline
        </label>
        <textarea
          id="headline-input"
          ref={inputRef}
          className="composer__input"
          rows={1}
          maxLength={1000}
          placeholder="Type or paste a headline"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              void analyze(text);
            }
          }}
        />
        <div className="composer__examples" aria-label="Example headlines">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              className="chip"
              onClick={() => {
                setText(example);
                void analyze(example);
              }}
            >
              {example}
            </button>
          ))}
        </div>
        <div className="composer__controls">
          <div className="toolbar">
            <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
              <legend style={{ padding: 0, marginBottom: 5 }}>Models</legend>
              <div className="checks">
                {registeredModels.map((model) => (
                  <label key={model} className="check">
                    <input
                      type="checkbox"
                      checked={selected.includes(model)}
                      onChange={() => toggle(model)}
                    />
                    {modelDisplayName(model)}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="field">
              Explanation
              <Segmented
                label="Explanation method"
                options={METHOD_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
                value={method}
                onChange={changeMethod}
              />
            </div>
          </div>
          <button
            type="submit"
            className="button button--primary"
            disabled={!text.trim() || selected.length === 0}
          >
            Score headline
          </button>
        </div>
      </form>

      {readings.length > 0 ? (
        <section className="readings" aria-live="polite" aria-label="Model readings">
          {shown.map((reading) => (
            <ReadingCard
              key={reading.model}
              reading={reading}
              text={analyzedText}
              method={method}
            />
          ))}
          {failed.length > 0 ? (
            <div className="reading reading--muted">
              <strong>
                {failed.map((r) => modelDisplayName(r.model)).join(', ')}{' '}
                {failed.length === 1 ? 'is' : 'are'} not available on this server
              </strong>
              <p>
                The API could not run {failed.length === 1 ? 'this model' : 'these models'}.
                Transformer models need the optional machine-learning packages, installed with{' '}
                <code>pip install -e ".[ml]"</code>. The fine-tuned model also needs its trained
                weights.
              </p>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

function ReadingCard({
  reading,
  text,
  method,
}: {
  reading: Reading;
  text: string;
  method: Method;
}) {
  if (reading.status === 'loading' || !reading.prediction) {
    return (
      <article className="reading" aria-busy="true">
        <div className="reading__head">
          <span className="reading__model">{modelDisplayName(reading.model)}</span>
        </div>
        <Skeleton height={34} />
      </article>
    );
  }
  const { prediction } = reading;
  const label = asLabel(prediction.label);
  return (
    <article className="reading">
      <div className="reading__head">
        <div>
          <div className="reading__model">{modelDisplayName(reading.model)}</div>
          <div className="reading__version">{prediction.model_version}</div>
        </div>
        <div className="reading__score">
          <SentimentLabel label={label} />
          <span className="num">{formatScore(prediction.score)}</span>
          <ValenceMarker score={prediction.score} label={label} width={160} />
        </div>
        <p className="reading__probs num">
          <span>{reading.model === 'vader' ? 'Share of words' : 'Probability'}</span>
          {LABELS.map((l) => (
            <span key={l}>
              {LABEL_TEXT[l]}{' '}
              <strong>{((prediction.probabilities[l] ?? 0) * 100).toFixed(0)}%</strong>
            </span>
          ))}
        </p>
      </div>

      {reading.explanation ? (
        <>
          <TokenMarkup text={text} attributions={reading.explanation.attributions} compact />
          <MarkupLegend />
          <WeightList attributions={reading.explanation.attributions} count={4} />
          <p className="method-note">{methodNote(method, reading.model)}</p>
        </>
      ) : reading.explanationError ? (
        <Notice tone="error" title="No explanation for this model">
          {reading.explanationError}
        </Notice>
      ) : (
        <Skeleton height={30} />
      )}
    </article>
  );
}
