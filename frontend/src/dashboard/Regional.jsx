import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';
import { Radar } from 'react-chartjs-2';
import { api } from '../api/client';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

/** Show persisted regional comparisons and inspect a selected warning region. */
export default function Regional() {
  const [radar, setRadar] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const [params, setParams] = useSearchParams();

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    Promise.all([api.get('/metrics/regional-radar'), api.get('/metrics/regional-performance')])
      .then(([radarResponse, performanceResponse]) => {
        if (active) {
          setRadar(radarResponse.data.regions);
          setPerformance(performanceResponse.data.regions);
        }
      })
      .catch(() => { if (active) setError('Unable to load regional data. Please try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [version]);

  const selected = performance?.find((row) => row.region === params.get('region') && ['Warning', 'Critical'].includes(row.status));
  const colors = ['#e7847e', '#c8bfba', '#a6aaa8'];
  const data = {
    labels: ['Health score', 'Availability %', 'Security score', 'Transformation index'],
    datasets: (radar || []).map((row, index) => ({
      label: row.region,
      data: [row.health_score, row.availability_pct, row.security_score, row.transformation_index].map(Number),
      borderColor: colors[index % colors.length],
      backgroundColor: 'transparent',
      pointBackgroundColor: colors[index % colors.length],
    })),
  };
  const options = { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#e5dfdf' } } }, scales: { r: { ticks: { color: '#c1bbbb', backdropColor: 'transparent' }, pointLabels: { color: '#e5dfdf' }, grid: { color: '#5a5353' }, angleLines: { color: '#5a5353' } } } };

  return (
    <section className="strategic" aria-labelledby="regional-title">
      <p className="eyebrow">Executive dashboard</p>
      <h1 id="regional-title">Executive Summary</h1>
      <p className="muted">Regional IT health and source-provided status.</p>
      <p className="muted">Enterprise-wide health, availability, security and transformation indicators are unavailable until separately supplied; regional values are not aggregated.</p>
      {loading && <p role="status">Loading regional data…</p>}
      {error && <div role="alert"><p className="error">{error}</p><button type="button" onClick={() => setVersion((v) => v + 1)}>Retry</button></div>}
      {!loading && !error && radar && performance && (
        <>
          <h2>Regional radar</h2>
          {radar.length ? (
            <div className="chart-panel">
              <p className="muted">Raw reported values are shown together; score definitions and comparability have not been specified.</p>
              <div className="chart-container">
                <Radar role="img" aria-label="Regional health radar comparison" data={data} options={options} />
              </div>
            </div>
          ) : <p>No regional radar data available.</p>}
          <h2>Regional status</h2>
          {performance.length ? (
            <div className="table-scroll">
              <table>
                <caption>Source-provided regional performance</caption>
                <thead><tr><th scope="col">Region</th><th scope="col">Health</th><th scope="col">Availability</th><th scope="col">Security</th><th scope="col">Transformation</th><th scope="col">Status</th><th scope="col">Action</th></tr></thead>
                <tbody>
                  {performance.map((row) => (
                    <tr key={row.region}>
                      <th scope="row">{row.region}</th><td>{row.health_score}</td><td>{row.availability_pct}%</td><td>{row.security_score}</td><td>{row.transformation_index}</td>
                      <td><span className={`regional-status status-${row.status.toLowerCase()}`}>{row.status}</span></td>
                      <td>{['Warning', 'Critical'].includes(row.status) ? <button type="button" className="regional-action" onClick={() => setParams({ region: row.region })}>Investigate {row.region}</button> : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p>No regional performance data available.</p>}
          {selected && (
            <article className="chart-panel" aria-labelledby="region-detail">
              <h2 id="region-detail">Investigate {selected.region}</h2>
              <p>Status: {selected.status} · Updated: {selected.updated_at}</p>
              <p>Health: {selected.health_score} · Availability: {selected.availability_pct}% · Security: {selected.security_score} · Transformation: {selected.transformation_index}</p>
              <p className="muted">These are the supplied values. Causes, thresholds and recommended actions have not been provided.</p>
              <button type="button" className="regional-action" onClick={() => setParams({})}>Close investigation</button>
            </article>
          )}
        </>
      )}
    </section>
  );
}
