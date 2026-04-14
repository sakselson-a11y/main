import { getWeatherInfo, windDirection } from '../weatherCodes'
import styles from './WeatherCard.module.css'

export default function WeatherCard({ data }) {
  const { city, temperature, weatherCode, windSpeed, windDirection: windDeg,
          avgTemp, maxTemp, minTemp, sunrise, sunset } = data
  const { label, icon } = getWeatherInfo(weatherCode)
  const windDir = windDirection(windDeg)

  return (
    <article className={`${styles.card} ${styles[city.id]}`}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.cityName}>{city.name}</h2>
          <p className={styles.country}>{city.country}</p>
        </div>
        <span className={styles.weatherIcon} role="img" aria-label={label}>
          {icon}
        </span>
      </header>

      <div className={styles.tempMain}>
        <span className={styles.temp}>{temperature}°</span>
        <span className={styles.condition}>{label}</span>
      </div>

      <div className={styles.grid}>
        <Stat label="Medeltemp" value={`${avgTemp > 0 ? '+' : ''}${avgTemp}°`} icon="📊" />
        <Stat label="Max / Min" value={`${maxTemp > 0 ? '+' : ''}${maxTemp}° / ${minTemp > 0 ? '+' : ''}${minTemp}°`} icon="🌡️" />
        <Stat label="Vind" value={`${windSpeed} km/h ${windDir}`} icon="💨" />
        <Stat label="Soluppgång" value={sunrise} icon="🌅" />
        <Stat label="Solnedgång" value={sunset} icon="🌇" />
      </div>
    </article>
  )
}

function Stat({ label, value, icon }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statIcon}>{icon}</span>
      <div>
        <p className={styles.statLabel}>{label}</p>
        <p className={styles.statValue}>{value}</p>
      </div>
    </div>
  )
}
