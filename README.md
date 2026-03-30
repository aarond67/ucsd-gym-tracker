# Cut Dashboard

This React + SCSS dashboard combines:
- your meal plan
- your lifting split
- your gym occupancy CSV feed

## Pages
- Dashboard
- Meal Plan
- Gym Plan
- Gym Occupancy

## Local setup
```bash
npm install
npm run dev
```

## Build
```bash
npm run build
```

## Hook it up to your scraper
The app reads this file in the deployed site:

```text
public/data/gym_occupancy.csv
```

Expected columns:
- Timestamp
- Facility
- Occupancy %
- Status

## GitHub Actions idea
If your scraper already runs in Actions/cloud, write or copy the newest CSV into `public/data/gym_occupancy.csv` before the deploy step. Then let the deploy workflow build and publish the site.

## Time zone note
Write timestamps in local time for the gym you care about, otherwise the hourly crowd chart will be misleading.
