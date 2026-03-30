import { ResponsiveContainer, BarChart, Bar, CartesianGrid, Tooltip, XAxis, YAxis } from 'recharts';

export default function OccupancyChart({ data }) {
  const chartData = data.filter((item) => item.avgOccupancy !== null);

  return (
    <div className="card chart-card">
      <div className="chart-card__header">
        <h3>Average crowd by hour</h3>
        <p>Use this to pick night lifting windows that stay calmer.</p>
      </div>
      <div className="chart-card__body">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" interval={1} angle={-35} textAnchor="end" height={70} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="avgOccupancy" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
