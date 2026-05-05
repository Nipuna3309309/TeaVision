import { money } from '../utils/format'
import './BuyerPanel.css'

function badgeClassByAction(actionIdx) {
  const a = Number(actionIdx)
  if (Number.isFinite(a)) {
    if (a >= 2) return 'byp-badge byp-badge-green'
    return 'byp-badge byp-badge-yellow'
  }
  return 'byp-badge byp-badge-neutral'
}

function titleImplies(title = '') {
  const t = String(title).toUpperCase()
  if (t.includes('WAIT')) return 'WAIT'
  if (t.includes('CAUTIOUS')) return 'CAUTIOUS'
  if (t.includes('COMPETITIVE')) return 'COMPETITIVE'
  if (t.includes('VERY AGGRESSIVE')) return 'VERY_AGGRESSIVE'
  return 'UNKNOWN'
}

export default function BuyerPanel({ result }) {
  if (!result?.buyer_explanation) return null

  const exp = result.buyer_explanation

  const actionIdx =
    exp?.action_meta?.action_idx ?? result?.buyer_action ?? null

  const badgeCls = badgeClassByAction(actionIdx)

  const title = exp?.action_meta?.title || 'Buyer Action'
  const meaning = exp?.action_meta?.meaning || '-'
  const reason = exp?.action_meta?.reason || '-'

  const net = Number(exp?.net_profit_estimate ?? 0)
  const profitCls = net >= 0 ? 'byp-profit-positive' : 'byp-profit-negative'

  const implied = titleImplies(title)
  const actionType = Number.isFinite(Number(actionIdx))
    ? (
        Number(actionIdx) === 0 ? 'WAIT' :
        Number(actionIdx) === 1 ? 'CAUTIOUS' :
        Number(actionIdx) === 2 ? 'COMPETITIVE' :
        'VERY_AGGRESSIVE'
      )
    : 'UNKNOWN'

  const mismatch =
    implied !== 'UNKNOWN' && actionType !== 'UNKNOWN' && implied !== actionType

  return (
    <div className="byp-panel">
      <div className="byp-header">
        <h2 className="byp-title">Buyer Agent (DQN)</h2>

        {Number.isFinite(Number(actionIdx)) && (
          <span className="byp-action-id">action #{Number(actionIdx)}</span>
        )}
      </div>

      <div className="byp-top-row">
        <span className={badgeCls}>{title}</span>

        {mismatch && (
          <span className="byp-mismatch">
            ⚠️ Label mismatch (title says {implied}, action is {actionType})
          </span>
        )}
      </div>

      <div className="byp-list">
        <p className="byp-item">
          <strong className="byp-label">Meaning:</strong>{' '}
          {meaning}
        </p>

        <p className="byp-item">
          <strong className="byp-label">Decision Reason:</strong>{' '}
          {reason}
        </p>

        <p className="byp-item">
          <strong className="byp-label">Net Profit Estimate:</strong>{' '}
          <span className={`byp-profit ${profitCls}`}>
            {money(net)}
          </span>
        </p>

        {Array.isArray(exp.context) && exp.context.length > 0 && (
          <ul className="byp-points">
            {exp.context.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        )}

        <div className="byp-muted-rule">
          {exp.quote && <p className="byp-quote">{exp.quote}</p>}
        </div>
      </div>
    </div>
  )
}