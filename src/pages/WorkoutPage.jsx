import SectionHeader from '../components/SectionHeader';
import { nightLifterNotes, weeklySplit } from '../data/workoutPlan';

export default function WorkoutPage() {
  return (
    <div className="page">
      <SectionHeader
        eyebrow="Gym Plan"
        title="Weight lifting split for the cut"
        text="High enough intensity to hold onto muscle while calories are lower, with the setup tuned toward night training."
      />

      <section className="plan-grid">
        {weeklySplit.map((block) => (
          <article key={block.day} className="card plan-card">
            <div className="plan-card__top">
              <span className="pill">{block.day}</span>
              <h3>{block.title}</h3>
              <p>{block.focus}</p>
            </div>
            <ul className="bullet-list">
              {block.exercises.map((exercise) => (
                <li key={exercise}>{exercise}</li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      <section className="card">
        <h3>Night lifter reminders</h3>
        <ul className="bullet-list bullet-list--two-col">
          {nightLifterNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
