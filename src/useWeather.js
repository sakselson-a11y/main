import { useState, useEffect } from 'react'

const CITIES = [
  {
    id: 'stockholm',
    name: 'Stockholm',
    country: 'Sverige',
    lat: 59.3293,
    lon: 18.0686,
    timezone: 'Europe/Stockholm',
  },
  {
    id: 'valencia',
    name: 'Valencia',
    country: 'Spanien',
    lat: 39.4699,
    lon: -0.3763,
    timezone: 'Europe/Madrid',
  },
]

function buildUrl({ lat, lon, timezone }) {
  const params = new URLSearchParams({
    latitude: lat,
    longitude: lon,
    timezone,
    current: [
      'temperature_2m',
      'weather_code',
      'wind_speed_10m',
      'wind_direction_10m',
    ].join(','),
    daily: [
      'temperature_2m_max',
      'temperature_2m_min',
      'sunrise',
      'sunset',
    ].join(','),
    forecast_days: 1,
  })
  return `https://api.open-meteo.com/v1/forecast?${params}`
}

export function useWeather() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchAll() {
      try {
        const results = await Promise.all(
          CITIES.map(async (city) => {
            const res = await fetch(buildUrl(city))
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const json = await res.json()
            return { city, raw: json }
          })
        )
        if (!cancelled) {
          setData(results.map(({ city, raw }) => parseWeather(city, raw)))
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      }
    }

    fetchAll()
    return () => { cancelled = true }
  }, [])

  return { data, loading, error }
}

function parseWeather(city, raw) {
  const c = raw.current
  const d = raw.daily

  const maxTemp = d.temperature_2m_max[0]
  const minTemp = d.temperature_2m_min[0]
  const avgTemp = (maxTemp + minTemp) / 2

  // Format sunrise/sunset from ISO datetime to HH:MM
  const fmt = (iso) => iso ? iso.slice(11, 16) : '–'

  return {
    city,
    temperature: Math.round(c.temperature_2m),
    weatherCode: c.weather_code,
    windSpeed: Math.round(c.wind_speed_10m),
    windDirection: Math.round(c.wind_direction_10m),
    maxTemp: Math.round(maxTemp),
    minTemp: Math.round(minTemp),
    avgTemp: Math.round(avgTemp * 10) / 10,
    sunrise: fmt(d.sunrise[0]),
    sunset: fmt(d.sunset[0]),
  }
}
