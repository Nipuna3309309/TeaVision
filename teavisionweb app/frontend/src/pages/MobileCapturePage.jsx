import { useState, useRef } from 'react'
import './MobileCapturePage.css'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : `http://${window.location.hostname}:8000`

function MobileCapturePage() {
  const [previewUrl, setPreviewUrl] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [detecting, setDetecting] = useState(false)
  const [result, setResult] = useState(null)
  const [mode, setMode] = useState('detect')
  const [envAnalysis, setEnvAnalysis] = useState(null)
  const [envLoading, setEnvLoading] = useState(false)
  const [capturedFile, setCapturedFile] = useState(null)
  const fileInputRef = useRef(null)

  const analyzeEnvironment = async (file) => {
    setEnvLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
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

  const handleCapture = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setPreviewUrl(URL.createObjectURL(file))
    setCapturedFile(file)
    setResult(null)
    setEnvAnalysis(null)

    // Auto-analyze environment
    analyzeEnvironment(file)

    // Auto-upload to backend for desktop to pick up
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    fetch(`${API_BASE}/mobile/upload`, { method: 'POST', body: formData })
      .then(r => r.json())
      .then(() => {
        setUploading(false)
      })
      .catch(() => setUploading(false))
  }

  const handleAnalyze = async () => {
    if (!capturedFile) return
    setDetecting(true)
    setResult(null)

    const formData = new FormData()
    formData.append('file', capturedFile)

    try {
      if (mode === 'detect') {
        formData.append('confidence', '0.35')
        formData.append('use_sahi', 'false')
        formData.append('model', 'teanet_rf_v4')
        const res = await fetch(`${API_BASE}/detect`, { method: 'POST', body: formData })
        const data = await res.json()
        if (data.error) {
          setResult({ type: 'error', data: { message: data.message || 'This image does not contain tea leaves on a white cloth.' } })
        } else {
          setResult({ type: 'detect', data })
        }
      } else {
        formData.append('model', 'mlp')
        const res = await fetch(`${API_BASE}/classify`, { method: 'POST', body: formData })
        const data = await res.json()
        setResult({ type: 'classify', data })
      }
    } catch {
      setResult({ type: 'error', data: { message: 'Analysis failed. Check connection.' } })
    }
    setDetecting(false)
  }

  const handleReset = () => {
    setPreviewUrl(null)
    setCapturedFile(null)
    setUploaded(false)
    setResult(null)
    setEnvAnalysis(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const lightInfo = envAnalysis?.light
  const lightMeta = lightInfo ? LIGHT_LEVELS[lightInfo.level] : null

  return (
    <div className="mobile-page">
      <div className="mob-header">
        <span className="mob-logo">🍃</span>
        <h1>Tea Analysis</h1>
        <p>Capture & Analyze</p>
      </div>

      {/* Camera Capture */}
      <div className="mob-capture-section">
        {previewUrl ? (
          <div className="mob-preview-wrapper">
            <img src={previewUrl} alt="Captured" className="mob-preview-img" />
            {uploading && <div className="mob-upload-badge">Uploading...</div>}
            {uploaded && <div className="mob-upload-badge sent">Sent to Desktop</div>}
          </div>
        ) : (
          <div className="mob-capture-area" onClick={() => fileInputRef.current.click()}>
            <span className="mob-camera-icon">📸</span>
            <p className="mob-capture-text">Tap to Capture</p>
            <p className="mob-capture-hint">Opens your phone camera</p>
          </div>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleCapture}
          hidden
        />
      </div>

      {/* Environment Analysis Mini Card */}
      {(envAnalysis || envLoading) && previewUrl && (
        <div className="mob-env-card">
          {envLoading ? (
            <div className="mob-env-loading">Analyzing environment...</div>
          ) : envAnalysis && (
            <>
              {/* Light Status */}
              <div className="mob-env-row">
                <span className="mob-env-icon">{lightMeta?.icon || '💡'}</span>
                <div className="mob-env-info">
                  <span className="mob-env-label" style={{ color: lightMeta?.color }}>
                    {lightInfo?.label}
                  </span>
                  <span className="mob-env-tip">{lightInfo?.tip}</span>
                </div>
                <span className="mob-env-pct">{envAnalysis.light.brightness_pct}%</span>
              </div>
              {/* Brightness Mini Bar */}
              <div className="mob-env-bar-wrap">
                <div className="mob-env-bar">
                  <div
                    className="mob-env-bar-marker"
                    style={{ left: `${envAnalysis.light.brightness_pct}%` }}
                  />
                </div>
              </div>
              {/* Dimensions */}
              {envAnalysis.dimensions.detected && envAnalysis.dimensions.primary_leaf && (
                <div className="mob-env-dims">
                  <div className="mob-env-dim">
                    <span className="mob-env-dim-val">
                      ~{envAnalysis.dimensions.primary_leaf.width_cm_est || envAnalysis.dimensions.primary_leaf.width_cm} cm
                    </span>
                    <span className="mob-env-dim-lbl">W</span>
                  </div>
                  <div className="mob-env-dim">
                    <span className="mob-env-dim-val">
                      ~{envAnalysis.dimensions.primary_leaf.height_cm_est || envAnalysis.dimensions.primary_leaf.height_cm} cm
                    </span>
                    <span className="mob-env-dim-lbl">H</span>
                  </div>
                  <div className="mob-env-dim">
                    <span className="mob-env-dim-val">{envAnalysis.dimensions.leaf_count}</span>
                    <span className="mob-env-dim-lbl">Leaves</span>
                  </div>
                  <div className="mob-env-dim">
                    <span className="mob-env-dim-val">{envAnalysis.dimensions.total_coverage_pct}%</span>
                    <span className="mob-env-dim-lbl">Cover</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Mode Toggle */}
      {previewUrl && !result && (
        <div className="mob-controls">
          <div className="mob-mode-toggle">
            <button
              className={`mob-mode-btn ${mode === 'detect' ? 'active' : ''}`}
              onClick={() => setMode('detect')}
            >
              Detect
            </button>
            <button
              className={`mob-mode-btn ${mode === 'classify' ? 'active' : ''}`}
              onClick={() => setMode('classify')}
            >
              Grade
            </button>
          </div>

          <button
            className="mob-analyze-btn"
            onClick={handleAnalyze}
            disabled={detecting}
          >
            {detecting ? 'Analyzing...' : `Analyze (${mode === 'detect' ? 'Detection' : 'Grading'})`}
          </button>
        </div>
      )}

      {/* Results */}
      {result && result.type === 'detect' && (
        <div className="mob-result">
          <h3>Detection Result</h3>
          <div className="mob-result-img-wrap">
            <img
              src={`data:image/jpeg;base64,${result.data.annotated_image}`}
              alt="Detection"
              className="mob-result-img"
            />
          </div>
          <div className="mob-metrics">
            <div className="mob-metric">
              <span className="mob-metric-val">{result.data.total_detections}</span>
              <span className="mob-metric-lbl">Detections</span>
            </div>
            <div className="mob-metric">
              <span className="mob-metric-val">{result.data.quality_grade?.split(' - ')[0]}</span>
              <span className="mob-metric-lbl">Grade</span>
            </div>
          </div>
          {result.data.class_counts && (
            <div className="mob-classes">
              {Object.entries(result.data.class_counts)
                .filter(([, c]) => c > 0)
                .map(([cls, count]) => (
                  <div key={cls} className="mob-class-row">
                    <span>{cls.replace(/_/g, ' ')}</span>
                    <span className="mob-class-count">{count}</span>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {result && result.type === 'classify' && (
        <div className="mob-result">
          <h3>Quality Result</h3>
          <div className={`mob-verdict ${result.data.prediction === 'high_quality' ? 'high' : 'med'}`}>
            <span className="mob-verdict-icon">
              {result.data.prediction === 'high_quality' ? '✅' : '⚠️'}
            </span>
            <span className="mob-verdict-label">
              {result.data.prediction === 'high_quality' ? 'High Quality' : 'Medium Quality'}
            </span>
          </div>
          {result.data.confidence && (
            <div className="mob-conf-bars">
              {Object.entries(result.data.confidence).map(([cls, prob]) => (
                <div key={cls} className="mob-conf-row">
                  <span className="mob-conf-label">
                    {cls === 'high_quality' ? 'High' : 'Medium'}
                  </span>
                  <div className="mob-conf-bar">
                    <div
                      className="mob-conf-fill"
                      style={{
                        width: `${prob}%`,
                        backgroundColor: cls === 'high_quality' ? '#4CAF50' : '#FF9800'
                      }}
                    />
                  </div>
                  <span className="mob-conf-val">{prob}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {result && result.type === 'error' && (
        <div className="mob-error">{result.data.message}</div>
      )}

      {/* Action Buttons */}
      {previewUrl && (
        <div className="mob-bottom-actions">
          <button className="mob-retake-btn" onClick={handleReset}>
            📸 Retake Photo
          </button>
          <button className="mob-retake-btn" onClick={() => fileInputRef.current.click()}>
            🖼️ Choose Another
          </button>
        </div>
      )}
    </div>
  )
}

export default MobileCapturePage
