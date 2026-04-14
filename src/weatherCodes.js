// WMO Weather interpretation codes
// https://open-meteo.com/en/docs#weathervariables
export function getWeatherInfo(code) {
  const map = {
    0:  { label: 'Klart',               icon: '☀️' },
    1:  { label: 'Mestadels klart',     icon: '🌤️' },
    2:  { label: 'Delvis molnigt',      icon: '⛅' },
    3:  { label: 'Mulet',               icon: '☁️' },
    45: { label: 'Dimma',               icon: '🌫️' },
    48: { label: 'Isbildande dimma',    icon: '🌫️' },
    51: { label: 'Lätt duggregn',       icon: '🌦️' },
    53: { label: 'Måttligt duggregn',   icon: '🌦️' },
    55: { label: 'Kraftigt duggregn',   icon: '🌦️' },
    61: { label: 'Lätt regn',           icon: '🌧️' },
    63: { label: 'Måttligt regn',       icon: '🌧️' },
    65: { label: 'Kraftigt regn',       icon: '🌧️' },
    71: { label: 'Lätt snöfall',        icon: '🌨️' },
    73: { label: 'Måttligt snöfall',    icon: '❄️' },
    75: { label: 'Kraftigt snöfall',    icon: '❄️' },
    77: { label: 'Snökorn',             icon: '🌨️' },
    80: { label: 'Lätta regnskurar',    icon: '🌦️' },
    81: { label: 'Måttliga regnskurar', icon: '🌧️' },
    82: { label: 'Kraftiga regnskurar', icon: '⛈️' },
    85: { label: 'Lätta snöbyar',       icon: '🌨️' },
    86: { label: 'Kraftiga snöbyar',    icon: '❄️' },
    95: { label: 'Åskväder',            icon: '⛈️' },
    96: { label: 'Åskväder med hagel',  icon: '⛈️' },
    99: { label: 'Åskväder med hagel',  icon: '⛈️' },
  }
  return map[code] ?? { label: 'Okänt', icon: '🌡️' }
}

export function windDirection(deg) {
  const dirs = ['N','NO','O','SO','S','SV','V','NV']
  return dirs[Math.round(deg / 45) % 8]
}
