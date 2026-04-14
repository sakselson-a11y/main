import { useState, useEffect } from 'react'

const WATER_LOCATIONS = [
  {
    id: 'stockholm',
    // Baggensfjärden, Östersjön nära Stockholm – proxy för Mälarens badtemperatur
    lat: 59.30,
    lon: 18.20,
  },
  {
    id: 'valencia',
    // Playa de la Malvarrosa, Medelhavet
    lat: 39.4832,
    lon: -0.3254,
  },
]

function buildUrl({ lat, lon }) {
  const params = new URLSearchParams({
    latitude: lat,
    longitude: lon,
    current: 'sea_surface_temperature',
  })
  return `https://marine-api.open-meteo.com/v1/marine?${params}`
}

export function useWaterTemp() {
  const [data, setData] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchAll() {
      const results = await Promise.allSettled(
        WATER_LOCATIONS.map(async (loc) => {
          const res = await fetch(buildUrl(loc))
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          const json = await res.json()
          const temp = json.current?.sea_surface_temperature
          return { id: loc.id, temp: temp != null ? Math.round(temp) : null }
        })
      )
      if (!cancelled) {
        const obj = {}
        WATER_LOCATIONS.forEach((loc, i) => {
          const r = results[i]
          obj[loc.id] = r.status === 'fulfilled' ? r.value.temp : null
        })
        setData(obj)
      }
    }

    fetchAll()
    return () => { cancelled = true }
  }, [])

  return data
}
