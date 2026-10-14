import { useEffect, useRef, useState, type FormEvent } from 'react';
import { apiClient } from '../api/client';
import type { TopicResponse } from '../api/types';
import { errorMessage } from '../lib/data';

export function NewTopicDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (topic: TopicResponse) => void;
}) {
  const [name, setName] = useState('');
  const [query, setQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    nameRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim() || !query.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const topic = await apiClient.createTopic({
        name: name.trim(),
        query: query.trim(),
        is_active: true,
      });
      onCreated(topic);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="new-topic-title">
        <h2 id="new-topic-title">Add a topic</h2>
        <form onSubmit={submit}>
          <label className="field">
            Name
            <input
              ref={nameRef}
              className="input"
              value={name}
              maxLength={100}
              onChange={(e) => setName(e.target.value)}
              placeholder="Energy"
              required
            />
          </label>
          <label className="field">
            Search words
            <input
              className="input"
              value={query}
              maxLength={255}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="oil gas renewables"
              required
            />
          </label>
          <p className="dialog__hint">
            Headlines are collected for this topic the next time collection runs, for example with{' '}
            <code>newsent collect</code>.
          </p>
          {error ? (
            <p className="dialog__hint" role="alert" style={{ color: 'var(--danger-ink)' }}>
              {error}
            </p>
          ) : null}
          <div className="dialog__actions">
            <button type="button" className="button button--quiet" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="button button--primary" disabled={saving}>
              {saving ? 'Adding topic…' : 'Add topic'}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
