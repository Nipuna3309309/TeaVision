import { integer, money, percent } from '../utils/format'
import './AuctionResultCard.css'

function InfoTooltip({ text }) {
  return (
    <span className="arc-tooltip-group">
      <span className="arc-tooltip-icon" aria-label="More information">
        i
      </span>

      <span className="arc-tooltip-box">
        {text}
      </span>
    </span>
  )
}

function RowLabel({ children, help }) {
  return (
    <div className="arc-row-label">
      <span className="arc-row-label-text">{children}</span>
      {help && <InfoTooltip text={help} />}
    </div>
  )
}

function normalizePercent(value) {
  const n = Number(value ?? 0)
  if (!Number.isFinite(n)) return 0
  return n <= 1 ? n * 100 : n
}

function signalMeta(signal) {
  if (signal === 1) return { text: 'Bullish (+1)', cls: 'arc-badge arc-badge-green' }
  if (signal === -1) return { text: 'Bearish (-1)', cls: 'arc-badge arc-badge-red' }
  return { text: 'Neutral (0)', cls: 'arc-badge arc-badge-neutral' }
}

function buyerActionClass(actionIdx) {
  const a = Number(actionIdx)
  if (!Number.isFinite(a)) return 'arc-badge arc-badge-neutral'
  if (a === 0) return 'arc-badge arc-badge-neutral'
  if (a === 1) return 'arc-badge arc-badge-yellow'
  return 'arc-badge arc-badge-green'
}

export default function AuctionResultCard({ result, lotVolume = 0 }) {
  if (!result) return null

  const signal = signalMeta(result.broker_signal)
  const commission = normalizePercent(result.commission_rate)
  const soldVolume = Number(result.sold_volume ?? 0)
  const unsoldVolume = Number(result.unsold_volume ?? 0)
  const totalVolume = Number(lotVolume || soldVolume + unsoldVolume || 0)
  const soldPct =
    totalVolume > 0 ? Math.min((soldVolume / totalVolume) * 100, 100) : 0

  return (
    <div className="arc-panel">
      <div className="arc-header">
        <h2 className="arc-title">Multi-Agent RL Auction Result</h2>
        <InfoTooltip text="This section shows the final auction outcome produced by the factory, broker, and buyer agents." />
      </div>

      <div className="arc-content">
        <div className="arc-result-row">
          <RowLabel help="Minimum price the factory is willing to accept for this lot.">
            Reserve Price
          </RowLabel>
          <strong className="arc-value">{money(result.reserve_price)}</strong>
        </div>

        <div className="arc-result-row">
          <RowLabel help="Price offered by the buyer agent for this tea lot.">
            Buyer Bid
          </RowLabel>
          <strong className="arc-value">{money(result.bid_price)}</strong>
        </div>

        <div className="arc-result-row">
          <RowLabel help="How much volume was successfully sold in the auction.">
            Sold Volume
          </RowLabel>
          <strong className="arc-value">{integer(soldVolume)} kg</strong>
        </div>

        <div className="arc-result-row">
          <RowLabel help="How much volume was not sold and remains after the auction.">
            Unsold Volume
          </RowLabel>
          <strong className="arc-value">{integer(unsoldVolume)} kg</strong>
        </div>

        <div className="arc-result-row">
          <div className="arc-inline-group">
            <RowLabel help="Broker commission percentage earned from the successful sale.">
              Commission Rate
            </RowLabel>
            <span className={signal.cls}>{signal.text}</span>
          </div>

          <strong className="arc-value">{percent(commission)}</strong>
        </div>

        <div className="arc-result-row">
          <RowLabel help="Estimated profit earned by the factory from this auction result.">
            Factory Profit
          </RowLabel>
          <strong className="arc-value arc-profit">{money(result.factory_profit)}</strong>
        </div>

        <div className="arc-result-row">
          <RowLabel help="Estimated profit earned by the broker from this auction result.">
            Broker Profit
          </RowLabel>
          <strong className="arc-value">{money(result.broker_profit)}</strong>
        </div>

        <div className="arc-result-row">
          <div className="arc-inline-group">
            <RowLabel help="Final decision taken by the buyer agent based on price and market conditions.">
              Buyer Action
            </RowLabel>
            <span className={buyerActionClass(result.buyer_action)}>
              {result.buyer_action_label}
            </span>
          </div>

          <span className={`arc-badge ${result.sold ? 'arc-badge-green' : 'arc-badge-yellow'}`}>
            {result.sold ? 'Sold' : 'Unsold'}
          </span>
        </div>
      </div>

      <div className="arc-progress-card">
        <div className="arc-progress-top">
          <div className="arc-progress-label">
            <span>Lot Release Progress</span>
            <InfoTooltip text="Shows what percentage of the total tea lot was sold in this auction." />
          </div>
          <span>{soldPct.toFixed(0)}%</span>
        </div>

        <div className="arc-progress-track">
          <div
            className="arc-progress-fill"
            style={{ width: `${soldPct}%` }}
          />
        </div>

        <div className="arc-progress-bottom">
          <span>Sold: {integer(soldVolume)} kg</span>
          <span>Unsold: {integer(unsoldVolume)} kg</span>
        </div>
      </div>
    </div>
  )
}