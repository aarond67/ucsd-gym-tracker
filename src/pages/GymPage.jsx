import { useEffect, useState } from 'react';
import SectionHeader from '../components/SectionHeader';
import StatCard from '../components/StatCard';
import OccupancyChart from '../components/OccupancyChart';
import { loadOccupancyCsv, summarizeOccupancy } from '../utils/occupancy';

export default function GymPage() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadOccupancyCsv()
      .then((rows) => setSummary(summarizeOccupancy(rows)))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="page">
      <SectionHeader
        eyebrow="Gym Occupancy"
        title="Live crowd timing from your scraper"
        text="This page reads public/data/gym_occupancy.csv so your GitHub Actions workflow can keep feeding the site without changing the React code."
      />

      <section className="stats-grid">
        <StatCard label="Latest" value={summary?.latest ? `${summary.latest.occupancy}%` : '--'} helper={summary?.latest?.timestamp || error || 'No CSV loaded yet'} />
        <StatCard label="Best hour" value={summary?.bestHour?.label || '--'} helper={summary?.bestHour ? `${summary.bestHour.avgOccupancy}% avg` : 'Waiting for data'} />
        <StatCard label="Busiest hour" value={summary?.busiestHour?.label || '--'} helper={summary?.busiestHour ? `${summary.busiestHour.avgOccupancy}% avg` : 'Waiting for data'} />
        <StatCard label="Sample size" value={summary?.recent ? `${summary.recent.length}+` : '--'} helper="Recent rows shown below" />
      </section>

      {summary?.hourly?.length ? <OccupancyChart data={summary.hourly} /> : null}

      <section className="two-col-grid">
        <article className="card">
          <h3>Recent samples</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Facility</th>
                  <th>Occupancy</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {summary?.recent?.map((row) => (
                  <tr key={`${row.timestamp}-${row.occupancy}`}>
                    <td>{row.timestamp}</td>
                    <td>{row.facility}</td>
                    <td>{row.occupancy}%</td>
                    <td>{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="card">
          <h3>GitHub Actions hookup</h3>
          <ol className="number-list">
            <li>Have your scraper write the latest CSV to <code>public/data/gym_occupancy.csv</code>.</li>
            <li>Commit or artifact-sync that file in the same repo your site deploys from.</li>
            <li>Let the deploy workflow rebuild the site after the CSV updates.</li>
            <li>Keep timestamps in local time so the hour summaries are actually useful.</li>
          </ol>
          <div className="notice">
            <strong>Expected columns:</strong> Timestamp, Facility, Occupancy %, Status
          </div>
        </article>
      </section>
    </div>
  );
}
