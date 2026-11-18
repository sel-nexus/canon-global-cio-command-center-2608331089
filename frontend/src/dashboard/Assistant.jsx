import { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { api } from '../api/client';

/** Offer contextual starter questions and an accessible assistant drawer. */
export default function Assistant({ tab, launch, onLaunchHandled }) {
  const [open, setOpen] = useState(false);
  const [prompts, setPrompts] = useState([]);
  const [promptError, setPromptError] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const dialog = useRef(null);
  const trigger = useRef(null);
  const sequence = useRef(0);

  useEffect(() => {
    let active = true;
    setPrompts([]);
    setPromptError('');
    setResult(null);
    setError('');
    sequence.current += 1;
    setPending(false);
    api.get('/ai/recommendations', { params: { context_tab: tab } }).then(({ data }) => {
      if (active) setPrompts(data);
    }).catch(() => { if (active) setPromptError('Suggested questions are unavailable.'); });
    return () => { active = false; };
  }, [tab]);

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.current?.querySelector('button')?.focus();
    function keys(event) {
      if (event.key === 'Escape') setOpen(false);
      if (event.key !== 'Tab') return;
      const items = [...dialog.current.querySelectorAll('button:not([disabled]), textarea:not([disabled])')];
      if (!items.length) return;
      if (event.shiftKey && document.activeElement === items[0]) { event.preventDefault(); items[items.length - 1].focus(); }
      else if (!event.shiftKey && document.activeElement === items[items.length - 1]) { event.preventDefault(); items[0].focus(); }
    }
    document.addEventListener('keydown', keys);
    return () => { document.removeEventListener('keydown', keys); document.body.style.overflow = oldOverflow; previous?.focus(); };
  }, [open]);

  async function ask(question, contextTab = tab) {
    if (!question.trim()) return;
    const id = ++sequence.current;
    setOpen(true);
    setQuery(question);
    setPending(true);
    setResult(null);
    setError('');
    try {
      const response = await api.post('/ai/chat', { query: question, context_tab: contextTab });
      if (sequence.current === id) setResult(response.data);
    } catch (failure) {
      if (sequence.current === id) setError(failure.response?.data?.detail || 'Assistant request failed. Please try again.');
    } finally { if (sequence.current === id) setPending(false); }
  }

  useEffect(() => {
    if (launch) { ask(launch.query, launch.tab); onLaunchHandled(); }
  }, [launch]);

  return (
    <>
      {tab === 'strategic' && <section aria-label="Suggested assistant questions">
        <h2>Suggested questions</h2>
        {promptError && <p className="muted">{promptError}</p>}
        {prompts.map((item) => (
          <button key={item.query} className="assistant-prompt" type="button" onClick={() => ask(item.query, item.context_tab)}>
            {item.label}
          </button>
        ))}
      </section>}
      <button ref={trigger} type="button" className="assistant-launch" onClick={() => setOpen(true)}>Executive assistant</button>
      {open && <div className="assistant-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
        <aside ref={dialog} className="assistant-drawer" role="dialog" aria-modal="true" aria-labelledby="assistant-title">
          <button type="button" className="assistant-close" onClick={() => setOpen(false)}>Close assistant</button>
          <h2 id="assistant-title">Executive assistant</h2>
          <p className="muted">
            Context: {tab}. In provider mode, questions and limited dashboard data are sent to the configured provider.
            Do not enter personal information or credentials.
          </p>
          <h3>Suggested follow-up</h3>
          {promptError && <p className="muted">{promptError}</p>}
          {prompts.map((item) => (
            <button
              key={item.query} type="button" className="assistant-prompt" disabled={pending}
              onClick={() => ask(item.query, item.context_tab)}
            >
              {item.label}
            </button>
          ))}
          <form onSubmit={(event) => { event.preventDefault(); ask(query); }}>
            <label htmlFor="assistant-query">Your question</label>
            <textarea id="assistant-query" value={query} onChange={(event) => setQuery(event.target.value)} maxLength={1000} required rows={4} />
            <button type="submit" disabled={pending || !query.trim()}>{pending ? 'Analyzing…' : 'Ask assistant'}</button>
          </form>
          {pending && <p role="status">Waiting for assistant response…</p>}
          {error && <p role="alert" className="error">{error}</p>}
          {result && <div aria-live="polite">
            <p><strong>
              {result.source === 'mock' ? 'MOCK / synthetic output — not an analysis of dashboard data.'
                : result.source === 'provider' ? 'Source: AI provider' : 'Source: unknown'}
            </strong></p>
            <h3>Analysis</h3><p>{result.narrative}</p>
            <h3>Suggested actions</h3>
            {result.actions.length
              ? <ul>{result.actions.map((action, index) => <li key={index}>{action}</li>)}</ul>
              : <p>No actions supplied.</p>}
            <p>Confidence: {result.confidence ?? 'Not supplied'}</p>
            <h3>Limitations</h3><ul>{result.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>}
        </aside>
      </div>}
    </>
  );
}

Assistant.propTypes = {
  tab: PropTypes.string.isRequired,
  launch: PropTypes.shape({ query: PropTypes.string, tab: PropTypes.string }),
  onLaunchHandled: PropTypes.func.isRequired,
};
