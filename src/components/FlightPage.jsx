import { useFlights } from '../useFlights'
import styles from './FlightPage.module.css'

function yesterday() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toLocaleDateString('sv-SE', { day: 'numeric', month: 'long' })
}

export default function FlightPage() {
  const { data, loading, error } = useFlights()

  const arlanda  = data?.arlanda
  const valencia = data?.valencia

  const diff = arlanda?.count != null && valencia?.count != null
    ? arlanda.count - valencia.count
    : null

  return (
    <section className={styles.section}>
      <div className={styles.heading}>
        <h2 className={styles.title}>Flyg</h2>
        <p className={styles.sub}>Avgångar {yesterday()} (UTC)</p>
      </div>

      {loading && <p className={styles.loading}>Hämtar flygdata…</p>}
      {error   && <p className={styles.err}>⚠️ Kunde inte hämta data</p>}

      {data && (
        <>
          <div className={styles.cards}>
            <AirportCard airport={arlanda}  icon="🇸🇪" />
            <AirportCard airport={valencia} icon="🇪🇸" />
          </div>

          {diff != null && (
            <div className={styles.verdict}>
              {diff > 0
                ? <>Arlanda hade <strong>{diff} fler avgångar</strong> än Valencia igår</>
                : diff < 0
                ? <>Valencia hade <strong>{Math.abs(diff)} fler avgångar</strong> än Arlanda igår</>
                : <>Lika många avgångar igår</>
              }
            </div>
          )}

          <p className={styles.note}>
            Källa:{' '}
            <a href="https://opensky-network.org" target="_blank" rel="noopener noreferrer">
              OpenSky Network
            </a>{' '}
            · Historisk ADS-B-data, publiceras nattligen
          </p>
        </>
      )}
    </section>
  )
}

function AirportCard({ airport, icon }) {
  return (
    <div className={styles.card}>
      <span className={styles.flag}>{icon}</span>
      <p className={styles.airportName}>{airport?.name ?? '–'}</p>
      <p className={styles.count}>
        {airport?.count != null ? airport.count : '–'}
      </p>
      <p className={styles.countLabel}>avgångar</p>
    </div>
  )
}
