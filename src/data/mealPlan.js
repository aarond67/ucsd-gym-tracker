export const controlData = {
  startingWeight: 238,
  weeklyLossGoal: 2,
  estimatedMaintenance: 2700,
  dailyWorkoutAddon: 250,
  workoutsPerWeek: 5,
  proteinFactor: 0.9,
  caloriesFloor: 1800,
  selectedWeek: 1,
  riceCupsStart: 1.5,
  riceDropEvery4Weeks: 0.1
};

export const weeklyAutoPlan = [
  { week: 1, plannedWeight: 238, targetCalories: 1879, protein: 214, riceCups: 1.5, chickenOz: 9.5, beefOz: 7.0, potatoG: 300, note: 'Starting week' },
  { week: 2, plannedWeight: 236, targetCalories: 1863, protein: 212, riceCups: 1.5, chickenOz: 9.4, beefOz: 7.0, potatoG: 296, note: 'Stay the course' },
  { week: 3, plannedWeight: 234, targetCalories: 1847, protein: 211, riceCups: 1.5, chickenOz: 9.3, beefOz: 6.9, potatoG: 292, note: 'Stay the course' },
  { week: 4, plannedWeight: 232, targetCalories: 1831, protein: 209, riceCups: 1.5, chickenOz: 9.2, beefOz: 6.9, potatoG: 288, note: 'Stay the course' },
  { week: 5, plannedWeight: 230, targetCalories: 1815, protein: 207, riceCups: 1.4, chickenOz: 9.1, beefOz: 6.8, potatoG: 284, note: 'Stay the course' },
  { week: 6, plannedWeight: 228, targetCalories: 1800, protein: 205, riceCups: 1.4, chickenOz: 9.0, beefOz: 6.8, potatoG: 280, note: 'Calories floor reached' }
];

export const currentWeekMenu = [
  {
    day: 1,
    flavor: 'Taco',
    meal1: 'Oats 1 cup cooked with water; scramble egg whites 1 cup + 2 eggs; Greek yogurt 1 cup on the side',
    meal1Calories: 600,
    meal1Protein: 57,
    meal2: 'Chicken 9.5 oz + rice 1.5 cup + broccoli 1 cup + taco seasoning + salsa',
    meal2Calories: 1159,
    meal2Protein: 132,
    addon: 'Protein shake 1 scoop in water',
    addonCalories: 120,
    addonProtein: 25,
    totalCalories: 1879,
    totalProtein: 214
  },
  {
    day: 2,
    flavor: 'Lemon Garlic',
    meal1: 'Same breakfast bowl',
    meal1Calories: 600,
    meal1Protein: 57,
    meal2: 'Chicken 9.5 oz + rice 1.5 cup + broccoli 1 cup + lemon juice + garlic',
    meal2Calories: 1159,
    meal2Protein: 132,
    addon: 'Protein shake 1 scoop in water',
    addonCalories: 120,
    addonProtein: 25,
    totalCalories: 1879,
    totalProtein: 214
  },
  {
    day: 3,
    flavor: 'Spicy',
    meal1: 'Same breakfast bowl',
    meal1Calories: 600,
    meal1Protein: 57,
    meal2: 'Chicken 9.5 oz + rice 1.5 cup + broccoli 1 cup + hot sauce + chili flakes',
    meal2Calories: 1159,
    meal2Protein: 132,
    addon: 'Protein shake 1 scoop in water',
    addonCalories: 120,
    addonProtein: 25,
    totalCalories: 1879,
    totalProtein: 214
  },
  {
    day: 4,
    flavor: 'Garlic Paprika',
    meal1: 'Same breakfast bowl',
    meal1Calories: 600,
    meal1Protein: 57,
    meal2: 'Chicken 9.5 oz + rice 1.5 cup + broccoli 1 cup + garlic + paprika',
    meal2Calories: 1159,
    meal2Protein: 132,
    addon: 'Protein shake 1 scoop in water',
    addonCalories: 120,
    addonProtein: 25,
    totalCalories: 1879,
    totalProtein: 214
  },
  {
    day: 5,
    flavor: 'Herb',
    meal1: 'Same breakfast bowl',
    meal1Calories: 600,
    meal1Protein: 57,
    meal2: 'Chicken 9.5 oz + rice 1.5 cup + mixed veggies 1 cup + Italian seasoning',
    meal2Calories: 1159,
    meal2Protein: 132,
    addon: 'Protein shake 1 scoop in water',
    addonCalories: 120,
    addonProtein: 25,
    totalCalories: 1879,
    totalProtein: 214
  },
  {
    day: 6,
    flavor: 'Buffalo',
    meal1: 'Same breakfast bowl',
    meal1Calories: 600,
    meal1Protein: 57,
    meal2: 'Chicken 9.5 oz + rice 1.5 cup + broccoli 1 cup + buffalo sauce',
    meal2Calories: 1159,
    meal2Protein: 132,
    addon: 'Protein shake 1 scoop in water',
    addonCalories: 120,
    addonProtein: 25,
    totalCalories: 1879,
    totalProtein: 214
  },
  {
    day: 7,
    flavor: 'Salt & Pepper',
    meal1: 'Same breakfast bowl',
    meal1Calories: 600,
    meal1Protein: 57,
    meal2: '93% beef 7 oz + potatoes 300 g + veggies 1 cup + salt + pepper',
    meal2Calories: 1159,
    meal2Protein: 132,
    addon: 'Protein shake 1 scoop in water',
    addonCalories: 120,
    addonProtein: 25,
    totalCalories: 1879,
    totalProtein: 214
  }
];

export const groceryList = [
  ['Chicken breast', '3.6 lb', '$28-38'],
  ['93% lean ground beef', '0.4 lb', '$5-8'],
  ['Egg whites', '7 cups', '$6-10'],
  ['Eggs', '14 eggs', '$4-6'],
  ['Greek yogurt', '7 cups', '$10-14'],
  ['Oats', '7 cups', '$3-5'],
  ['Rice', '9 cups cooked', '$4-6'],
  ['Potatoes', '0.7 lb', '$1-3'],
  ['Broccoli / mixed veg', '7 cups', '$8-12'],
  ['Protein powder', '7 scoops', '$6-10']
];

export const recipes = [
  {
    name: 'Breakfast Bowl',
    ingredients: '1 cup oats, 1 cup water, 1 cup egg whites, 2 eggs, 1 cup Greek yogurt',
    steps: 'Microwave oats. Scramble egg whites + eggs. Serve yogurt on the side.'
  },
  {
    name: 'Taco Chicken Bowl',
    ingredients: 'Chicken, rice, broccoli, taco seasoning, salsa',
    steps: 'Season chicken, bake at 400°F for 20–25 min, serve over rice with broccoli and salsa.'
  },
  {
    name: 'Salt & Pepper Beef Plate',
    ingredients: '93% beef, potatoes, vegetables, salt, pepper, garlic powder',
    steps: 'Brown beef, cook potatoes, plate with vegetables.'
  }
];
