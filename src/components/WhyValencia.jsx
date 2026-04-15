import { useSunshineHours } from '../useSunshineHours'
import styles from './WhyValencia.module.css'

function fmt(diff, unit, posLabel, negLabel) {
  const sign = diff > 0 ? '+' : ''
  const label = diff > 0 ? posLabel : negLabel
  return { value: `${sign}${diff} ${unit}`, label }
}

export default function WhyValencia({ stockholm, valencia, waterTemp }) {
  if (!stockholm || !valencia) return null

  const sunshine = useSunshineHours()

  const tempDiff = valencia.temperature - stockholm.temperature
  const windDiff = valencia.windSpeed - stockholm.windSpeed

  const temp  = fmt(tempDiff, '°', 'varmare', 'kallare')
  const wind  = fmt(windDiff, 'km/h', 'mer vind', 'lugnare vind')

  const valWater = waterTemp?.valencia
  const sthWater = waterTemp?.stockholm
  const waterDiff = valWater != null && sthWater != null ? valWater - sthWater : null
  const water = waterDiff != null
    ? fmt(waterDiff, '°', 'varmare vatten', 'kallare vatten')
    : null

  const sunDiff = sunshine ? sunshine.valencia - sunshine.stockholm : null

  const today = new Date().toLocaleDateString('sv-SE', {
    day: 'numeric', month: 'long', year: 'numeric'
  })

  return (
    <section className={styles.section}>
      <div className={styles.heading}>
        <h2 className={styles.title}>Varför man ska bo i Valencia</h2>
        <p className={styles.todayBadge}>Väder- och baddata från idag · {today}</p>
      </div>

      <div className={styles.rows}>
        <Row icon="🌡️" label="Temperatur" value={temp.value} detail={temp.label} />
        <Row icon="💨" label="Vind" value={wind.value} detail={wind.label} />
        <Row
          icon="🌊"
          label="Badtemperatur"
          value={water ? water.value : '–'}
          detail={water ? water.label : ''}
          sub={valWater != null && sthWater != null
            ? `Malvarrosa ${valWater}° · Smedsuddsbadet ${sthWater}°`
            : 'Hämtar…'}
        />
      </div>

      <p className={styles.fact}>
        {sunshine && sunDiff != null
          ? <>Kom ihåg att Valencia har haft <strong>{sunDiff.toLocaleString('sv-SE')} fler soltimmar</strong> än Stockholm under {sunshine.year}</>
          : <>Hämtar soltimmar för {new Date().getFullYear()}…</>
        }
      </p>
    </section>
  )
}

function Row({ icon, label, value, detail, sub }) {
  return (
    <div className={styles.row}>
      <div className={styles.rowLeft}>
        <span className={styles.rowIcon}>{icon}</span>
        <div>
          <span className={styles.rowLabel}>{label}</span>
          {sub && <p className={styles.rowSub}>{sub}</p>}
        </div>
      </div>
      <div className={styles.rowRight}>
        <span className={styles.rowValue}>{value}</span>
        <span className={styles.rowDetail}>{detail}</span>
      </div>
    </div>
  )
}
