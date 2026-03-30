import { useEffect, useMemo, useState } from 'react';
import StatCard from '../components/StatCard';
import SectionHeader from '../components/SectionHeader';
import OccupancyChart from '../components/OccupancyChart';
import { controlData, currentWeekMenu, weeklyAutoPlan } from '../data/mealPlan';
import { weeklySplit } from '../data/workoutPlan';
import { loadOccupancyCsv, summarizeOccupancy } from '../utils/occupancy';

export default function DashboardPage() {
  const [occupancy, setOccupancy] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadOccupancyCsv()
      .then((rows) => setOccupancy(summarizeOccupancy(rows)))
      .catch(() => setError('Add or update public/data/gym_occupancy.csv to activate live occupancy cards.'));
  }, []);

  const currentWeek = weeklyAutoPlan[0];
  const todayMenu = currentWeekMenu[0];
  const nextWorkout = weeklySplit[0];

  const dashboardCards = useMemo(
    () => [
      { label: 'Target calories', value: `${currentWeek.targetCalories}`, helper: `Week ${currentWeek.week} cut target` },
      { label: 'Protein target', value: `${currentWeek.protein} g`, helper: `${controlData.proteinFactor} g per lb setup` },
      { label: 'Starting weight', value: `${controlData.startingWeight} lb`, helper: `${controlData.weeklyLossGoal} lb per week goal` },
      { label: 'Workouts / week', value: `${controlData.workoutsPerWeek}`, helper: '4 lifting days + recovery/cardio' }
    ],
    [currentWeek]
  );

  return (
    <div className="page">
      <SectionHeader
        eyebrow="Overview"
        title="Everything in one place"
        text="This homepage blends your cut targets, current meal structure, workout split, and your live gym crowd feed from GitHub Actions."
      />

      <section className="stats-grid">
        {dashboardCards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="card hero-card">
          <div>
            <span className="pill">Tonight&apos;s focus</span>
            <h3>{nextWorkout.title}</h3>
            <p>{nextWorkout.focus}</p>
          </div>
          <ul className="bullet-list">
            {nextWorkout.exercises.slice(0, 3).map((exercise) => (
              <li key={exercise}>{exercise}</li>
            ))}
          </ul>
        </article>

        <article className="card hero-card hero-card--accent">
          <div>
            <span className="pill">Today&apos;s food</span>
            <h3>{todayMenu.flavor} day</h3>
            <p>{todayMenu.totalCalories} calories · {todayMenu.totalProtein} g protein</p>
          </div>
          <ul className="bullet-list">
            <li>{todayMenu.meal1}</li>
            <li>{todayMenu.meal2}</li>
            <li>{todayMenu.addon}</li>
          </ul>
        </article>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Latest occupancy"
          value={occupancy?.latest ? `${occupancy.latest.occupancy}%` : '--'}
          helper={occupancy?.latest ? `${occupancy.latest.status || 'Live'} at ${new Date(occupancy.latest.timestamp).toLocaleString()}` : error || 'Waiting for CSV'}
        />
        <StatCard
          label="Average occupancy"
          value={occupancy ? `${occupancy.average}%` : '--'}
          helper="Across the loaded gym history"
        />
        <StatCard
          label="Best hour"
          value={occupancy?.bestHour?.label || '--'}
          helper={occupancy?.bestHour ? `${occupancy.bestHour.avgOccupancy}% avg crowd` : 'Waiting for CSV'}
        />
        <StatCard
          label="Busiest hour"
          value={occupancy?.busiestHour?.label || '--'}
          helper={occupancy?.busiestHour ? `${occupancy.busiestHour.avgOccupancy}% avg crowd` : 'Waiting for CSV'}
        />
      </section>

      {occupancy?.hourly?.length ? <OccupancyChart data={occupancy.hourly} /> : null}
    </div>
  );
}
