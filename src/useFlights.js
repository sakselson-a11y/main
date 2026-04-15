import { useState, useEffect } from 'react'

const AIRPORTS = [
  { id: 'arlanda',  icao: 'ESSA', name: 'Stockholm Arlanda' },
  { id: 'valencia', icao: 'LEVC', name: 'Valencia' },
]

function yesterdayRange() {
  const d = new Date()
  d.setUTCHours(0, 0, 0, 0)
  const end   = Math.floor(d.getTime() / 1000)          // today midnight UTC
  const begin = end - 86400                              // 24 h earlier
  return { begin, end }
}

export function useFlights() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchAll() {
      const cacheKey = 'flightsCache_v1'
      const maxAge   = 6 * 60 * 60 * 1000   // re-fetch after 6 h

      try {
        const cached = JSON.parse(localStorage.getItem(cacheKey))
        if (cached && Date.now() - cached.ts < maxAge) {
          if (!cancelled) { setData(cached.data); setLoading(false) }
          return
        }
      } catch (_) {}

      const { begin, end } = yesterdayRange()

      try {
        const results = await Promise.allSettled(
          AIRPORTS.map(async ({ id, icao, name }) => {
            const url =
              `https://opensky-network.org/api/flights/departure` +
              `?airport=${icao}&begin=${begin}&end=${end}`
            const res = await fetch(url)
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const json = await res.json()
            return { id, name, count: Array.isArray(json) ? json.length : 0 }
          })
        )

        if (!cancelled) {
          const obj = {}
          AIRPORTS.forEach(({ id, name }, i) => {
            const r = results[i]
            obj[id] = r.status === 'fulfilled'
              ? r.value
              : { id, name, count: null }
          })
          try { localStorage.setItem(cacheKey, JSON.stringify({ ts: Date.now(), data: obj })) } catch (_) {}
          setData(obj)
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) { setError(err.message); setLoading(false) }
      }
    }

    fetchAll()
    return () => { cancelled = true }
  }, [])

  return { data, loading, error }
}
