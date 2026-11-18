import { useEffect, useState } from 'react';
import { api } from '../api/client';

/** Display the latest source-reported risk assessment. */
export default function Governance() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.get('/governance/risk-overview')
      .then((response) => { if (active) setData(response.data); })
      .catch(() => { if (active) setError('Unable to load risk assessment. Please try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [version]);

  const latest = data?.latest;
  return (
    <section className="strategic" aria-labelledby="governance-title">
      <p className="eyebrow">Executive dashboard</p>
      <h1 id="governance-title">Risk &amp; Governance</h1>
      <p className="muted">Source-reported regulatory, cybersecurity and privacy posture.</p>
      {loading && <p role="status">Loading risk assessment…</p>}
      {error && <div role="alert"><p className="error">{error}</p><button type="button" onClick={() => setVersion((v) => v + 1)}>Retry</button></div>}
      {!loading && !error && !latest && <p>No risk assessment available.</p>}
      {!loading && !error && latest && (
        <>
          <p className="muted">Reporting date: {latest.recorded_date} · Updated: {latest.updated_at}</p>
          <div className="metric-grid">
            <article className="metric-card"><h2>Global Regulatory Compliance Score</h2><p className="metric-value">{latest.compliance_pct == null ? 'Not provided' : `${latest.compliance_pct}%`}</p></article>
            <article className="metric-card"><h2>Cybersecurity Maturity (NIST)</h2><p className="metric-value">{latest.nist_maturity ?? 'Not provided'}</p></article>
            <article className="metric-card"><h2>Data Privacy Audit Status</h2><p className="metric-value">{latest.privacy_audit_status ?? 'Not provided'}</p></article>
          </div>
        </>
      )}
    </section>
  );
}
