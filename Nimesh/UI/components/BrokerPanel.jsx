import { money } from '../utils/format'
import './BrokerPanel.css'

function signalClass(label = '') {
  const upper = label.toUpperCase()
  if (upper.includes('BULL')) return 'bp-badge bp-badge-green'
  if (upper.includes('BEAR')) return 'bp-badge bp-badge-red'
  return 'bp-badge bp-badge-neutral'
}

export default function BrokerPanel({ result }) {
  if (!result?.broker_explanation) return null

  const exp = result.broker_explanation

  return (
    <div className="bp-panel">
      <h2 className="bp-title">Broker Agent (PPO)</h2>

      <div className="bp-badge-wrap">
        <span className={signalClass(exp.signal_label)}>
          {exp.signal_label || 'Broker Signal'}
        </span>
      </div>

      <div className="bp-list">
        <p className="bp-item">
          <strong className="bp-label">Commission:</strong>{' '}
          {(Number(exp.commission_rate ?? 0) * 100).toFixed(2)}%
        </p>

        <p className="bp-item">
          <strong className="bp-label">Guidance:</strong> {exp.guidance}
        </p>

        <p className="bp-item">
          <strong className="bp-label">Broker Profit:</strong>{' '}
          <span className="bp-profit">{money(exp.broker_profit)}</span>
        </p>

        {Array.isArray(exp.lines) && exp.lines.length > 0 && (
          <ul className="bp-points">
            {exp.lines.map((line, idx) => (
              <li key={idx}>{line}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}