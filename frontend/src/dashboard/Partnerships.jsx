import { useEffect, useState } from 'react';
import { api } from '../api/client';

/** Show supplier assessments and source-reported quarterly financial history. */
export default function Partnerships({ onSummarize }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.get(`/partnerships?limit=20&offset=${offset}`).then((response) => {
      if (active) setData(response.data);
    }).catch(() => {
      if (active) setError('Unable to load partnerships. Please try again.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [version, offset]);

  const value = (amount, suffix = '') => amount == null ? 'Not provided' : `${amount}${suffix}`;
  return (
    <section className="strategic" aria-labelledby="partnerships-title">
      <p className="eyebrow">Executive dashboard</p>
      <h1 id="partnerships-title">Partnerships</h1>
      <p className="muted">Source-reported supplier assessments and quarterly history.</p>
      {onSummarize && <button type="button" onClick={onSummarize}>Summarize partnerships</button>}
      {loading && <p role="status">Loading partnerships…</p>}
      {error && <div role="alert"><p className="error">{error}</p><button type="button" onClick={() => setVersion((v) => v + 1)}>Retry</button></div>}
      {!loading && !error && data && (data.partners.length === 0 && offset === 0 ? <p>No partnership data available.</p> : (
        <>
          {data.partners.map((partner) => (
            <article className="chart-panel" key={partner.id}>
              <h2>{partner.vendor_name}</h2>
              <p className="muted">Contract: {partner.contract_status} · Review: {partner.review_quarter} · Updated: {partner.updated_at}</p>
              <div className="table-scroll">
                <table>
                  <caption>Current supplier assessment</caption>
                  <thead><tr><th scope="col">SLA compliance</th><th scope="col">Delivery score</th><th scope="col">Innovation output</th><th scope="col">Annual spend</th><th scope="col">ROI multiple</th></tr></thead>
                  <tbody><tr><td>{value(partner.sla_compliance_pct, '%')}</td><td>{value(partner.delivery_score)}</td><td>{value(partner.innovation_output)}</td><td>{partner.currency} {value(partner.annual_spend)}</td><td>{value(partner.roi_multiple, '×')}</td></tr></tbody>
                </table>
              </div>
              <h3>Quarterly spend, verified savings and ROI</h3>
              <p className="muted">Amounts and ROI are supplied independently; missing values are not zero. Currency is shown per period.</p>
              {partner.history.length === 0 ? <p>No quarterly history available.</p> : (
                <div className="table-scroll">
                  <table>
                    <caption>Quarterly spend versus verified savings and ROI for {partner.vendor_name}</caption>
                    <thead><tr><th scope="col">Quarter</th><th scope="col">Currency</th><th scope="col">Spend</th><th scope="col">Verified savings</th><th scope="col">ROI multiple</th></tr></thead>
                    <tbody>{partner.history.map((row) => (
                      <tr key={`${row.year}-${row.quarter}`}><th scope="row">Q{row.quarter} {row.year}</th><td>{row.currency}</td><td>{value(row.spend)}</td><td>{value(row.verified_savings)}</td><td>{value(row.roi_multiple, '×')}</td></tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
              {partner.history_total > partner.history.length && <p className="muted">Showing the latest {partner.history.length} of {partner.history_total} quarters.</p>}
            </article>
          ))}
          <p className="muted">Showing {data.partners.length ? offset + 1 : 0}–{offset + data.partners.length} of {data.total} partners.</p>
          <button type="button" disabled={offset === 0} onClick={() => setOffset((v) => Math.max(0, v - 20))}>Previous partners</button>{' '}
          <button type="button" disabled={offset + data.partners.length >= data.total} onClick={() => setOffset((v) => v + 20)}>Next partners</button>
        </>
      ))}
    </section>
  );
}
