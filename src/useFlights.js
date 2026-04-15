import { useState, useEffect } from 'react'

const AIRPORTS = [
  { id: 'arlanda',  icao: 'ESSA', name: 'Stockholm Arlanda' },
  { id: 'valencia', icao: 'LEVC', name: 'Valencia' },
]

// Scheduled daily departures by IATA traffic season
// Source: Swedavia årsredovisning 2023, AENA estadísticas 2023
// Summer schedule: late March – late October
// Winter schedule: late October – late March
const SCHEDULE = {
  arlanda:  { summer: 280, winter: 185 },
  valencia: { summer: 160, winter: 70  },
}

function isSummerSchedule() {
  const m = new Date().getMonth() + 1  // 1-12
  return m >= 4 && m <= 10
}

function scheduledCount(id) {
  return isSummerSchedule() ? SCHEDULE[id].summer : SCHEDULE[id].winter
}

function twoDaysAgo() {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() - 2)
  d.setUTCHours(0, 0, 0, 0)
  const begin = Math.floor(d.getTime() / 1000)
  const end   = begin + 86400
  const label = d.toLocaleDateString('sv-SE', { day: 'numeric', month: 'long' })
  return { begin, end, label }
}

export function useFlights() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const CACHE_KEY = 'flightsCache_v3'
      const today     = new Date().toISOString().slice(0, 10)

      // Serve daily cache (refreshes at midnight – "ändras på natten")
      try {
        const c = JSON.parse(localStorage.getItem(CACHE_KEY))
        if (c?.date === today) {
          if (!cancelled) { setData(c.data); setLoading(false) }
          return
        }
      } catch (_) {}

      const { begin, end, label } = twoDaysAgo()

      // Try OpenSky historical API (requires data to be ≥48 h old)
      const results = await Promise.allSettled(
        AIRPORTS.map(async ({ id, icao, name }) => {
          const url = `https://opensky-network.org/api/flights/departure?airport=${icao}&begin=${begin}&end=${end}`
          const res = await fetch(url, { signal: AbortSignal.timeout(8000) })
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          const json = await res.json()
          // Sanity-check: a major airport should have at least 30 flights
          if (!Array.isArray(json) || json.length < 30) throw new Error('implausible')
          return { id, name, count: json.length, live: true, dateLabel: label }
        })
      )

      if (cancelled) return

      const obj = {}
      let anyLive = false
      AIRPORTS.forEach(({ id, name }, i) => {
        const r = results[i]
        if (r.status === 'fulfilled') {
          obj[id]  = r.value
          anyLive  = true
        } else {
          obj[id] = { id, name, count: scheduledCount(id), live: false, dateLabel: null }
        }
      })
      obj.anyLive = anyLive

      try { localStorage.setItem(CACHE_KEY, JSON.stringify({ date: today, data: obj })) } catch (_) {}
      setData(obj)
      setLoading(false)
    }

    load()
    return () => { cancelled = true }
  }, [])

  return { data, loading }
}
