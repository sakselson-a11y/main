import { useState, useEffect } from 'react'

const AIRPORTS = [
  { id: 'arlanda',  icao: 'ESSA', name: 'Stockholm Arlanda' },
  { id: 'valencia', icao: 'LEVC', name: 'Valencia' },
]

// International-only scheduled daily departures by IATA traffic season
// Source: Swedavia årsredovisning 2023, AENA estadísticas 2023
// (Total minus estimated domestic: ~50/day ARN, ~25/day VLC)
// Summer schedule: late March – late October
// Winter schedule: late October – late March
const SCHEDULE = {
  arlanda:  { summer: 230, winter: 145 },
  valencia: { summer: 135, winter: 52  },
}

function isSummerSchedule() {
  const m = new Date().getMonth() + 1
  return m >= 4 && m <= 10
}

function scheduledCount(id) {
  return isSummerSchedule() ? SCHEDULE[id].summer : SCHEDULE[id].winter
}

function buildScheduleData() {
  const obj = { anyLive: false }
  AIRPORTS.forEach(({ id, name }) => {
    obj[id] = { id, name, count: scheduledCount(id), live: false, dateLabel: null }
  })
  return obj
}

// Filter out domestic flights based on destination ICAO prefix
// ES = Sweden, LE = Spain mainland + Balearics, GC = Canary Islands
function isInternational(flight, departureIcao) {
  const dest = flight.estArrivalAirport
  if (!dest) return true
  if (departureIcao.startsWith('ES')) return !dest.startsWith('ES')
  if (departureIcao.startsWith('LE')) return !dest.startsWith('LE') && !dest.startsWith('GC')
  return true
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

const CACHE_KEY = 'flightsCache_v4'

function readCache() {
  try {
    const c = JSON.parse(localStorage.getItem(CACHE_KEY))
    const today = new Date().toISOString().slice(0, 10)
    if (c?.date === today) return c.data
  } catch (_) {}
  return null
}

export function useFlights() {
  // Initialise synchronously from cache or schedule – no spinner needed
  const [data, setData] = useState(() => readCache() ?? buildScheduleData())

  useEffect(() => {
    let cancelled = false

    // If we already have cached live data for today, nothing more to do
    const cached = readCache()
    if (cached?.anyLive) return

    // Try OpenSky in the background; silently keep schedule data on any failure
    async function tryLive() {
      try {
        const { begin, end, label } = twoDaysAgo()

        const results = await Promise.allSettled(
          AIRPORTS.map(async ({ id, icao, name }) => {
            const url =
              `https://opensky-network.org/api/flights/departure` +
              `?airport=${icao}&begin=${begin}&end=${end}`
            const res = await fetch(url, { signal: AbortSignal.timeout(8000) })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const json = await res.json()
            if (!Array.isArray(json) || json.length < 30) throw new Error('implausible')
            const intl = json.filter(f => isInternational(f, icao))
            return { id, name, count: intl.length, live: true, dateLabel: label }
          })
        )

        if (cancelled) return

        const anyLive = results.some(r => r.status === 'fulfilled')
        if (!anyLive) return  // all failed – keep schedule data already shown

        const obj = { anyLive: true }
        AIRPORTS.forEach(({ id, name }, i) => {
          const r = results[i]
          obj[id] = r.status === 'fulfilled'
            ? r.value
            : { id, name, count: scheduledCount(id), live: false, dateLabel: null }
        })

        const today = new Date().toISOString().slice(0, 10)
        try { localStorage.setItem(CACHE_KEY, JSON.stringify({ date: today, data: obj })) } catch (_) {}
        setData(obj)
      } catch (_) {
        // Network error or anything else – schedule data stays on screen
      }
    }

    tryLive()
    return () => { cancelled = true }
  }, [])

  return { data }
}
