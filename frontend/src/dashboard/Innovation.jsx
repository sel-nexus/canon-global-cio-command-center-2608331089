import { useEffect, useState } from 'react';
import { api } from '../api/client';

/** Display source-reported innovation outcomes and portfolio amounts. */
export default function Innovation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.get('/governance/innovation')
      .then((response) => { if (active) setData(response.data); })
      .catch(() => { if (active) setError('Unable to load innovation data. Please try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [version]);

  const latest = data?.latest;
  const portfolio = data?.portfolio || [];
  return (
    <section className="strategic" aria-labelledby="innovation-title">
      <p className="eyebrow">Executive dashboard</p>
      <h1 id="innovation-title">Innovation</h1>
      <p className="muted">Source-reported portfolio and innovation outcomes.</p>
      {loading && <p role="status">Loading innovation data…</p>}
      {error && <div role="alert"><p className="error">{error}</p><button type="button" onClick={() => setVersion((v) => v + 1)}>Retry</button></div>}
      {!loading && !error && data && (
        <>
          <h2>Innovation outcomes</h2>
          {latest ? <>
            <p className="muted">Reporting period: Q{latest.quarter} {latest.year} · Updated: {latest.updated_at}</p>
            <div className="metric-grid">
              <article className="metric-card"><h2>AI models deployed to production</h2><p className="metric-value">{latest.deployed_models ?? 'Not provided'}</p></article>
              <article className="metric-card"><h2>Patent disclosures filed</h2><p className="metric-value">{latest.patent_disclosures ?? 'Not provided'}</p></article>
              <article className="metric-card"><h2>Quarterly innovation index</h2><p className="metric-value">{latest.innovation_index ?? 'Not provided'}</p></article>
            </div>
          </> : <p>No innovation outcomes available.</p>}
          <h2>Innovation portfolio</h2>
          {portfolio.length ? <div className="table-scroll">
            <table>
              <caption>Source-reported portfolio · Q{portfolio[0].quarter} {portfolio[0].year}</caption>
              <thead><tr><th scope="col">Category</th><th scope="col">Amount</th><th scope="col">Unit</th><th scope="col">Updated</th></tr></thead>
              <tbody>{portfolio.map((row) => <tr key={row.category}><th scope="row">{row.category}</th><td>{row.amount}</td><td>{row.unit}</td><td>{row.updated_at}</td></tr>)}</tbody>
            </table>
            <p className="muted">Only supplied categories are shown; missing categories are not zero.</p>
          </div> : <p>No innovation portfolio available.</p>}
        </>
      )}
    </section>
  );
}
