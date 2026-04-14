import styles from './WhyValencia.module.css'

function fmt(diff, unit, posLabel, negLabel) {
  const sign = diff > 0 ? '+' : ''
  const label = diff > 0 ? posLabel : negLabel
  return { value: `${sign}${diff} ${unit}`, label }
}

function fmtMinutes(diff) {
  const sign = diff > 0 ? '+' : ''
  const abs = Math.abs(diff)
  const h = Math.floor(abs / 60)
  const m = abs % 60
  const time = h > 0 ? `${h}h ${m}min` : `${m}min`
  const label = diff > 0 ? 'längre dag' : 'kortare dag'
  return { value: `${sign}${time}`, label }
}

export default function WhyValencia({ stockholm, valencia }) {
  if (!stockholm || !valencia) return null

  const tempDiff = valencia.temperature - stockholm.temperature
  const windDiff = valencia.windSpeed - stockholm.windSpeed
  const dayDiff = valencia.daylightMinutes - stockholm.daylightMinutes

  const temp = fmt(tempDiff, '°', 'varmare', 'kallare')
  const wind = fmt(windDiff, 'km/h', 'mer vind', 'lugnare vind')
  const day = fmtMinutes(dayDiff)

  return (
    <section className={styles.section}>
      <h2 className={styles.title}>Varför man ska bo i Valencia</h2>

      <div className={styles.rows}>
        <Row icon="🌡️" label="Temperatur" value={temp.value} detail={temp.label} />
        <Row icon="🌅" label="Dagslängd" value={day.value} detail={day.label} />
        <Row icon="💨" label="Vind" value={wind.value} detail={wind.label} />
      </div>

      <p className={styles.fact}>
        Kom ihåg att Valencia har <strong>130 fler soldagar</strong> per år än Stockholm
      </p>
    </section>
  )
}

function Row({ icon, label, value, detail }) {
  return (
    <div className={styles.row}>
      <div className={styles.rowLeft}>
        <span className={styles.rowIcon}>{icon}</span>
        <span className={styles.rowLabel}>{label}</span>
      </div>
      <div className={styles.rowRight}>
        <span className={styles.rowValue}>{value}</span>
        <span className={styles.rowDetail}>{detail}</span>
      </div>
    </div>
  )
}
