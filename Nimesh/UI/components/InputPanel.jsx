import './InputPanel.css'

function InfoTooltip({ text }) {
  return (
    <span className="ip-tooltip">
      <span
        className="ip-tooltip-icon"
        aria-label="More information"
      >
        i
      </span>

      <span className="ip-tooltip-box">
        {text}
      </span>
    </span>
  )
}

function Label({ children, help }) {
  return (
    <label className="ip-field-label">
      <span>{children}</span>
      {help && <InfoTooltip text={help} />}
    </label>
  )
}

function SelectControl({ value, onChange, children }) {
  return (
    <div className="ip-select-wrap">
      <select
        value={value}
        onChange={onChange}
        className="ip-field-input ip-select"
      >
        {children}
      </select>

      <div className="ip-select-icon">
        <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.51a.75.75 0 01-1.08 0l-4.25-4.51a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </div>
    </div>
  )
}

const monthNames = [
  { value: 1, label: 'Jan' },
  { value: 2, label: 'Feb' },
  { value: 3, label: 'Mar' },
  { value: 4, label: 'Apr' },
  { value: 5, label: 'May' },
  { value: 6, label: 'Jun' },
  { value: 7, label: 'Jul' },
  { value: 8, label: 'Aug' },
  { value: 9, label: 'Sep' },
  { value: 10, label: 'Oct' },
  { value: 11, label: 'Nov' },
  { value: 12, label: 'Dec' },
]

