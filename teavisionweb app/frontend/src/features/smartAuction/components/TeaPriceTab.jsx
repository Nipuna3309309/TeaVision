import { useEffect, useMemo, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from 'recharts'
import api from '../api/client'
import { money } from '../utils/format'
import './TeaPriceTab.css'

function InfoTooltip({ text }) {
  return (
    <span className="tpt-tooltip">
      <span className="tpt-info-dot" aria-label="More information">
        i
      </span>
      <span className="tpt-tooltip-content">{text}</span>
    </span>
  )
}

function Label({ children, help }) {
  return (
    <label className="tpt-field-label">
      <span>{children}</span>
      {help && <InfoTooltip text={help} />}
    </label>
  )
}

function SelectControl({ value, onChange, children }) {
  return (
    <div className="tpt-select-wrap">
      <select value={value} onChange={onChange} className="tpt-field-input tpt-select">
        {children}
      </select>

      <div className="tpt-select-icon">
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

export default function TeaPriceTab() {
  const [meta, setMeta] = useState(null)
  const [loadingMeta, setLoadingMeta] = useState(true)
  const [predicting, setPredicting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const [form, setForm] = useState({
    elevation: 'Mid',
    grade: '',
    target_year: 2026,
    target_month: 1,
    target_week_in_month: 1,
    return_last_n_weeks: 12,
  })

  const grades = useMemo(() => {
    return meta?.grades_by_elevation?.[form.elevation] || []
  }, [meta, form.elevation])

  useEffect(() => {
    loadMetadata()
  }, [])

  useEffect(() => {
    if (!meta) return
    const nextGrades = meta?.grades_by_elevation?.[form.elevation] || []
    if (!nextGrades.includes(form.grade)) {
      setForm((prev) => ({ ...prev, grade: nextGrades[0] || '' }))
    }
  }, [meta, form.elevation])

  async function loadMetadata() {
    try {
      setLoadingMeta(true)
      setError('')
      const res = await api.get('/tea-price/metadata')
      const data = res.data
      setMeta(data)

      const firstGrades = data?.grades_by_elevation?.Mid || []
      setForm((prev) => ({
        ...prev,
        elevation: 'Mid',
        grade: firstGrades[0] || '',
      }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tea price metadata')
    } finally {
      setLoadingMeta(false)
    }
  }

  async function handlePredict() {
    try {
      setPredicting(true)
      setError('')
      setResult(null)

      const res = await api.post('/tea-price/predict', form)
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Tea price prediction failed')
    } finally {
      setPredicting(false)
    }
  }

  const chartData = useMemo(() => {
    if (!result?.series) return []
    return result.series.map((p) => ({
      label: new Date(p.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      price: Number(p.predicted_price),
      lower: Number(p.lower_band),
      upper: Number(p.upper_band),
    }))
  }, [result])

  const rangeLine = useMemo(() => {
    if (!result) return '—'

    const pred = Number(result.predicted_price || 0)
    const lower = Number(result.predicted_lower_band || 0)
    const upper = Number(result.predicted_upper_band || 0)
    const delta = Math.abs(pred - lower)

    return `${pred.toFixed(2)} ± ${delta.toFixed(2)} ⇒ ${lower.toFixed(2)} to ${upper.toFixed(2)}`
  }, [result])

  const priceRangeValue = useMemo(() => {
    if (!result) return 'Rs. 0.00 - Rs. 0.00'

    const lower = Number(result.predicted_lower_band || 0)
    const upper = Number(result.predicted_upper_band || 0)

    return `${money(lower)} - ${money(upper)}`
  }, [result])

  const priceBetweenText = useMemo(() => {
    if (!result) return 'No forecast yet'

    const lower = Number(result.predicted_lower_band || 0)
    const upper = Number(result.predicted_upper_band || 0)

    return `Price likely between ${money(lower)} and ${money(upper)}`
  }, [result])

  return (
    <div className="tpt-layout">
      <div className="tpt-sidebar-col">
        <div className="tpt-glass-panel">
          <h2 className="tpt-section-title">Tea Price Forecast Inputs</h2>

          {loadingMeta ? (
            <p className="tpt-loading-text">Loading price models...</p>
          ) : (
            <div className="tpt-form">
              <div>
                <Label help="Select the elevation category used for ARIMA price forecasting.">
                  Elevation
                </Label>
                <SelectControl
                  value={form.elevation}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      elevation: e.target.value,
                    }))
                  }
                >
                  <option value="Low">Low</option>
                  <option value="Mid">Mid</option>
                  <option value="High">High</option>
                </SelectControl>
              </div>

              <div>
                <Label help="Select the tea grade to forecast.">Grade</Label>
                <SelectControl
                  value={form.grade}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      grade: e.target.value,
                    }))
                  }
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

              <div>
                <Label help="Forecast target year.">Year</Label>
                <input
                  type="number"
                  className="tpt-field-input"
                  value={form.target_year}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      target_year: Number(e.target.value || 2026),
                    }))
                  }
                />
              </div>

              <div className="tpt-grid-2">
                <div>
                  <Label help="Forecast target month.">Month</Label>
                  <SelectControl
                    value={form.target_month}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        target_month: Number(e.target.value),
                      }))
                    }
                  >
                    {monthNames.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </SelectControl>
                </div>

                <div>
                  <Label help="Week number inside the month.">Week</Label>
                  <SelectControl
                    value={form.target_week_in_month}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        target_week_in_month: Number(e.target.value),
                      }))
                    }
                  >
                    {[1, 2, 3, 4, 5].map((w) => (
                      <option key={w} value={w}>
                        {w}
                      </option>
                    ))}
                  </SelectControl>
                </div>
              </div>

              <div>
                <Label help="How many last predicted weeks should be displayed on chart and table.">
                  Show last weeks
                </Label>
                <input
                  type="range"
                  min="1"
                  max="60"
                  value={form.return_last_n_weeks}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      return_last_n_weeks: Number(e.target.value),
                    }))
                  }
                  className="tpt-range"
                />
                <div className="tpt-range-text">{form.return_last_n_weeks} weeks</div>
              </div>

              <div className="tpt-button-group">
                <button
                  className="tpt-btn-main"
                  onClick={handlePredict}
                  disabled={predicting || !form.grade}
                >
                  {predicting ? 'Predicting...' : 'Predict Tea Price'}
                </button>

                <button
                  className="tpt-btn-ghost"
                  onClick={loadMetadata}
                  disabled={predicting}
                >
                  Reload Tea Price Models
                </button>
              </div>

              {error && <div className="tpt-error-box">{error}</div>}
            </div>
          )}
        </div>
      </div>

      <div className="tpt-content">
        <div className="tpt-top-cards">
          <div className="tpt-soft-card tpt-soft-card-wide">
            <div className="tpt-top-card-label">
              <span>Predicted Unit Price</span>
              <span className="tpt-info-dot">i</span>
            </div>
            <div className="tpt-hero-value">
              {result ? money(result.predicted_price) : 'Rs. 0.00'}
            </div>
            <div className="tpt-hero-subtext">
              {result ? rangeLine : 'Select inputs and run prediction'}
            </div>
          </div>

          <div className="tpt-soft-card">
            <div className="tpt-top-card-label">
              <span>Expected Price Range</span>
              <span className="tpt-info-dot">i</span>
            </div>
            <div className="tpt-hero-value tpt-hero-value-small">
              {result ? priceRangeValue : 'Rs. 0.00 - Rs. 0.00'}
            </div>
            <div className="tpt-hero-subtext">
              {result ? priceBetweenText : 'No forecast yet'}
            </div>
            {result && <div className="tpt-range-line-note">{rangeLine}</div>}
          </div>
        </div>

        <div className="tpt-glass-panel">
          <h2 className="tpt-section-title">Tea Price Forecast Summary</h2>

          {!result ? (
            <p className="tpt-empty-text">
              Run a price prediction to see the result, target date, range and trend.
            </p>
          ) : (
            <div className="tpt-summary-grid">
              <div className="tpt-chart-card">
                <div className="tpt-chart-title">Predicted + Range Trend</div>

                <div className="tpt-chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="price" strokeWidth={2} dot />
                      <Line
                        type="monotone"
                        dataKey="lower"
                        strokeDasharray="4 4"
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="upper"
                        strokeDasharray="4 4"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="tpt-glass-panel tpt-details-card">
                <h3 className="tpt-sub-title">Forecast Details</h3>

                <div className="tpt-panel-list">
                  <p>
                    <strong>Elevation:</strong> {result.elevation}
                  </p>
                  <p>
                    <strong>Grade:</strong> {result.grade}
                  </p>
                  <p>
                    <strong>Target Date:</strong> {result.target_date}
                  </p>
                  <p>
                    <strong>Week Index:</strong> {result.target_sale_no} (approx.)
                  </p>
                  <p>
                    <strong>Weeks Ahead:</strong> {result.steps_ahead}
                  </p>
                  <p>
                    <strong>Model Last Known Date:</strong> {result.model_last_train_date}
                  </p>
                  <p>
                    <strong>Lower Band:</strong> {money(result.predicted_lower_band)}
                  </p>
                  <p>
                    <strong>Upper Band:</strong> {money(result.predicted_upper_band)}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="tpt-glass-panel">
          <h2 className="tpt-section-title">Forecast Points</h2>

          <div className="tpt-table-wrap">
            <table className="tpt-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Week</th>
                  <th className="tpt-text-right">Predicted</th>
                  <th className="tpt-text-right">Low</th>
                  <th className="tpt-text-right">High</th>
                </tr>
              </thead>
              <tbody>
                {!result || !result.series || result.series.length === 0 ? (
                  <tr>
                    <td className="tpt-empty-row" colSpan="5">
                      No forecast points yet.
                    </td>
                  </tr>
                ) : (
                  result.series.map((row, idx) => (
                    <tr key={idx}>
                      <td>{row.date}</td>
                      <td>{row.sale_no}</td>
                      <td className="tpt-text-right">
                        {Number(row.predicted_price).toFixed(2)}
                      </td>
                      <td className="tpt-text-right">
                        {Number(row.lower_band).toFixed(2)}
                      </td>
                      <td className="tpt-text-right">
                        {Number(row.upper_band).toFixed(2)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}