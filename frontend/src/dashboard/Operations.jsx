import { useEffect, useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { api } from '../api/client';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

/** Display persisted incidents and source-reported operational history. */
export default function Operations() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    Promise.all([api.get('/operations/summary'), api.get('/operations/incidents')])
      .then(([summary, incidents]) => { if (active) setData({ summary: summary.data, incidents: incidents.data }); })
      .catch(() => { if (active) setError('Unable to load operations. Please try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [version]);

  const summary = data?.summary;
  const history = summary?.history || [];
  const value = (v, suffix = '') => v == null ? 'Not provided' : `${v}${suffix}`;
  const chart = {
    labels: history.map((row) => row.recorded_date),
    datasets: [
      { label: 'Incident volume', data: history.map((row) => row.incident_volume), borderColor: '#e7847e', yAxisID: 'volume' },
      { label: 'P1 volume', data: history.map((row) => row.p1_volume), borderColor: '#ffb5ad', yAxisID: 'volume' },
      { label: 'P2 volume', data: history.map((row) => row.p2_volume), borderColor: '#c1bbbb', yAxisID: 'volume' },
      { label: 'Resolutions per reporting day', data: history.map((row) => row.resolution_count), borderColor: '#a2d6b8', yAxisID: 'resolutions' },
    ],
  };
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#e5dfdf' } } },
    scales: {
      x: { ticks: { color: '#c1bbbb' } },
      volume: {
        position: 'left', beginAtZero: true,
        title: { display: true, text: 'Incidents', color: '#c1bbbb' }, ticks: { color: '#c1bbbb' },
      },
      resolutions: {
        position: 'right', beginAtZero: true, grid: { drawOnChartArea: false },
        title: { display: true, text: 'Resolutions / reporting day', color: '#c1bbbb' }, ticks: { color: '#c1bbbb' },
      },
    },
  };

  return (
    <section className="strategic" aria-labelledby="operations-title">
      <p className="eyebrow">Executive dashboard</p>
      <h1 id="operations-title">Operations</h1>
      <p className="muted">Incident records and source-reported operational measures.</p>
      {loading && <p role="status">Loading operations…</p>}
      {error && (
        <div role="alert">
          <p className="error">{error}</p>
          <button type="button" onClick={() => setVersion((v) => v + 1)}>Retry</button>
        </div>
      )}
      {!loading && !error && data && (
        <>
          <div className="metric-grid">
            {['P1', 'P2', 'P3'].map((severity) => (
              <article className="metric-card" key={severity}>
                <h2>Active {severity}</h2>
                <p className="metric-value">{value(summary.active_counts?.[severity])}</p>
              </article>
            ))}
            <article className="metric-card">
              <h2>MTTR (minutes)</h2>
              <p className="metric-value">{value(summary.latest?.mttr_minutes)}</p>
            </article>
            <article className="metric-card">
              <h2>SLA compliance</h2>
              <p className="metric-value">{value(summary.latest?.sla_compliance_pct, '%')}</p>
            </article>
            <article className="metric-card">
              <h2>System uptime</h2>
              <p className="metric-value">{value(summary.latest?.uptime_pct, '%')}</p>
            </article>
          </div>
          <p className="muted">
            {summary.latest
              ? `Latest supplied measures: ${summary.latest.recorded_date} · Updated: ${summary.latest.updated_at}`
              : 'No operations history available.'}
          </p>
          <h2>Incident volume and resolution history</h2>
          {history.length ? (
            <article className="chart-panel">
              <p className="muted">Source-supplied counts per reporting day; missing observations are not zero.</p>
              <div className="chart-container">
                <Line role="img" aria-label="Incident volume and resolution history" data={chart} options={options} />
              </div>
              <div className="table-scroll">
                <table>
                  <caption>Source-reported incident history</caption>
                  <thead>
                    <tr>
                      <th scope="col">Date</th>
                      <th scope="col">Volume</th>
                      <th scope="col">P1</th>
                      <th scope="col">P2</th>
                      <th scope="col">Resolutions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((row) => (
                      <tr key={row.recorded_date}>
                        <th scope="row">{row.recorded_date}</th>
                        <td>{value(row.incident_volume)}</td>
                        <td>{value(row.p1_volume)}</td>
                        <td>{value(row.p2_volume)}</td>
                        <td>{value(row.resolution_count)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {summary.history_total > history.length && (
                <p className="muted">Showing the latest {history.length} of {summary.history_total} reporting days.</p>
              )}
            </article>
          ) : <p>No incident history available.</p>}
          <h2>Recent incidents</h2>
          {data.incidents.incidents.length ? (
            <div className="table-scroll">
              <table>
                <caption>Recent stored incidents</caption>
                <thead>
                  <tr>
                    <th scope="col">Number</th>
                    <th scope="col">Title</th>
                    <th scope="col">Severity</th>
                    <th scope="col">Status</th>
                    <th scope="col">Created</th>
                    <th scope="col">Resolved</th>
                  </tr>
                </thead>
                <tbody>
                  {data.incidents.incidents.map((incident) => (
                    <tr key={incident.incident_number}>
                      <th scope="row">{incident.incident_number}</th>
                      <td>{incident.title}</td>
                      <td>{incident.severity}</td>
                      <td>{incident.status}</td>
                      <td>{incident.created_at}</td>
                      <td>{value(incident.resolved_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {data.incidents.total > data.incidents.incidents.length && (
                <p className="muted">Showing {data.incidents.incidents.length} of {data.incidents.total} incidents.</p>
              )}
            </div>
          ) : <p>No incidents available.</p>}
        </>
      )}
    </section>
  );
}
