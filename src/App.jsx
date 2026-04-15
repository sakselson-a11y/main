import { useWeather } from './useWeather'
import { useWaterTemp } from './useWaterTemp'
import WeatherCard from './components/WeatherCard'
import WhyValencia from './components/WhyValencia'
import PriceTable from './components/PriceTable'
import styles from './App.module.css'

export default function App() {
  const { data, loading, error } = useWeather()
  const waterTemp = useWaterTemp()

  const stockholm = data?.find(d => d.city.id === 'stockholm')
  const valencia = data?.find(d => d.city.id === 'valencia')

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <h1 className={styles.title}>¿Por qué Valencia?</h1>
        <p className={styles.subtitle}>Aktuella jämförelser · Uppdateras automatiskt</p>
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
          <>
            <div className={styles.cards}>
              {data.map((item) => (
                <WeatherCard key={item.city.id} data={item} />
              ))}
            </div>
            <WhyValencia stockholm={stockholm} valencia={valencia} waterTemp={waterTemp} />
            <PriceTable />
          </>
        )}
      </main>

      <footer className={styles.footer}>
        Källa: <a href="https://open-meteo.com" target="_blank" rel="noopener noreferrer">Open-Meteo</a>
      </footer>
    </div>
  )
}
