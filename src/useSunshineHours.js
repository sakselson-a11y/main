import { useState, useEffect } from 'react'

const CITIES = [
  { id: 'stockholm', lat: 59.3293, lon: 18.0686, timezone: 'Europe/Stockholm' },
  { id: 'valencia', lat: 39.4699, lon: -0.3763, timezone: 'Europe/Madrid' },
]

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function buildUrl({ lat, lon, timezone }, startDate, endDate) {
  const params = new URLSearchParams({
    latitude: lat,
    longitude: lon,
    start_date: startDate,
    end_date: endDate,
    daily: 'sunshine_duration',
    timezone,
  })
  return `https://archive-api.open-meteo.com/v1/archive?${params}`
}

export function useSunshineHours() {
  const [data, setData] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      const now = new Date()
      const year = now.getFullYear()
      const startDate = `${year}-01-01`

      // Archive typically lags 2 days; use 3 to be safe
      const end = new Date(now)
      end.setDate(end.getDate() - 3)
      const endDate = end.toISOString().slice(0, 10)

      // If endDate is before startDate (very early January), skip
      if (endDate < startDate) return

      const cacheKey = `sunshineCache_${year}`
      const today = todayStr()

      try {
        const cached = JSON.parse(localStorage.getItem(cacheKey))
        if (cached?.date === today) {
          if (!cancelled) setData({ year, ...cached })
          return
        }
      } catch (_) { /* ignore */ }

      try {
        const results = await Promise.all(
          CITIES.map(async (city) => {
            const res = await fetch(buildUrl(city, startDate, endDate))
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const json = await res.json()
            const seconds = json.daily.sunshine_duration.reduce((a, b) => a + (b ?? 0), 0)
            return { id: city.id, hours: Math.round(seconds / 3600) }
          })
        )

        if (!cancelled) {
          const stockholm = results.find(r => r.id === 'stockholm').hours
          const valencia  = results.find(r => r.id === 'valencia').hours
          const payload = { date: today, stockholm, valencia }
          try { localStorage.setItem(cacheKey, JSON.stringify(payload)) } catch (_) { /* ignore */ }
          setData({ year, ...payload })
        }
      } catch (err) {
        console.warn('Sunshine fetch failed:', err)
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [])

  return data
}
