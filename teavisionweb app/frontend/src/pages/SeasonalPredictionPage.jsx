import React, { useState } from 'react'
import axios from 'axios'
import './SeasonalPredictionPage.css'

function SeasonalPredictionPage() {
  const [data, setData] = useState({
    month: new Date().getMonth() + 1,
    season: 'wet',
    region: 'mid-country',
    temperature: 24.5,
    humidity: 78.0,
    rainfall: 12.0
  })

  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (e) => {
    const { name, value } = e.target
    setData(prev => ({ 
      ...prev, 
      [name]: (name === 'season' || name === 'region') ? value : Number(value)
    }))
  }

  const handlePredict = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await axios.post(
        'http://localhost:8000/seasonal-predict',
        data
      )
      setResult(response.data)
    } catch (err) {
      console.error(err)
      setError('Prediction failed. Make sure the backend is running.')
    }
    setLoading(false)
  }

  // "Today's Status" values - fixed to represent current real-world status
  const todayWeather = {
    region: 'Low-Country',
    temp: 25.5,
    humidity: 78,
    rainfall: 12,
    condition: 'Clear',
    icon: '🌧️',
    wind: '5m/s'
  }

  const currentDate = new Date().toLocaleDateString('en-US', { 
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' 
  })

  return (
    <div className="neo-farm-container">
      {/* HEADER / WIDGET AREA - Now shows fixed "Today" details */}
      <div className="nf-header-card">
        <div className="nf-top-row">
          <div className="nf-location">
            <span className="nf-pin">📍</span>
            <div>
              <h3>{todayWeather.region}</h3>
              <p>Sri Lanka • Tea Estate</p>
            </div>
          </div>
          <div className="nf-user-avatar">
             👨‍🌾 
          </div>
        </div>

        <div className="nf-weather-main">
          <div className="nf-temp-huge">
            {todayWeather.temp}<span>°C</span>
          </div>
          <div className="nf-weather-desc">
            <div className="nf-weather-desc-row">
              <span className="nf-w-icon">{todayWeather.icon}</span> {todayWeather.condition}
            </div>
            <div className="nf-w-date">{currentDate}</div>
          </div>
        </div>

        <div className="nf-weather-stats">
          <div className="nf-stat-pill">
            <span className="stat-label">Wind</span>
            <span className="stat-val">{todayWeather.wind}</span>
          </div>
          <div className="nf-stat-pill">
            <span className="stat-label">Humidity</span>
            <span className="stat-val">{todayWeather.humidity}%</span>
          </div>
          <div className="nf-stat-pill">
            <span className="stat-label">Rainfall</span>
            <span className="stat-val">{todayWeather.rainfall}mm</span>
          </div>
        </div>
      </div>

      <div className="nf-content-grid">
        {/* INPUT FORM CARD */}
        <div className="nf-card">
          <h2 className="nf-card-title">Orchestrated Seasonal Disease Risk Prediction</h2>
          <p className="nf-card-subtitle">Adjust environmental conditions to predict tea diseases using our Ensemble ML Model.</p>

          <div className="nf-form-grid">
            <div className="nf-input-group">
              <label>Month (1-12)</label>
              <input type="number" name="month" min="1" max="12" value={data.month} onChange={handleChange} />
            </div>
            <div className="nf-input-group">
              <label>Season</label>
              <select name="season" value={data.season} onChange={handleChange}>
                <option value="dry">Dry</option>
                <option value="intermediate">Intermediate</option>
                <option value="wet">Wet</option>
              </select>
            </div>
            <div className="nf-input-group">
              <label>Region</label>
              <select name="region" value={data.region} onChange={handleChange}>
                <option value="low-country">Low-Country</option>
                <option value="mid-country">Mid-Country</option>
                <option value="high-country">High-Country</option>
              </select>
            </div>
            <div className="nf-input-group">
              <label>Temperature (°C)</label>
              <input type="number" step="0.1" name="temperature" value={data.temperature} onChange={handleChange} />
            </div>
            <div className="nf-input-group">
              <label>Humidity (%)</label>
              <input type="number" step="0.1" name="humidity" value={data.humidity} onChange={handleChange} />
            </div>
            <div className="nf-input-group">
              <label>Rainfall (mm/month)</label>
              <input type="number" step="0.1" name="rainfall" value={data.rainfall} onChange={handleChange} />
            </div>
          </div>

          <button className="nf-predict-btn" onClick={handlePredict} disabled={loading}>
            {loading ? 'Analyzing Ensemble...' : 'Predict Disease Outbreak'}
          </button>
          
          {error && <div className="nf-error">{error}</div>}
        </div>

        {/* RESULTS CARD */}
        <div className="nf-card nf-results-card">
          <h2 className="nf-card-title">Prediction Status</h2>
          
          {!result && !loading && (
             <div className="nf-empty-state">
               <span className="nf-empty-icon">🍃</span>
               <p>Awaiting environmental parameters to run the ensemble classifier sequence.</p>
             </div>
          )}

          {loading && (
             <div className="nf-loading-state">
                <div className="nf-spinner"></div>
                <p>Consulting ensemble estimators...</p>
             </div>
          )}

          {result && (
            <div className="nf-result-content">
              {/* Circular Moisture/Risk Indicator */}
              <div className="nf-risk-circle-wrap">
                <svg className="nf-risk-circle" viewBox="0 0 36 36">
                  <path
                    className="nf-circle-bg"
                    d="M18 2.0845
                      a 15.9155 15.9155 0 0 1 0 31.831
                      a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className={`nf-circle-fill ${result.risk_level.toLowerCase()}`}
                    strokeDasharray={`${result.risk_level === 'High' ? '85' : result.predicted_disease === 'Healthy' ? '15' : '50'}, 100`}
                    d="M18 2.0845
                      a 15.9155 15.9155 0 0 1 0 31.831
                      a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                </svg>
                <div className="nf-risk-score">
                  <span className={`nf-risk-text ${result.risk_level.toLowerCase()}`}>{result.risk_level}</span>
                  <span className="nf-risk-sub">Risk Level</span>
                </div>
              </div>

              <div className="nf-verdict-box">
                <h4>Predicted Outcome</h4>
                <div className={`nf-disease-name ${result.predicted_disease === 'Healthy' ? 'safe' : 'danger'}`}>
                  {result.predicted_disease === 'Healthy' ? 'Healthy (No Disease)' : result.predicted_disease}
                </div>
                <p className="nf-ensemble-note">
                  Generated by VotingClassifier 
                  <br/> (RandomForest + LightGBM)
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SeasonalPredictionPage