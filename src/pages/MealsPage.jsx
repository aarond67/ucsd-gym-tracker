import SectionHeader from '../components/SectionHeader';
import { controlData, currentWeekMenu, groceryList, recipes, weeklyAutoPlan } from '../data/mealPlan';

export default function MealsPage() {
  return (
    <div className="page">
      <SectionHeader
        eyebrow="Meal Plan"
        title="Cut meals and weekly targets"
        text="This page mirrors the meal spreadsheet so the site stays tied to the same calories, protein, and portion logic."
      />

      <section className="stats-grid">
        <article className="card simple-card"><strong>{controlData.startingWeight} lb</strong><span>Starting weight</span></article>
        <article className="card simple-card"><strong>{controlData.weeklyLossGoal} lb</strong><span>Weekly loss goal</span></article>
        <article className="card simple-card"><strong>{controlData.estimatedMaintenance}</strong><span>Maintenance estimate</span></article>
        <article className="card simple-card"><strong>{controlData.caloriesFloor}</strong><span>Calories floor</span></article>
      </section>

      <section className="two-col-grid">
        <article className="card">
          <h3>Weekly auto plan</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Planned wt</th>
                  <th>Calories</th>
                  <th>Protein</th>
                  <th>Rice</th>
                  <th>Chicken</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {weeklyAutoPlan.map((row) => (
                  <tr key={row.week}>
                    <td>{row.week}</td>
                    <td>{row.plannedWeight}</td>
                    <td>{row.targetCalories}</td>
                    <td>{row.protein} g</td>
                    <td>{row.riceCups} cups</td>
                    <td>{row.chickenOz} oz</td>
                    <td>{row.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="card">
          <h3>Grocery list</h3>
          <ul className="shopping-list">
            {groceryList.map(([item, amount, cost]) => (
              <li key={item}>
                <div>
                  <strong>{item}</strong>
                  <span>{amount}</span>
                </div>
                <small>{cost}</small>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="card">
        <h3>Current week menu</h3>
        <div className="menu-grid">
          {currentWeekMenu.map((day) => (
            <article key={day.day} className="menu-card">
              <span className="pill">Day {day.day}</span>
              <h4>{day.flavor}</h4>
              <p><strong>Meal 1:</strong> {day.meal1}</p>
              <p><strong>Meal 2:</strong> {day.meal2}</p>
              <p><strong>Add-on:</strong> {day.addon}</p>
              <div className="menu-card__footer">
                <span>{day.totalCalories} cal</span>
                <span>{day.totalProtein} g protein</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>Recipe cards</h3>
        <div className="recipe-grid">
          {recipes.map((recipe) => (
            <article key={recipe.name} className="recipe-card">
              <h4>{recipe.name}</h4>
              <p><strong>Ingredients:</strong> {recipe.ingredients}</p>
              <p><strong>Steps:</strong> {recipe.steps}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
