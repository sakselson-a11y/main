import styles from './PriceTable.module.css'

// Priser baserade på Numbeo-data (apr 2025–apr 2026)
// Valencia-priser omräknade från EUR till SEK (kurs ~11,5)
const PRICES = [
  { icon: '🍺', item: '1 öl på bar (33 cl)',              sthlm: 85,     val: 35    },
  { icon: '🍽️', item: 'Middag för fyra på restaurang',   sthlm: 1_400,  val: 800   },
  { icon: '🧈', item: '1 kg smör (mataffär)',             sthlm: 80,     val: 23    },
  { icon: '☕', item: 'Cappuccino på café',               sthlm: 55,     val: 26    },
  { icon: '🥤', item: 'Coca-Cola på café (33 cl)',        sthlm: 42,     val: 22    },
  { icon: '🍕', item: 'Pizza på restaurang',              sthlm: 135,    val: 75    },
  { icon: '🥛', item: '1 liter mjölk (mataffär)',         sthlm: 16,     val: 12    },
  { icon: '🍦', item: 'Glass, 2 kulor',                   sthlm: 45,     val: 15    },
  { icon: '🎬', item: 'Bio, 1 biljett',                   sthlm: 140,    val: 103   },
  { icon: '🏠', item: '3-rums hyreslägenhet/mån',         sthlm: 18_000, val: 12_700},
]

function kr(n) {
  return n.toLocaleString('sv-SE') + ' kr'
}

export default function PriceTable() {
  return (
    <section className={styles.section}>
      <h2 className={styles.title}>Priser i Valencia vs Stockholm</h2>

      <div className={styles.rows}>
        {PRICES.map(({ icon, item, sthlm, val }) => {
          const diff = val - sthlm
          const cheaper = diff < 0
          return (
            <div key={item} className={styles.row}>
              <div className={styles.rowLeft}>
                <span className={styles.icon}>{icon}</span>
                <span className={styles.item}>{item}</span>
              </div>
              <div className={styles.rowRight}>
                <span className={cheaper ? styles.cheaper : styles.dearer}>
                  {cheaper ? '−' : '+'}{kr(Math.abs(diff))}
                </span>
                <span className={styles.label}>
                  {cheaper ? 'billigare' : 'dyrare'}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      <p className={styles.source}>
        Ungefärliga priser baserade på{' '}
        <a href="https://www.numbeo.com/cost-of-living/compare_cities.jsp?country1=Spain&city1=Valencia&country2=Sweden&city2=Stockholm"
           target="_blank" rel="noopener noreferrer">Numbeo</a>{' '}
        (EUR→SEK ~11,5). Uppdateras manuellt.
      </p>
    </section>
  )
}
