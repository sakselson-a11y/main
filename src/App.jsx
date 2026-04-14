import { useWeather } from './useWeather'
import WeatherCard from './components/WeatherCard'
import styles from './App.module.css'

export default function App() {
  const { data, loading, error } = useWeather()

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <h1 className={styles.title}>Väderappen</h1>
        <p className={styles.subtitle}>Aktuellt väder · Uppdateras automatiskt</p>
      </header>

      <main className={styles.main}>
        {loading && (
          <div className={styles.state}>
            <span className={styles.spinner} aria-hidden="true" />
            <p>Hämtar väderdata…</p>
          </div>
        )}

        {error && (
          <div className={styles.state}>
            <p className={styles.error}>⚠️ Kunde inte hämta data: {error}</p>
          </div>
        )}

        {data && (
          <div className={styles.cards}>
            {data.map((item) => (
              <WeatherCard key={item.city.id} data={item} />
            ))}
          </div>
        )}
      </main>

      <footer className={styles.footer}>
        Källa: <a href="https://open-meteo.com" target="_blank" rel="noopener noreferrer">Open-Meteo</a>
      </footer>
    </div>
  )
}
