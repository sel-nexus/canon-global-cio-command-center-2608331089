import { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend } from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { api } from '../api/client';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend);

/** Display only observations returned by the authenticated dashboard API. */
export default function Strategic() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const [exporting, setExporting] = useState('');
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.get('/dashboard/strategic-metrics').then((response) => {
      if (active) setData(response.data);
    }).catch(() => {
      if (active) setError('Unable to load strategic metrics. Please try again.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [version]);

  async function download(format) {
    setExporting(format);
    setExportError('');
    try {
      const response = await api.get('/dashboard/strategic-metrics/export', { params: { format }, responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `strategic-metrics.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setExportError('Export failed. Please try again.');
    } finally { setExporting(''); }
  }

  const months = [];
  if (data) {
    const [year, month] = data.window_start.split('-').map(Number);
    for (let i = 0; i < 12; i += 1) {
      const date = new Date(Date.UTC(year, month - 1 + i, 1));
      months.push(date.toISOString().slice(0, 7));
    }
  }
  const series = new Map();
  data?.trends.forEach((item) => {
    const key = JSON.stringify([item.category, item.metric_name, item.unit]);
    if (!series.has(key)) series.set(key, { name: item.metric_name, category: item.category, unit: item.unit, values: {} });
    series.get(key).values[item.recorded_date.slice(0, 7)] = Number(item.metric_value);
  });
  const budgets = new Map();
  data?.budgets.forEach((item) => {
    const key = JSON.stringify([item.name, item.unit]);
    if (!budgets.has(key)) budgets.set(key, { name: item.name, unit: item.unit, values: {} });
    budgets.get(key).values[item.month.slice(0, 7)] = item;
  });
  const options = { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#e5dfdf' } } }, scales: { x: { ticks: { color: '#c1bbbb' } }, y: { ticks: { color: '#c1bbbb' } } } };

  return (
    <section className="strategic" aria-labelledby="strategic-title">
      <div className="strategic-heading">
        <div>
          <p className="eyebrow">Executive dashboard</p>
          <h1 id="strategic-title">Strategic Command</h1>
          <p className="muted">Enterprise indicators and source-provided insights.</p>
        </div>
        <div className="export-actions" aria-label="Export strategic data">
          <button type="button" disabled={loading || Boolean(error) || Boolean(exporting)} onClick={() => download('json')}>Export JSON</button>
          <button type="button" disabled={loading || Boolean(error) || Boolean(exporting)} onClick={() => download('csv')}>Export CSV</button>
        </div>
      </div>
      {exportError && <p role="alert" className="error">{exportError}</p>}
      {loading && <p role="status">Loading strategic data…</p>}
      {error && <div role="alert"><p className="error">{error}</p><button type="button" onClick={() => setVersion((v) => v + 1)}>Retry</button></div>}
      {!loading && !error && data && (
        <>
          <p className="muted">Reporting window: {data.window_start} to {data.window_end}</p>
          {data.metrics.length === 0 && data.budgets.length === 0 ? <p>No strategic data available for this period.</p> : (
            <>
              <div className="metric-grid">
                {data.metrics.map((metric) => (
                  <article className="metric-card" key={`${metric.category}:${metric.metric_name}`}>
                    <p className="eyebrow">{metric.category}</p>
                    <h2>{metric.metric_name}</h2>
                    <p className="metric-value">{metric.metric_value} {metric.unit}</p>
                    <p className="muted">{metric.trend || 'Trend unavailable'}{metric.change_pct != null ? ` · ${metric.change_pct}%` : ''} · {metric.recorded_date}</p>
                  </article>
                ))}
              </div>
              <h2>Insights</h2>
              {data.insights.length ? <ul>{data.insights.map((item) => <li key={`${item.category}:${item.metric_name}`}>{item.insight} <span className="muted">({item.metric_name}, {item.recorded_date})</span></li>)}</ul> : <p className="muted">No insights provided.</p>}
              <h2>12-month performance</h2>
              {series.size ? [...series.entries()].map(([key, item]) => (
                <article className="chart-panel" key={key}>
                  <h3>{item.name} {item.unit && `(${item.unit})`}</h3>
                  <div className="chart-container"><Line aria-label={`${item.name} performance chart`} role="img" options={options} data={{ labels: months, datasets: [{ label: item.name, data: months.map((month) => item.values[month] ?? null), borderColor: '#e7847e', backgroundColor: '#e7847e', spanGaps: false }] }} /></div>
                  <table><caption>Recorded {item.name} observations</caption><thead><tr><th scope="col">Date</th><th scope="col">Value</th></tr></thead><tbody>{data.trends.filter((row) => row.metric_name === item.name && row.category === item.category && row.unit === item.unit).map((row) => <tr key={row.recorded_date}><td>{row.recorded_date}</td><td>{row.metric_value} {row.unit}</td></tr>)}</tbody></table>
                </article>
              )) : <p className="muted">No performance observations provided.</p>}
              <h2>Budget versus actual</h2>
              {budgets.size ? [...budgets.entries()].map(([key, item]) => (
                <article className="chart-panel" key={key}>
                  <h3>{item.name} {item.unit && `(${item.unit})`}</h3>
                  <div className="chart-container"><Bar aria-label={`${item.name} budget versus actual chart`} role="img" options={options} data={{ labels: months, datasets: [{ label: 'Budget', data: months.map((m) => item.values[m] ? Number(item.values[m].budget) : null), backgroundColor: '#a5a0a0' }, { label: 'Actual', data: months.map((m) => item.values[m] ? Number(item.values[m].actual) : null), backgroundColor: '#e7847e' }] }} /></div>
                  <table><caption>Recorded {item.name} budget and actual</caption><thead><tr><th scope="col">Month</th><th scope="col">Budget</th><th scope="col">Actual</th></tr></thead><tbody>{Object.values(item.values).map((row) => <tr key={row.month}><td>{row.month}</td><td>{row.budget}</td><td>{row.actual}</td></tr>)}</tbody></table>
                </article>
              )) : <p className="muted">No budget comparisons provided.</p>}
            </>
          )}
        </>
      )}
    </section>
  );
}
