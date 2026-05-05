import { money } from '../utils/format'
import './FactoryPanel.css'

function reserveClass(label = '') {
  const upper = label.toUpperCase()
  if (upper.includes('LOW')) return 'fp-badge fp-badge-yellow'
  if (upper.includes('HIGH')) return 'fp-badge fp-badge-green'
  return 'fp-badge fp-badge-neutral'
}

export default function FactoryPanel({ result }) {
  if (!result?.factory_explanation) return null

  const exp = result.factory_explanation

  return (
    <div className="fp-panel">
      <h2 className="fp-title">Factory Agent (PPO)</h2>

      <div className="fp-badge-wrap">
        <span className={reserveClass(exp.reserve_label)}>
          {exp.reserve_label || 'Reserve Strategy'}
        </span>
      </div>

      <div className="fp-list">
        <p className="fp-item">
          <strong className="fp-label">Reserve Factor:</strong>{' '}
          {Number(exp.reserve_factor ?? 0).toFixed(2)}x
        </p>

        <p className="fp-item">
          <strong className="fp-label">Release Factor:</strong>{' '}
          {Number(exp.release_factor ?? 0).toFixed(2)}x
        </p>

        <p className="fp-item">
          <strong className="fp-label">Factory Profit:</strong>{' '}
          <span className="fp-profit">
            {money(exp.factory_profit)}
          </span>
        </p>

        {Array.isArray(exp.lines) && exp.lines.length > 0 && (
          <ul className="fp-points">
            {exp.lines.map((line, idx) => (
              <li key={idx}>{line}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}