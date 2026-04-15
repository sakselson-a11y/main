import { useState, useRef } from 'react'
import styles from './Carousel.module.css'

const LABELS = ['Stockholm', 'Valencia', 'Jämförelse', 'Priser']

export default function Carousel({ slides }) {
  const [current, setCurrent] = useState(0)
  const touchX = useRef(null)

  function goTo(i) { setCurrent(Math.max(0, Math.min(slides.length - 1, i))) }

  function onTouchStart(e) { touchX.current = e.touches[0].clientX }
  function onTouchEnd(e) {
    if (touchX.current === null) return
    const dx = e.changedTouches[0].clientX - touchX.current
    if (dx < -40) goTo(current + 1)
    else if (dx > 40) goTo(current - 1)
    touchX.current = null
  }

  return (
    <div className={styles.wrapper}>
      {/* Dot navigation */}
      <nav className={styles.dots} aria-label="Sidor">
        {LABELS.map((label, i) => (
          <button
            key={label}
            className={i === current ? styles.dotActive : styles.dot}
            onClick={() => goTo(i)}
            aria-label={label}
            title={label}
          >
            <span className={styles.dotLabel}>{label}</span>
          </button>
        ))}
      </nav>

      {/* Slides */}
      <div
        className={styles.viewport}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      >
        <div
          className={styles.track}
          style={{ transform: `translateX(-${current * 100}%)` }}
        >
          {slides.map((slide, i) => (
            <div key={i} className={styles.slide}>
              {slide}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
