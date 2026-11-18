import { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { api } from '../api/client';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

/** Show source-provided quarterly business outcomes without calculating ROI. */
export default function Business() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.get('/business/impact').then((response) => {
      if (active) setData(response.data);
    }).catch(() => {
      if (active) setError('Unable to load business impact. Please try again.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [version]);

  const quarters = data?.quarters || [];
  const latest = quarters[quarters.length - 1];
  const value = (amount, unit) => amount == null ? 'Not provided' : `${amount}${unit}`;
  const chart = {
    labels: quarters.map((row) => `Q${row.quarter} ${row.year}`),
    datasets: [
      { label: 'IT Investment', data: quarters.map((row) => row.investment_m == null ? null : Number(row.investment_m)), backgroundColor: '#a5a0a0' },
      { label: 'Revenue Attribution', data: quarters.map((row) => row.revenue_attribution_m == null ? null : Number(row.revenue_attribution_m)), backgroundColor: '#e7847e' },
      { label: 'Cost Avoidance', data: quarters.map((row) => row.cost_avoidance_m == null ? null : Number(row.cost_avoidance_m)), backgroundColor: '#7c7777' },
    ],
  };
  const options = { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#e5dfdf' } } }, scales: { x: { stacked: true, ticks: { color: '#c1bbbb' } }, y: { stacked: true, ticks: { color: '#c1bbbb' }, title: { display: true, text: '$M', color: '#c1bbbb' } } } };

  return (
    <section className="strategic" aria-labelledby="business-title">
      <p className="eyebrow">Executive dashboard</p>
      <h1 id="business-title">Business Impact</h1>
      <p className="muted">Quarterly financial outcomes supplied by the data owner.</p>
      {loading && <p role="status">Loading business impact…</p>}
      {error && <div role="alert"><p className="error">{error}</p><button type="button" onClick={() => setVersion((v) => v + 1)}>Retry</button></div>}
      {!loading && !error && data && (latest ? (
        <>
          <p className="muted">Value cards: Q{latest.quarter} {latest.year} · Updated: {latest.updated_at}</p>
          <div className="metric-grid">
            <article className="metric-card"><h2>Revenue Attribution ($M)</h2><p className="metric-value">{value(latest.revenue_attribution_m, '')}</p></article>
            <article className="metric-card"><h2>Operational Cost Savings ($M)</h2><p className="metric-value">{value(latest.operational_cost_savings_m, '')}</p></article>
            <article className="metric-card"><h2>Transformation ROI (%)</h2><p className="metric-value">{value(latest.transformation_roi_pct, '%')}</p></article>
          </div>
          <h2>Quarterly comparison</h2>
          <article className="chart-panel">
            <p className="muted">Values are shown as supplied in $M. Stacking is for comparison, not a calculated total; missing values are not zero.</p>
            <div className="chart-container">
              <Bar role="img" aria-label="Quarterly business impact comparison" data={chart} options={options} />
            </div>
            <div className="table-scroll">
              <table>
                <caption>Quarterly business impact values ($M)</caption>
                <thead><tr><th scope="col">Quarter</th><th scope="col">IT Investment</th><th scope="col">Revenue Attribution</th><th scope="col">Cost Avoidance</th></tr></thead>
                <tbody>{quarters.map((row) => (
                  <tr key={`${row.year}-${row.quarter}`}><th scope="row">Q{row.quarter} {row.year}</th><td>{value(row.investment_m, '')}</td><td>{value(row.revenue_attribution_m, '')}</td><td>{value(row.cost_avoidance_m, '')}</td></tr>
                ))}</tbody>
              </table>
            </div>
            {data.total > quarters.length && <p className="muted">Showing the latest {quarters.length} of {data.total} quarters.</p>}
          </article>
        </>
      ) : <p>No business impact data available.</p>)}
    </section>
  );
}
