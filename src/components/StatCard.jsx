export default function StatCard({ label, value, helper }) {
  return (
    <article className="card stat-card">
      <p className="stat-card__label">{label}</p>
      <h3 className="stat-card__value">{value}</h3>
      {helper ? <small className="stat-card__helper">{helper}</small> : null}
    </article>
  );
}
