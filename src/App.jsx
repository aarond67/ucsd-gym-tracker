import { NavLink, Route, Routes } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import MealsPage from './pages/MealsPage';
import WorkoutPage from './pages/WorkoutPage';
import GymPage from './pages/GymPage';

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/meals', label: 'Meal Plan' },
  { to: '/workouts', label: 'Gym Plan' },
  { to: '/occupancy', label: 'Gym Occupancy' }
];

export default function App() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__badge">AD</div>
          <div>
            <h1>Cut Dashboard</h1>
            <p>Meal plan + training + gym timing</p>
          </div>
        </div>

        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) => `nav__link ${isActive ? 'is-active' : ''}`}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          <p>Built for a night-based cut routine.</p>
          <small>Use the occupancy page with your GitHub Actions CSV feed.</small>
        </div>
      </aside>

      <main className="content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/meals" element={<MealsPage />} />
          <Route path="/workouts" element={<WorkoutPage />} />
          <Route path="/occupancy" element={<GymPage />} />
        </Routes>
      </main>
    </div>
  );
}
