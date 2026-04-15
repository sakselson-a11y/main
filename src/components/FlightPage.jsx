import { useFlights } from '../useFlights'
import styles from './FlightPage.module.css'

export default function FlightPage() {
  const { data } = useFlights()

  const arlanda  = data?.arlanda
  const valencia = data?.valencia
  const isLive   = data?.anyLive

  const diff = arlanda?.count != null && valencia?.count != null
    ? arlanda.count - valencia.count
    : null

  const subLabel = isLive
    ? `Faktiska internationella avgångar ${arlanda?.dateLabel ?? ''} (ADS-B)`
    : 'Planerade internationella avgångar per dygn'

  return (
    <section className={styles.section}>
      <div className={styles.heading}>
        <h2 className={styles.title}>Flyg</h2>
        <p className={styles.sub}>{subLabel}</p>
      </div>

      <div className={styles.cards}>
        <AirportCard airport={arlanda} icon="🇸🇪" />
        <AirportCard airport={valencia} icon="🇪🇸" />
      </div>

      {diff != null && (
        <div className={styles.verdict}>
          {isLive
            ? diff > 0
              ? <>Arlanda hade <strong>{diff} fler avgångar</strong> än Valencia den dagen</>
              : diff < 0
              ? <>Valencia hade <strong>{Math.abs(diff)} fler avgångar</strong> än Arlanda den dagen</>
              : <>Lika många avgångar den dagen</>
            : diff > 0
            ? <>Arlanda har <strong>{diff} fler planerade avgångar</strong> per dag än Valencia</>
            : diff < 0
            ? <>Valencia har <strong>{Math.abs(diff)} fler planerade avgångar</strong> per dag än Arlanda</>
            : <>Lika många planerade avgångar per dag</>
          }
        </div>
      )}

      <p className={styles.note}>
        {isLive
          ? <>Källa: <a href="https://opensky-network.org" target="_blank" rel="noopener noreferrer">OpenSky Network</a> · Historisk ADS-B-data, publiceras nattligen</>
          : <>Källa: Swedavia &amp; AENA årsstatistik 2023 · Schemasnitt, varierar per säsong</>
        }
      </p>
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
      <p className={styles.countLabel}>avgångar/dag</p>
    </div>
  )
}
