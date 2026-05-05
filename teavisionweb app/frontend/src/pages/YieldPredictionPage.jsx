import { useState, useEffect, useRef } from 'react'
import './YieldPredictionPage.css'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : `http://${window.location.hostname}:8000`

const DIVISION_COLORS = {
  Lower: '#2196F3',
  Atb: '#4CAF50',
  Upper: '#FF9800'
}

function YieldPredictionPage() {
  const [fieldsData, setFieldsData] = useState(null)
  const [selectedLocation, setSelectedLocation] = useState('Nawalapitiya')
  const [selectedField, setSelectedField] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const canvasRef = useRef(null)

  const [bestMonth, setBestMonth] = useState(null)

  // User input fields (current month operational variables)
  const [rainfall, setRainfall] = useState('150')
  const [wetDays, setWetDays] = useState('10')
  const [pluckingRounds, setPluckingRounds] = useState('4')
  const [monthsAfterPruning, setMonthsAfterPruning] = useState('12')

  useEffect(() => {
    fetch(`${API_BASE}/yield/fields`)
      .then(r => r.json())
      .then(data => setFieldsData(data))
      .catch(() => setError('Failed to load field data. Is the backend running?'))
  }, [])

  // Fetch best month when field changes
  useEffect(() => {
    if (!selectedField) { setBestMonth(null); return }
    fetch(`${API_BASE}/yield/best/${selectedField}`)
      .then(r => r.json())
      .then(data => { if (!data.error) setBestMonth(data); else setBestMonth(null) })
      .catch(() => setBestMonth(null))
  }, [selectedField])

  // Reset selected field when location changes
  useEffect(() => {
    setSelectedField('')
    setResult(null)
    setError(null)
  }, [selectedLocation])

  // Build flat field list for dropdown
  const allFields = []
  if (fieldsData?.divisions) {
    Object.entries(fieldsData.divisions).forEach(([div, data]) => {
      const isNawa = ["Lower", "Atb", "Upper"].includes(div)
      if ((selectedLocation === 'Nawalapitiya' && isNawa) || (selectedLocation === 'Hanthana' && !isNawa)) {
        data.fields.forEach(f => {
          allFields.push({ ...f, division: div })
        })
      }
    })
  }

  const selectedFieldInfo = allFields.find(f => f.field_key === selectedField)

  const handlePredict = async () => {
    if (!selectedField) return
    setLoading(true)
    setError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('field_key', selectedField)
    formData.append('months', 1)
    formData.append('rainfall', parseFloat(rainfall) || 0)
    formData.append('wet_days', parseFloat(wetDays) || 0)
    formData.append('plucking_rounds', parseFloat(pluckingRounds) || 0)
    formData.append('months_after_pruning', parseFloat(monthsAfterPruning) || 12)

    try {
      const res = await fetch(`${API_BASE}/yield/predict`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        setResult(data)
      }
    } catch {
      setError('Prediction failed. Check backend connection.')
    }
    setLoading(false)
  }

  // Draw chart when result changes
  useEffect(() => {
    if (!result || !canvasRef.current) return
    drawChart(canvasRef.current, result)
  }, [result])

  return (
    <div className="yield-page">
      <div className="yp-header">
        <h1>Tea Yield Prediction</h1>
        <div className="yp-location-toggles">
          <button
            className={`yp-loc-btn ${selectedLocation === 'Nawalapitiya' ? 'active' : ''}`}
            onClick={() => setSelectedLocation('Nawalapitiya')}
          >
            Nawalapitiya Estate
          </button>
          <button
            className={`yp-loc-btn ${selectedLocation === 'Hanthana' ? 'active' : ''}`}
            onClick={() => setSelectedLocation('Hanthana')}
          >
            Hanthana Estate
          </button>
        </div>
      </div>

      {/* Best Month Card */}
      {bestMonth && (
        <div className="yp-best-month">
          <div className="yp-best-badge">Best Performing Month</div>
          <div className="yp-best-content">
            <div className="yp-best-yield">
              <span className="yp-best-val">{bestMonth.yield_kg}</span>
              <span className="yp-best-unit">kg</span>
              <span className="yp-best-date">{bestMonth.date}</span>
            </div>
            <div className="yp-best-attrs">
              <div className="yp-best-attr">
                <span className="yp-best-attr-val">{bestMonth.rainfall_mm}</span>
                <span className="yp-best-attr-lbl">Rainfall (mm)</span>
              </div>
              <div className="yp-best-attr">
                <span className="yp-best-attr-val">{bestMonth.wet_days}</span>
                <span className="yp-best-attr-lbl">Wet Days</span>
              </div>
              <div className="yp-best-attr">
                <span className="yp-best-attr-val">{bestMonth.plucking_rounds}</span>
                <span className="yp-best-attr-lbl">Plucking Rounds</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="yp-controls-row">
        {/* Left: Field Selection + Info */}
        <div className="yp-field-panel">
          <h3>Select Tea Field</h3>

          {/* Field ID Dropdown */}
          <div className="yp-field-dropdown-wrap">
            <select
              className="yp-field-dropdown"
              value={selectedField}
              onChange={e => { setSelectedField(e.target.value); setResult(null) }}
            >
              <option value="">-- Select a Field --</option>
              {Object.entries(fieldsData?.divisions || {})
                .filter(([div]) => {
                  const isNawa = ["Lower", "Atb", "Upper"].includes(div)
                  return selectedLocation === 'Nawalapitiya' ? isNawa : !isNawa
                })
                .map(([div, data]) => (
                  <optgroup key={div} label={`${div} Division (${data.count} fields)`}>
                    {data.fields.map(f => (
                      <option key={f.field_key} value={f.field_key}>
                        Field {f.field_id}
                      </option>
                    ))}
                  </optgroup>
                ))}
            </select>
          </div>

          {/* Explanation */}
          <div className="yp-explanation">
            <strong>How it works:</strong> The model predicts next month's yield.
            Fertilizer is not taken as a direct user input — its effect is represented
            through historical lagged variables from the previous 3 months internally.
            You only enter the current operational and field-condition variables.
          </div>
        </div>

        {/* Right: Input Fields */}
        <div className="yp-settings-panel">
          <h3>Current Month Inputs</h3>
          <p className="yp-input-hint">Enter the values that a field manager can observe or report for the current month</p>

          <div className="yp-input-grid">
            <div className="yp-input-field">
              <label>Rainfall (mm)</label>
              <input type="number" value={rainfall} onChange={e => setRainfall(e.target.value)}
                placeholder="150" min="0" step="10" />
              <span className="yp-input-sub">Total monthly rainfall</span>
            </div>
            <div className="yp-input-field">
              <label>Wet Days Count</label>
              <input type="number" value={wetDays} onChange={e => setWetDays(e.target.value)}
                placeholder="10" min="0" max="31" />
              <span className="yp-input-sub">Days with rainfall this month</span>
            </div>
            <div className="yp-input-field">
              <label>Plucking Rounds</label>
              <input type="number" value={pluckingRounds} onChange={e => setPluckingRounds(e.target.value)}
                placeholder="4" min="0" max="12" />
              <span className="yp-input-sub">Harvesting cycles this month</span>
            </div>
            <div className="yp-input-field">
              <label>Months After Pruning</label>
              <input type="number" value={monthsAfterPruning} onChange={e => setMonthsAfterPruning(e.target.value)}
                placeholder="12" min="0" max="60" />
              <span className="yp-input-sub">Recovery stage since last pruning</span>
            </div>
          </div>

          <button
            className="yp-predict-btn"
            onClick={handlePredict}
            disabled={!selectedField || loading}
          >
            {loading ? 'Predicting...' : 'Predict Next Month Yield'}
          </button>
        </div>
      </div>

      {error && <div className="yp-error">{error}</div>}

      {/* Results */}
      {result && (
        <div className="yp-results">
          {/* Summary Cards */}
          <div className="yp-summary-row">
            <div className="yp-summary-card yp-card-highlight">
              <span className="yp-summary-val">{result.forecast.values[0]}</span>
              <span className="yp-summary-unit">kg</span>
              <span className="yp-summary-lbl">Predicted Next Month Yield</span>
            </div>
            <div className="yp-summary-card">
              <span className="yp-summary-val">{result.forecast.lower_ci[0]}-{result.forecast.upper_ci[0]}</span>
              <span className="yp-summary-unit">kg</span>
              <span className="yp-summary-lbl">95% Confidence Interval</span>
            </div>
            <div className="yp-summary-card">
              <span className="yp-summary-val" style={{ color: DIVISION_COLORS[result.division] }}>{result.division}</span>
              <span className="yp-summary-lbl">Division — Field {result.field_id}</span>
            </div>
          </div>

          {/* Inputs used tags */}
          {result.inputs_used && Object.keys(result.inputs_used).length > 0 && (
            <div className="yp-inputs-used">
              <span className="yp-iu-label">Inputs used:</span>
              {result.inputs_used.rainfall_mm > 0 && <span className="yp-iu-tag">Rainfall: {result.inputs_used.rainfall_mm} mm</span>}
              {result.inputs_used.wet_days > 0 && <span className="yp-iu-tag">Wet Days: {result.inputs_used.wet_days}</span>}
              {result.inputs_used.plucking_rounds > 0 && <span className="yp-iu-tag">Plucking: {result.inputs_used.plucking_rounds} rounds</span>}
              <span className="yp-iu-tag">Months After Pruning: {result.inputs_used.months_after_pruning}</span>
              <span className="yp-iu-tag-info">Fertilizer effect: from historical 3-month lags (internal)</span>
            </div>
          )}

          {/* Chart */}
          <div className="yp-chart-card">
            <h3>Historical Yield + Next Month Forecast</h3>
            <div className="yp-chart-legend">
              <span className="yp-legend-item"><span className="yp-dot" style={{ background: '#1976D2' }} /> Historical (Fitted)</span>
              <span className="yp-legend-item"><span className="yp-dot" style={{ background: '#4CAF50' }} /> Predicted</span>
              <span className="yp-legend-item"><span className="yp-dot" style={{ background: 'rgba(76,175,80,0.15)' }} /> 95% CI</span>
            </div>
            <canvas ref={canvasRef} width={900} height={350} className="yp-canvas" />
          </div>

        </div>
      )}
    </div>
  )
}

/**
 * Canvas chart: historical fitted values + next month forecast with CI
 */
function drawChart(canvas, data) {
  const ctx = canvas.getContext('2d')
  const W = canvas.width
  const H = canvas.height
  const pad = { top: 20, right: 20, bottom: 50, left: 65 }

  ctx.clearRect(0, 0, W, H)

  const hist = data.historical
  const fc = data.forecast

  const allVals = [...hist.values, ...fc.values, ...fc.upper_ci]
  const maxVal = Math.max(...allVals, 1) * 1.15
  const totalPoints = hist.dates.length + fc.dates.length
  if (totalPoints === 0) return

  const chartW = W - pad.left - pad.right
  const chartH = H - pad.top - pad.bottom
  const dx = chartW / Math.max(totalPoints - 1, 1)

  const toX = (i) => pad.left + i * dx
  const toY = (v) => pad.top + chartH - (v / maxVal) * chartH

  // Background
  ctx.fillStyle = '#fafafa'
  ctx.fillRect(pad.left, pad.top, chartW, chartH)

  // Grid
  ctx.strokeStyle = '#e8e8e8'
  ctx.lineWidth = 0.5
  for (let i = 0; i <= 5; i++) {
    const y = pad.top + (chartH / 5) * i
    ctx.beginPath()
    ctx.moveTo(pad.left, y)
    ctx.lineTo(W - pad.right, y)
    ctx.stroke()

    ctx.fillStyle = '#888'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText((maxVal - (maxVal / 5) * i).toFixed(0), pad.left - 8, y + 4)
  }

  // Y label
  ctx.save()
  ctx.translate(14, pad.top + chartH / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillStyle = '#666'
  ctx.font = '12px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('Yield (kg)', 0, 0)
  ctx.restore()

  // CI fill for forecast point(s)
  const fcStart = hist.dates.length
  if (fc.dates.length > 0) {
    const ciX = toX(fcStart)
    const ciTop = toY(fc.upper_ci[0])
    const ciBot = toY(fc.lower_ci[0])
    ctx.fillStyle = 'rgba(76, 175, 80, 0.15)'
    ctx.fillRect(ciX - 15, ciTop, 30, ciBot - ciTop)
  }

  // Historical line
  if (hist.values.length > 1) {
    ctx.strokeStyle = '#1976D2'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(toX(0), toY(hist.values[0]))
    for (let i = 1; i < hist.values.length; i++) ctx.lineTo(toX(i), toY(hist.values[i]))
    ctx.stroke()

    // Historical dots
    ctx.fillStyle = '#1976D2'
    for (let i = 0; i < hist.values.length; i++) {
      ctx.beginPath()
      ctx.arc(toX(i), toY(hist.values[i]), 2.5, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  // Divider line
  if (hist.dates.length > 0 && fc.dates.length > 0) {
    ctx.strokeStyle = '#bbb'
    ctx.lineWidth = 1
    ctx.setLineDash([5, 4])
    const divX = toX(fcStart - 0.5)
    ctx.beginPath()
    ctx.moveTo(divX, pad.top)
    ctx.lineTo(divX, pad.top + chartH)
    ctx.stroke()
    ctx.setLineDash([])

    ctx.fillStyle = '#4CAF50'
    ctx.font = 'bold 10px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText('Predicted', divX + 6, pad.top + 12)
  }

  // Forecast point (single next-month prediction)
  if (fc.values.length > 0) {
    // Connecting line from last historical
    if (hist.values.length > 0) {
      ctx.strokeStyle = '#4CAF50'
      ctx.lineWidth = 2
      ctx.setLineDash([4, 3])
      ctx.beginPath()
      ctx.moveTo(toX(hist.values.length - 1), toY(hist.values[hist.values.length - 1]))
      ctx.lineTo(toX(fcStart), toY(fc.values[0]))
      ctx.stroke()
      ctx.setLineDash([])
    }

    // Big forecast dot
    ctx.fillStyle = '#4CAF50'
    ctx.beginPath()
    ctx.arc(toX(fcStart), toY(fc.values[0]), 6, 0, Math.PI * 2)
    ctx.fill()

    // Value label
    ctx.fillStyle = '#2e7d32'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(`${fc.values[0]} kg`, toX(fcStart), toY(fc.values[0]) - 12)
  }

  // X-axis labels
  const allDates = [...hist.dates, ...fc.dates]
  const step = Math.max(1, Math.floor(allDates.length / 8))
  ctx.fillStyle = '#666'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'center'
  for (let i = 0; i < allDates.length; i += step) {
    ctx.fillText(allDates[i].substring(0, 7), toX(i), H - pad.bottom + 18)
  }
  // Always show last date (the prediction month)
  if (allDates.length > 0) {
    ctx.fillStyle = '#4CAF50'
    ctx.font = 'bold 10px sans-serif'
    ctx.fillText(allDates[allDates.length - 1].substring(0, 7), toX(allDates.length - 1), H - pad.bottom + 18)
  }
}

export default YieldPredictionPage
