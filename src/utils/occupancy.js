import Papa from 'papaparse';

export async function loadOccupancyCsv(path = './data/gym_occupancy.csv') {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error('Could not load gym occupancy CSV.');
  }

  const csvText = await response.text();
  const parsed = Papa.parse(csvText, {
    header: true,
    dynamicTyping: true,
    skipEmptyLines: true
  });

  return parsed.data
    .map((row) => ({
      timestamp: row.Timestamp || row.timestamp,
      facility: row.Facility || row.facility || 'Main Gym',
      occupancy: Number(row['Occupancy %'] ?? row.occupancy ?? 0),
      status: row.Status || row.status || ''
    }))
    .filter((row) => row.timestamp && Number.isFinite(row.occupancy));
}

export function summarizeOccupancy(rows) {
  if (!rows.length) {
    return {
      latest: null,
      average: 0,
      bestHour: null,
      busiestHour: null,
      hourly: [],
      recent: []
    };
  }

  const sorted = [...rows].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  const latest = sorted.at(-1);
  const average = sorted.reduce((sum, row) => sum + row.occupancy, 0) / sorted.length;

  const hourBuckets = Array.from({ length: 24 }, (_, hour) => ({
    hour,
    label: formatHour(hour),
    values: []
  }));

  sorted.forEach((row) => {
    const hour = new Date(row.timestamp).getHours();
    if (!Number.isNaN(hour)) {
      hourBuckets[hour].values.push(row.occupancy);
    }
  });

  const hourly = hourBuckets.map((bucket) => ({
    hour: bucket.hour,
    label: bucket.label,
    avgOccupancy: bucket.values.length
      ? Math.round((bucket.values.reduce((sum, value) => sum + value, 0) / bucket.values.length) * 10) / 10
      : null
  }));

  const withData = hourly.filter((item) => item.avgOccupancy !== null);
  const bestHour = withData.reduce((best, item) => (!best || item.avgOccupancy < best.avgOccupancy ? item : best), null);
  const busiestHour = withData.reduce((worst, item) => (!worst || item.avgOccupancy > worst.avgOccupancy ? item : worst), null);

  return {
    latest,
    average: Math.round(average * 10) / 10,
    bestHour,
    busiestHour,
    hourly,
    recent: sorted.slice(-12).reverse()
  };
}

function formatHour(hour) {
  const date = new Date();
  date.setHours(hour, 0, 0, 0);
  return date.toLocaleTimeString([], { hour: 'numeric' });
}
