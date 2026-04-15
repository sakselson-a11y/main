import { useState, useEffect } from 'react'

const CITIES = [
  { id: 'stockholm', lat: 59.3293, lon: 18.0686, timezone: 'Europe/Stockholm' },
  { id: 'valencia',  lat: 39.4699, lon: -0.3763, timezone: 'Europe/Madrid'   },
]

function buildUrl({ lat, lon, timezone }, startDate, endDate) {
  const params = new URLSearchParams({
    latitude: lat,
    longitude: lon,
    start_date: startDate,
    end_date:   endDate,
    daily:      'precipitation_sum',
    timezone,
  })
  return `https://archive-api.open-meteo.com/v1/archive?${params}`
}

export function useRainyDays() {
  const [data, setData] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      const now  = new Date()
      const year = now.getFullYear()
      const startDate = `${year}-01-01`

      // Archive lags ~3 days
      const end = new Date(now)
      end.setDate(end.getDate() - 3)
      const endDate = end.toISOString().slice(0, 10)

      if (endDate < startDate) return

      const cacheKey = `rainyDaysCache_${year}`
      const today    = now.toISOString().slice(0, 10)

      try {
        const cached = JSON.parse(localStorage.getItem(cacheKey))
        if (cached?.date === today) {
          if (!cancelled) setData({ year, ...cached })
          return
        }
      } catch (_) {}

      try {
        const results = await Promise.all(
          CITIES.map(async (city) => {
            const res = await fetch(buildUrl(city, startDate, endDate))
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const json = await res.json()
            const days = json.daily.precipitation_sum
              .filter(v => v != null && v >= 1).length
            return { id: city.id, days }
          })
        )

        if (!cancelled) {
          const stockholm = results.find(r => r.id === 'stockholm').days
          const valencia  = results.find(r => r.id === 'valencia').days
          const payload   = { date: today, stockholm, valencia }
          try { localStorage.setItem(cacheKey, JSON.stringify(payload)) } catch (_) {}
          setData({ year, ...payload })
        }
      } catch (err) {
        console.warn('Rainy days fetch failed:', err)
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [])

  return data
}
