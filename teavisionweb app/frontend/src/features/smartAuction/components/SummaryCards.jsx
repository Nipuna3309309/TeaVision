import { money } from '../utils/format'
import './SummaryCards.css'

function toPercentNumber(value) {
  const n = Number(value ?? 0)
  if (!Number.isFinite(n)) return 0
  return n <= 1 ? n * 100 : n
}

function SmallInfo({ label }) {
  return (
    <div className="summary-top-card-label">
      <span>{label}</span>
      <span className="summary-info-dot">i</span>
    </div>
  )
}

export default function SummaryCards({ result }) {
  if (!result) return null

  const current = Number(result.current_price_used ?? result.current_price ?? 0)
  const forecast = Number(result.forecast_price ?? 0)
  const diffPct = current > 0 ? ((forecast - current) / current) * 100 : 0
  const confidence = toPercentNumber(result.confidence_score ?? 0)

  return (
    <div className="summary-cards-grid">
      <div className="summary-soft-card">
        <SmallInfo label="Current Market Price" />
        <div className="summary-hero-value">{money(current)}</div>
      </div>

      <div className="summary-soft-card">
        <SmallInfo label="Forecast Unit Price" />
        <div className="summary-hero-value">{money(forecast)}</div>

        <div className="summary-hero-subtext">
          Target Ref:{' '}
          <span className="summary-muted-strong">
            {result.target_date || result.target_sale_no || 'Upcoming sale'}
          </span>{' '}
          |{' '}
          <span className="summary-muted-strong">
            Week {result.target_sale_no ?? '-'} (approx.)
          </span>{' '}
          |{' '}
          <span
            className={`summary-diff ${
              diffPct >= 0 ? 'summary-diff-positive' : 'summary-diff-negative'
            }`}
          >
            {diffPct >= 0 ? '+' : ''}
            {diffPct.toFixed(2)}%
          </span>
        </div>
      </div>

      <div className="summary-soft-card">
        <div className="summary-top-card-label">Auction Status</div>

        <div className="summary-status-row">
          <div className="summary-status-text">
            {result.sold ? 'SOLD' : 'UNSOLD'}
          </div>

          <div
            className={`summary-status-icon ${
              result.sold
                ? 'summary-status-icon-sold'
                : 'summary-status-icon-unsold'
            }`}
          >
            {result.sold ? '✓' : '!'}
          </div>
        </div>

        {confidence > 0 && (
          <div className="summary-confidence">
            Confidence: <span>{confidence.toFixed(1)}%</span>
          </div>
        )}
      </div>
    </div>
  )
}