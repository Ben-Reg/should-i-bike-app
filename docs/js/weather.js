const CACHE_KEY = 'forecast';
const CACHE_MINUTES = 60;

const conversions = {
  'wmoUnit:degC':         v => Math.round((v * 9/5) + 32),
  'wmoUnit:km_h-1':       v => Math.round(v * 0.62137),
  'wmoUnit:m':            v => Math.round(v * 1.0936132983377),
  'wmoUnit:degree_(angle)': angleToDir,
};

function angleToDir(angle) {
  const dirs = [
    [0,'N'],[22.5,'NNE'],[45,'NE'],[67.5,'ENE'],
    [90,'E'],[112.5,'ESE'],[135,'SE'],[157.5,'SSE'],
    [180,'S'],[202.5,'SSW'],[225,'SW'],[247.5,'WSW'],
    [270,'W'],[292.5,'WNW'],[315,'NW'],[337.5,'NNW']
  ];
  const matches = dirs.filter(d => d[0] <= angle);
  return matches[matches.length - 1][1];
}

async function zipToLatLon(zip, country) {
  const cc = (country || 'US').toLowerCase();
  const url = `https://nominatim.openstreetmap.org/search?postalcode=${encodeURIComponent(zip)}&countrycodes=${cc}&format=json&limit=1`;
  const res = await fetch(url, { headers: { 'Accept': 'application/json', 'User-Agent': 'should-i-bike-pwa' } });
  const data = await res.json();
  if (!data.length) throw new Error(`Could not find location for zip ${zip}`);
  return { lat: parseFloat(data[0].lat), lon: parseFloat(data[0].lon) };
}

async function fetchNoaaUrls(lat, lon) {
  const res = await fetch(`https://api.weather.gov/points/${lat.toFixed(4)},${lon.toFixed(4)}`, {
    headers: { 'User-Agent': 'should-i-bike-pwa (3612364+Ben-Reg@users.noreply.github.com)', 'Accept': 'application/geo+json' }
  });
  if (!res.ok) throw new Error('NOAA points API failed');
  const data = await res.json();
  return {
    forecastHourly: data.properties.forecastHourly,
    forecastGridData: data.properties.forecastGridData,
  };
}

function expandGridValues(gridElement) {
  const expanded = [];
  for (const entry of gridElement.values) {
    const isoTime = entry.validTime.slice(0, 25);
    const durationMatch = entry.validTime.match(/\/PT(\d+)H/) || entry.validTime.match(/\/P(\d+)DT(\d+)H/);
    let hours = 1;
    if (durationMatch) {
      hours = durationMatch[2]
        ? parseInt(durationMatch[1]) * 24 + parseInt(durationMatch[2])
        : parseInt(durationMatch[1]);
    }
    const base = new Date(isoTime);
    for (let h = 0; h < hours; h++) {
      const t = new Date(base.getTime() + h * 3600000);
      expanded.push({ time: t, value: entry.value });
    }
  }
  return expanded;
}

async function fetchAndBuildForecast(zip, country, hoursReturned) {
  const { lat, lon } = await zipToLatLon(zip, country);
  const { forecastHourly: hourlyUrl, forecastGridData: gridUrl } = await fetchNoaaUrls(lat, lon);

  const [hourlyRes, gridRes] = await Promise.all([
    fetch(hourlyUrl, { headers: { 'User-Agent': 'should-i-bike-pwa (3612364+Ben-Reg@users.noreply.github.com)' } }),
    fetch(gridUrl,   { headers: { 'User-Agent': 'should-i-bike-pwa (3612364+Ben-Reg@users.noreply.github.com)' } }),
  ]);
  if (!hourlyRes.ok || !gridRes.ok) throw new Error('NOAA forecast fetch failed');

  const [hourlyData, gridData] = await Promise.all([hourlyRes.json(), gridRes.json()]);

  const hourlyPeriods = hourlyData.properties.periods.slice(0, hoursReturned);
  const gridProps = gridData.properties;

  // Build grid lookup maps for windGust and visibility
  const windGustExpanded   = expandGridValues(gridProps.windGust);
  const visibilityExpanded = expandGridValues(gridProps.visibility);

  function gridValueAt(expanded, targetTime) {
    const t = new Date(targetTime).getTime();
    const matches = expanded.filter(e => e.time.getTime() <= t);
    return matches.length ? matches[matches.length - 1].value : null;
  }

  const forecast = hourlyPeriods.map(p => {
    const startTime = p.startTime;
    const rawGust = gridValueAt(windGustExpanded, startTime);
    const rawVis  = gridValueAt(visibilityExpanded, startTime);
    return {
      startTime,
      temperature:   p.temperature,
      windSpeed:     p.windSpeed,
      windDirection: p.windDirection,
      windGust:      rawGust !== null ? Math.round(rawGust * 0.62137) : null,
      visibility:    rawVis  !== null ? Math.round(rawVis * 1.0936)   : null,
      probabilityOfPrecipitation: p.probabilityOfPrecipitation?.value ?? 0,
    };
  });

  // Also store raw grid data keyed by element name for getForecastValue
  const gridCache = {};
  for (const [key, val] of Object.entries(gridProps)) {
    if (val && val.values) {
      gridCache[key] = { uom: val.uom, expanded: expandGridValues(val) };
    }
  }

  return { forecast, gridCache };
}

async function getWeather(zip, country, hoursReturned) {
  const cached = await db.weather_cache.get(CACHE_KEY);
  const now = Date.now();
  if (cached && (now - cached.timestamp) < CACHE_MINUTES * 60 * 1000) {
    return cached.data;
  }
  const data = await fetchAndBuildForecast(zip, country, hoursReturned);
  await db.weather_cache.put({ key: CACHE_KEY, data, timestamp: now });
  return data;
}

async function getForecastValue(weatherElement, dateStr, hour, zip, country, hoursReturned) {
  const { gridCache } = await getWeather(zip, country, hoursReturned);
  const el = gridCache[weatherElement];
  if (!el) return null;

  // dateStr is yyyy-mm-dd from <input type="date">
  const target = new Date(`${dateStr}T${String(hour).padStart(2,'0')}:00:00`);

  const matches = el.expanded.filter(e => e.time <= target);
  if (!matches.length) return null;

  const raw = matches[matches.length - 1].value;
  const conv = conversions[el.uom];
  return conv ? conv(raw) : raw;
}

async function clearWeatherCache() {
  await db.weather_cache.delete(CACHE_KEY);
}