export default function InputPanel({
  form,
  setForm,
  grades,
  onRun,
  onLearn,
  onReload,
  running,
  learning,
}) {
  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="ip-panel">
      <h2 className="ip-section-title">Inputs</h2>

      <div className="ip-body">
        <div className="ip-block">
          <Label help="How much tea lot volume will be sent to the auction.">
            Lot Volume
          </Label>
          <input
            type="number"
            className="ip-field-input"
            value={form.lot_volume}
            onChange={(e) => setField('lot_volume', Number(e.target.value || 0))}
          />
        </div>

        <div className="ip-block">
          <Label help="Select the factory elevation category for this tea lot.">
            Factory Elevation
          </Label>
          <SelectControl
            value={form.elevation}
            onChange={(e) => setField('elevation', e.target.value)}
          >
            <option value="Low">Low</option>
            <option value="Mid">Mid</option>
            <option value="High">High</option>
          </SelectControl>
        </div>

        <div className="ip-block">
          <Label help="Choose the tea grade that will be auctioned.">
            Tea Grade
          </Label>
          <SelectControl
            value={form.grade}
            onChange={(e) => setField('grade', e.target.value)}
          >
            {grades.length === 0 ? (
              <option value="">No grades found</option>
            ) : (
              grades.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))
            )}
          </SelectControl>
        </div>

        <div className="ip-block">
          <label className="ip-check-row">
            <input
              type="checkbox"
              checked={form.use_current_price}
              onChange={(e) => setField('use_current_price', e.target.checked)}
              className="ip-checkbox"
            />
            <span className="ip-check-text">
              Use Current Market Price
              <InfoTooltip text="Turn this on if the current market price is different from the normal predicted value." />
            </span>
          </label>

          {form.use_current_price && (
            <div className="ip-subcard">
              <div className="ip-subcard-head">
                <span>Current Market Price (Rs/unit)</span>
                <InfoTooltip text="Enter the latest market price per unit to guide the auction decision." />
              </div>
              <input
                type="number"
                step="0.01"
                className="ip-field-input ip-field-input-tall"
                value={form.current_price}
                onChange={(e) =>
                  setField('current_price', Number(e.target.value || 0))
                }
              />
            </div>
          )}
        </div>

        <div className="ip-grid-two">
          <div className="ip-block">
            <Label help="Expected demand level in the market for this tea lot.">
              Market Demand
            </Label>
            <SelectControl
              value={form.demand}
              onChange={(e) => setField('demand', e.target.value)}
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </SelectControl>
          </div>

          <div className="ip-block">
            <Label help="Competition level from other sellers or auction lots.">
              Competition
            </Label>
            <SelectControl
              value={form.competition}
              onChange={(e) => setField('competition', e.target.value)}
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </SelectControl>
          </div>
        </div>

        <div className="ip-block">
          <Label help="Weekly storage cost for keeping 1 kg before selling.">
            Storage Cost (Rs/kg/week)
          </Label>
          <input
            type="number"
            step="0.5"
            className="ip-field-input"
            value={form.storage_cost}
            onChange={(e) => setField('storage_cost', Number(e.target.value || 0))}
          />
        </div>

        <div className="ip-block">
          <label className="ip-check-row">
            <input
              type="checkbox"
              checked={form.use_production_cost}
              onChange={(e) => setField('use_production_cost', e.target.checked)}
              className="ip-checkbox"
            />
            <span className="ip-check-text">
              Set Production Cost
              <InfoTooltip text="Turn this on if you want to manually enter the production cost per unit." />
            </span>
          </label>

          {form.use_production_cost && (
            <div className="ip-block ip-block-nested">
              <Label help="Production cost per unit for this tea lot.">
                Production Cost (Rs/unit)
              </Label>
              <input
                type="number"
                className="ip-field-input"
                value={form.production_cost}
                onChange={(e) =>
                  setField('production_cost', Number(e.target.value || 0))
                }
              />
            </div>
          )}
        </div>

        <div className="ip-block">
          <div className="ip-period-head">
            <span>Period</span>
            <InfoTooltip text="Choose the target auction time period for the simulation." />
          </div>

          <div className="ip-grid-three">
            <div className="ip-block">
              <div className="ip-mini-head">
                <span>Year</span>
                <InfoTooltip text="Select the auction year." />
              </div>
              <SelectControl
                value={form.year}
                onChange={(e) => setField('year', Number(e.target.value))}
              >
                <option value={2023}>2023</option>
                <option value={2024}>2024</option>
                <option value={2025}>2025</option>
                <option value={2026}>2026</option>
              </SelectControl>
            </div>

            <div className="ip-block">
              <div className="ip-mini-head">
                <span>Month</span>
                <InfoTooltip text="Select the month of the target auction." />
              </div>
              <SelectControl
                value={form.month}
                onChange={(e) => setField('month', Number(e.target.value))}
              >
                {monthNames.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </SelectControl>
            </div>

            <div className="ip-block">
              <div className="ip-mini-head">
                <span>Week</span>
                <InfoTooltip text="Select which week in the month the auction belongs to." />
              </div>
              <SelectControl
                value={form.week_in_month}
                onChange={(e) => setField('week_in_month', Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5].map((w) => (
                  <option key={w} value={w}>
                    {w}
                  </option>
                ))}
              </SelectControl>
            </div>
          </div>
        </div>

        <div className="ip-learning-card">
          <div className="ip-learning-head">
            <h3 className="ip-learning-title">
              <span>Online Learning</span>
              <InfoTooltip text="These settings control how much extra learning each agent does before updating decisions." />
            </h3>

            <button
              type="button"
              onClick={onLearn}
              disabled={running || learning}
              className="ip-learning-run"
            >
              {learning ? 'Learning...' : 'Run'}
            </button>
          </div>

          <div className="ip-learning-body">
            <div className="ip-block">
              <Label help="Number of online learning steps for the buyer agent.">
                Buyer Online Learning Steps
              </Label>
              <input
                type="number"
                className="ip-field-input"
                value={form.buyer_online_steps}
                onChange={(e) =>
                  setField('buyer_online_steps', Number(e.target.value || 0))
                }
              />
            </div>

            <div className="ip-block">
              <Label help="Number of online learning steps for the factory agent.">
                Factory Online Learning Steps
              </Label>
              <input
                type="number"
                className="ip-field-input"
                value={form.factory_online_steps}
                onChange={(e) =>
                  setField('factory_online_steps', Number(e.target.value || 0))
                }
              />
            </div>

            <div className="ip-block">
              <Label help="Number of online learning steps for the broker agent.">
                Broker Online Learning Steps
              </Label>
              <input
                type="number"
                className="ip-field-input"
                value={form.broker_online_steps}
                onChange={(e) =>
                  setField('broker_online_steps', Number(e.target.value || 0))
                }
              />
            </div>
          </div>
        </div>

        <div className="ip-actions">
          <button
            className="ip-btn-main"
            onClick={onRun}
            disabled={running || learning}
          >
            {running ? 'Running...' : 'Run Simulation'}
          </button>

          <button
            className="ip-btn-ghost"
            onClick={onReload}
            disabled={running || learning}
          >
            Reload Models / Grades
          </button>
        </div>
      </div>
    </div>
  )
}