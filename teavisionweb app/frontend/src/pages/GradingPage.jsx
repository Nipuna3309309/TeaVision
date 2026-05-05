import { useState, useRef, useEffect } from 'react'
import ModelSelector from '../components/ModelSelector'
import './GradingPage.css'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : `http://${window.location.hostname}:8000`

const LIGHT_LEVELS = {
  too_dark: { icon: '🌑', bg: '#ffebee' },
  poor: { icon: '🌙', bg: '#fff3e0' },
  good: { icon: '☀️', bg: '#e8f5e9' },
  bright: { icon: '🌤️', bg: '#f1f8e9' },
  too_bright: { icon: '🔆', bg: '#ffebee' },
}

function GradingPage() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [selectedModel, setSelectedModel] = useState('mlp')
  const [mlModels, setMlModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  // Environment analysis
  const [envAnalysis, setEnvAnalysis] = useState(null)
  const [envLoading, setEnvLoading] = useState(false)
  const [cameraDistance, setCameraDistance] = useState('')
  const [manualLight, setManualLight] = useState('')
  const [showManualInputs, setShowManualInputs] = useState(false)
  const [showModelComparison, setShowModelComparison] = useState(false)
  const fileInputRef = useRef(null)
  const cameraInputRef = useRef(null)

  useEffect(() => {
    fetch(`${API_BASE}/models`)
      .then(r => r.json())
      .then(data => setMlModels(data.ml_models || []))
      .catch(() => {})
  }, [])

  const analyzeEnvironment = async (file, distance) => {
    setEnvLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (distance && parseFloat(distance) > 0) {
        formData.append('camera_distance', parseFloat(distance))
      }
      const res = await fetch(`${API_BASE}/analyze-environment`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      setEnvAnalysis(data)
    } catch {
      setEnvAnalysis(null)
    }
    setEnvLoading(false)
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setResult(null)
      setError(null)
      setEnvAnalysis(null)
      analyzeEnvironment(file, cameraDistance)
    }
  }

  const handleCameraCapture = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setResult(null)
      setError(null)
      setEnvAnalysis(null)
      analyzeEnvironment(file, cameraDistance)

      // Auto-upload for desktop sync
      const formData = new FormData()
      formData.append('file', file)
      fetch(`${API_BASE}/mobile/upload`, { method: 'POST', body: formData }).catch(() => {})
    }
  }

  const handleDistanceChange = (val) => {
    setCameraDistance(val)
    if (selectedFile && val && parseFloat(val) > 0) {
      analyzeEnvironment(selectedFile, val)
    }
  }

  const handleClassify = async () => {
    if (!selectedFile) return
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('model', selectedModel)

    try {
      const res = await fetch(`${API_BASE}/classify`, {
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
      setError('Classification failed. Make sure the backend is running.')
    }
    setLoading(false)
  }

  const handleReset = () => {
    setSelectedFile(null)
    setPreviewUrl(null)
    setResult(null)
    setError(null)
    setEnvAnalysis(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (cameraInputRef.current) cameraInputRef.current.value = ''
  }

  const handleLoadFromPhone = async () => {
    try {
      const res = await fetch(`${API_BASE}/mobile/latest`)
      const data = await res.json()
      if (!data.available) {
        setError('No image from phone yet. Capture one using the mobile page first.')
        return
      }
      const byteStr = atob(data.image)
      const bytes = new Uint8Array(byteStr.length)
      for (let i = 0; i < byteStr.length; i++) bytes[i] = byteStr.charCodeAt(i)
      const blob = new Blob([bytes], { type: 'image/jpeg' })
      const file = new File([blob], data.filename || 'phone_capture.jpg', { type: 'image/jpeg' })
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(blob))
      setResult(null)
      setError(null)
      analyzeEnvironment(file, cameraDistance)
    } catch {
      setError('Could not load phone image. Check backend connection.')
    }
  }

  const getLightInfo = () => {
    if (manualLight) {
      const manualMap = {
        'too_dark': { level: 'too_dark', label: 'Too Dark (Manual)', color: '#F44336', tip: 'You indicated low light conditions.' },
        'poor': { level: 'poor', label: 'Poor Lighting (Manual)', color: '#FF9800', tip: 'You indicated dim conditions.' },
        'good': { level: 'good', label: 'Good Lighting (Manual)', color: '#4CAF50', tip: 'Good conditions for analysis.' },
        'bright': { level: 'bright', label: 'Bright (Manual)', color: '#8BC34A', tip: 'Bright conditions.' },
        'too_bright': { level: 'too_bright', label: 'Too Bright (Manual)', color: '#F44336', tip: 'You indicated overexposed conditions.' },
      }
      return manualMap[manualLight] || null
    }
    return envAnalysis?.light || null
  }

  const isHighQuality = result?.prediction === 'high_quality'
  const lightInfo = getLightInfo()
  const lightMeta = lightInfo ? LIGHT_LEVELS[lightInfo.level] || LIGHT_LEVELS.good : null

  return (
    <div className="grading-page">
      <div className="gp-header">
        <h1>Tea Leaf Quality Grading</h1>
        <p>ML-based freshness classification using 25 hand-crafted features</p>
      </div>

      <div className="gp-controls-row">
        {/* Upload */}
        <div className="gp-upload-section">
          <div
            className="gp-upload-area"
            onClick={() => fileInputRef.current.click()}
            onDrop={(e) => {
              e.preventDefault()
              const file = e.dataTransfer.files[0]
              if (file && file.type.startsWith('image/')) {
                setSelectedFile(file)
                setPreviewUrl(URL.createObjectURL(file))
                setResult(null)
                setError(null)
                setEnvAnalysis(null)
                analyzeEnvironment(file, cameraDistance)
              }
            }}
            onDragOver={(e) => e.preventDefault()}
          >
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" className="gp-upload-preview" />
            ) : (
              <div className="gp-upload-placeholder">
                <span className="gp-upload-icon">🌿</span>
                <p>Click or drag to upload</p>
                <p className="gp-upload-hint">JPG, JPEG, PNG</p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png"
              onChange={handleFileSelect}
              hidden
            />
          </div>
          {/* Capture Buttons */}
          <div className="gp-capture-buttons">
            <button className="gp-camera-btn" onClick={() => cameraInputRef.current.click()}>
              📸 Take Photo
            </button>
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleCameraCapture}
              hidden
            />
            <button className="gp-phone-button" onClick={handleLoadFromPhone}>
              📱 From Phone
            </button>
          </div>
        </div>

        {/* Settings */}
        <div className="gp-settings-panel">
          <h3>Classification Settings</h3>

          <ModelSelector
            models={mlModels}
            selectedModel={selectedModel}
            onSelect={setSelectedModel}
            label="Classification Model"
          />

          <div className="gp-button-row">
            <button
              className="gp-classify-button"
              onClick={handleClassify}
              disabled={!selectedFile || loading}
            >
              {loading ? 'Classifying...' : 'Classify Quality'}
            </button>
            {selectedFile && (
              <button className="gp-reset-button" onClick={handleReset}>
                Reset
              </button>
            )}
          </div>

          {/* Manual Override Toggle */}
          <div className="gp-manual-toggle">
            <button
              className={`gp-toggle-btn ${showManualInputs ? 'active' : ''}`}
              onClick={() => setShowManualInputs(!showManualInputs)}
            >
              {showManualInputs ? 'Hide Manual Inputs' : 'Manual Light & Distance'}
            </button>
          </div>

          {showManualInputs && (
            <div className="gp-manual-inputs">
              <div className="gp-manual-field">
                <label>Camera Distance (cm)</label>
                <input
                  type="number"
                  min="1"
                  max="200"
                  placeholder="e.g. 30"
                  value={cameraDistance}
                  onChange={(e) => handleDistanceChange(e.target.value)}
                  className="gp-input"
                />
                <span className="gp-input-hint">Distance from camera to leaves</span>
              </div>
              <div className="gp-manual-field">
                <label>Light Condition (Override)</label>
                <select
                  value={manualLight}
                  onChange={(e) => setManualLight(e.target.value)}
                  className="gp-select"
                >
                  <option value="">Auto-detect</option>
                  <option value="too_dark">Too Dark</option>
                  <option value="poor">Poor / Dim</option>
                  <option value="good">Good</option>
                  <option value="bright">Bright</option>
                  <option value="too_bright">Too Bright / Overexposed</option>
                </select>
              </div>
            </div>
          )}

          {/* Feature Info */}
          <div className="gp-info-box">
            <h4>25 Features Extracted</h4>
            <div className="gp-feature-categories">
              <span>11 Color (RGB, HSV, LAB)</span>
              <span>3 Texture (GLCM, LBP)</span>
              <span>7 Shape (contour, solidity)</span>
              <span>4 Quality (brightness, contrast)</span>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="gp-error">{error}</div>}

      {/* Environment Analysis Card */}
      {(envAnalysis || envLoading) && (
        <div className="gp-env-card">
          <div className="gp-env-header">
            <span className="gp-env-title">Environment Analysis</span>
            {envLoading && <span className="gp-env-loading">Analyzing...</span>}
          </div>

          {envAnalysis && (
            <div className="gp-env-content">
              {/* Light Meter */}
              <div className="gp-env-section">
                <h4>Lighting Condition</h4>
                <div className="gp-light-meter" style={{ background: lightMeta?.bg || '#f5f5f5' }}>
                  <div className="gp-light-icon">{lightMeta?.icon || '💡'}</div>
                  <div className="gp-light-info">
                    <span className="gp-light-label" style={{ color: lightInfo?.color }}>
                      {lightInfo?.label || 'Unknown'}
                    </span>
                    <span className="gp-light-tip">{lightInfo?.tip}</span>
                  </div>
                  <div className="gp-light-value">
                    <span className="gp-light-pct">{envAnalysis.light.brightness_pct}%</span>
                    <span className="gp-light-sub">Brightness</span>
                  </div>
                </div>
                <div className="gp-brightness-bar-wrap">
                  <div className="gp-brightness-bar">
                    <div
                      className="gp-brightness-marker"
                      style={{ left: `${envAnalysis.light.brightness_pct}%` }}
                    />
                  </div>
                  <div className="gp-brightness-labels">
                    <span>Dark</span>
                    <span>Ideal</span>
                    <span>Bright</span>
                  </div>
                </div>
                <div className="gp-env-extras">
                  <span>Uniformity: {envAnalysis.light.uniformity_pct}%</span>
                  <span>Contrast: {envAnalysis.light.contrast}</span>
                  <span>Color: {envAnalysis.light.color_temp_label}</span>
                  <span>Method: {envAnalysis.light.method === 'exif' ? 'Camera EXIF' : 'Image Analysis'}</span>
                  {envAnalysis.light.exif?.ev != null && <span>EV: {envAnalysis.light.exif.ev}</span>}
                  {envAnalysis.light.exif?.iso != null && <span>ISO: {envAnalysis.light.exif.iso}</span>}
                </div>
              </div>

              {/* Leaf Dimensions */}
              <div className="gp-env-section">
                <h4>Leaf Dimensions (Auto-detected)</h4>
                {envAnalysis.dimensions.detected ? (
                  <div className="gp-dim-content">
                    <div className="gp-dim-metrics">
                      <div className="gp-dim-metric">
                        <span className="gp-dim-val">{envAnalysis.dimensions.leaf_count}</span>
                        <span className="gp-dim-lbl">Leaves</span>
                      </div>
                      <div className="gp-dim-metric">
                        <span className="gp-dim-val">{envAnalysis.dimensions.total_coverage_pct}%</span>
                        <span className="gp-dim-lbl">Coverage</span>
                      </div>
                      {envAnalysis.dimensions.primary_leaf && (
                        <>
                          <div className="gp-dim-metric">
                            <span className="gp-dim-val">
                              {envAnalysis.dimensions.primary_leaf.width_cm
                                ? `${envAnalysis.dimensions.primary_leaf.width_cm} cm`
                                : `~${envAnalysis.dimensions.primary_leaf.width_cm_est} cm`}
                            </span>
                            <span className="gp-dim-lbl">Width</span>
                          </div>
                          <div className="gp-dim-metric">
                            <span className="gp-dim-val">
                              {envAnalysis.dimensions.primary_leaf.height_cm
                                ? `${envAnalysis.dimensions.primary_leaf.height_cm} cm`
                                : `~${envAnalysis.dimensions.primary_leaf.height_cm_est} cm`}
                            </span>
                            <span className="gp-dim-lbl">Height</span>
                          </div>
                          <div className="gp-dim-metric">
                            <span className="gp-dim-val">
                              {envAnalysis.dimensions.primary_leaf.area_cm2
                                ? `${envAnalysis.dimensions.primary_leaf.area_cm2} cm²`
                                : `~${envAnalysis.dimensions.primary_leaf.area_cm2_est} cm²`}
                            </span>
                            <span className="gp-dim-lbl">Area</span>
                          </div>
                        </>
                      )}
                    </div>
                    {envAnalysis.dimensions.primary_leaf?.estimate_note && !cameraDistance && (
                      <div className="gp-dim-note">
                        {envAnalysis.dimensions.primary_leaf.estimate_note}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="gp-dim-empty">No leaf contours detected.</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="gp-results">
          {/* Image + Verdict Row */}
          <div className="gp-verdict-row">
            {/* Uploaded Image */}
            {previewUrl && (
              <div className="gp-result-image-card">
                <h3>Analyzed Image</h3>
                <img src={previewUrl} alt="Analyzed leaf" className="gp-result-image" />
              </div>
            )}

            {/* Main Verdict */}
            <div className={`gp-verdict ${isHighQuality ? 'high' : 'medium'}`}>
              <div className="gp-verdict-icon">
                {isHighQuality ? '✅' : '⚠️'}
              </div>
              <div className="gp-verdict-text">
                <span className="gp-verdict-label">
                  {isHighQuality ? 'High Quality' : 'Medium Quality'}
                </span>
                <span className="gp-verdict-desc">
                  {isHighQuality
                    ? 'Fresh, well-maintained tea leaves suitable for premium grades'
                    : 'Acceptable quality with some signs of aging or damage'}
                </span>
              </div>
              <div className="gp-verdict-model">
                <span>Model: {result.model_used}</span>
                {result.model_accuracy && <span>Accuracy: {result.model_accuracy}%</span>}
              </div>
            </div>
          </div>

          <div className="gp-details-row">
            {/* Confidence */}
            {result.confidence && (
              <div className="gp-detail-card">
                <h3>Prediction Confidence</h3>
                {Object.entries(result.confidence).map(([cls, prob]) => (
                  <div key={cls} className="gp-confidence-row">
                    <span className="gp-conf-label">
                      {cls === 'high_quality' ? 'High Quality' : 'Medium Quality'}
                    </span>
                    <div className="gp-conf-bar-bg">
                      <div
                        className="gp-conf-bar-fill"
                        style={{
                          width: `${prob}%`,
                          backgroundColor: cls === 'high_quality' ? '#4CAF50' : '#FF9800'
                        }}
                      />
                    </div>
                    <span className="gp-conf-value">{prob}%</span>
                  </div>
                ))}
              </div>
            )}

            {/* Key Features */}
            <div className="gp-detail-card">
              <h3>Extracted Features</h3>
              {Object.entries(result.features).map(([name, value]) => (
                <div key={name} className="gp-feature-row">
                  <span className="gp-feat-name">{name}</span>
                  <span className="gp-feat-value">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Model Comparison Table */}
          {mlModels.length > 1 && (
            <div className="gp-model-comparison">
              <button
                className="gp-comparison-toggle"
                onClick={() => setShowModelComparison(!showModelComparison)}
              >
                {showModelComparison ? '▼ Hide' : '▶ Show'} Model Comparison ({mlModels.length} models)
              </button>
              {showModelComparison && (
                <div className="gp-comparison-table-wrap">
                  <table className="gp-comparison-table">
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Type</th>
                        <th>Test Accuracy</th>
                        <th>F1 Score</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {mlModels
                        .sort((a, b) => (b.test_acc || 0) - (a.test_acc || 0))
                        .map(m => (
                        <tr key={m.key} className={m.key === selectedModel ? 'gp-selected-model' : ''}>
                          <td>
                            <strong>{m.name}</strong>
                            <span className="gp-model-desc">{m.description}</span>
                          </td>
                          <td><span className="gp-model-tag">{m.tag}</span></td>
                          <td className="gp-acc-cell">
                            {m.test_acc ? (
                              <>
                                <span className="gp-acc-val">{m.test_acc}%</span>
                                <div className="gp-acc-bar">
                                  <div style={{ width: `${m.test_acc}%`, background: m.test_acc >= 90 ? '#4CAF50' : m.test_acc >= 80 ? '#8BC34A' : '#FF9800' }} />
                                </div>
                              </>
                            ) : '—'}
                          </td>
                          <td>{m.f1 ? `${m.f1}%` : '—'}</td>
                          <td>
                            {m.key !== selectedModel ? (
                              <button className="gp-use-model-btn" onClick={() => setSelectedModel(m.key)}>Use</button>
                            ) : (
                              <span className="gp-current-badge">Current</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default GradingPage
