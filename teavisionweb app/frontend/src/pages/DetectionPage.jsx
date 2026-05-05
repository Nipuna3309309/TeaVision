import { useState, useRef, useEffect } from 'react'
import ModelSelector from '../components/ModelSelector'
import './DetectionPage.css'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : `http://${window.location.hostname}:8000`

const CLASS_COLORS = {
  'Coarse_pluck': '#FFA500',
  'Damage_Spot': '#FF0000',
  'Damaged_Leaf': '#C80000',
  'Fresh_Bud_1': '#00FF00',
  'Fresh_Bud_2': '#00C800',
  'Old_Leaf': '#FFFF00',
  'stems': '#FF00FF'
}

const QUALITY_LABELS = {
  good: { label: 'Good (Fresh Buds)', color: '#4CAF50' },
  moderate: { label: 'Moderate', color: '#FF9800' },
  poor: { label: 'Poor (Damaged)', color: '#F44336' }
}

const LIGHT_LEVELS = {
  too_dark: { icon: '🌑', bg: '#ffebee' },
  poor: { icon: '🌙', bg: '#fff3e0' },
  good: { icon: '☀️', bg: '#e8f5e9' },
  bright: { icon: '🌤️', bg: '#f1f8e9' },
  too_bright: { icon: '🔆', bg: '#ffebee' },
}

function DetectionPage() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [confidence, setConfidence] = useState(0.35)
  const [useSahi, setUseSahi] = useState(false)
  const [selectedModel, setSelectedModel] = useState('teanet_rf_v4')
  const [yoloModels, setYoloModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [teavisionMeta, setTeavisionMeta] = useState(null)
  const fileInputRef = useRef(null)
  const cameraInputRef = useRef(null)

  // Track the last phone image timestamp to detect new uploads
  const lastPhoneTimestamp = useRef(0)

  useEffect(() => {
    fetch(`${API_BASE}/models`)
      .then(r => r.json())
      .then(data => setYoloModels(data.yolo_models || []))
      .catch(() => { })
  }, [])



  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setResult(null)
      setError(null)
      setTeavisionMeta(null)
    }
  }

  const handleCameraCapture = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setResult(null)
      setError(null)
      setTeavisionMeta(null)

      // Also auto-upload to backend for desktop sync
      const formData = new FormData()
      formData.append('file', file)
      fetch(`${API_BASE}/mobile/upload`, { method: 'POST', body: formData }).catch(() => { })
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setResult(null)
      setError(null)
      setTeavisionMeta(null)
    }
  }

  const handleDetect = async () => {
    if (!selectedFile) return

    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('confidence', confidence)
    formData.append('use_sahi', useSahi)
    formData.append('model', selectedModel)

    try {
      const res = await fetch(`${API_BASE}/detect`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      if (data.error) {
        setError(data.message || 'This image does not contain tea leaves on a white cloth. Please upload a valid image.')
        setResult(null)
      } else {
        setResult(data)
      }
    } catch (err) {
      setError('Detection failed. Make sure the backend is running on port 8000.')
    }
    setLoading(false)
  }

  const handleReset = () => {
    setSelectedFile(null)
    setPreviewUrl(null)
    setResult(null)
    setError(null)
    setTeavisionMeta(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (cameraInputRef.current) cameraInputRef.current.value = ''
  }

  const handleDownloadResult = () => {
    if (!result?.annotated_image) return
    const link = document.createElement('a')
    link.href = `data:image/jpeg;base64,${result.annotated_image}`
    link.download = `detection_result_${new Date().toISOString().slice(0, 10)}.jpg`
    link.click()
  }

  const handleLoadFromPhone = async () => {
    try {
      const res = await fetch(`${API_BASE}/mobile/latest`)
      const data = await res.json()
      if (!data.available) {
        setError('No image from phone yet. Use TeaVision app or scan the QR code first.')
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
      setTeavisionMeta(data.metadata || null)
    } catch {
      setError('Could not load phone image. Check backend connection.')
    }
  }

  const getGradeStyle = (grade) => {
    if (!grade || grade === 'N/A') return { bg: '#9E9E9E' }
    if (grade.startsWith('A')) return { bg: '#4CAF50' }
    if (grade.startsWith('B')) return { bg: '#8BC34A' }
    if (grade.startsWith('C')) return { bg: '#FF9800' }
    return { bg: '#F44336' }
  }

  return (
    <div className="detection-page">
      <div className="dp-header">
        <h1>Tea Leaf Detection</h1>
        <p>YOLOv8 + SAHI Object Detection for Tea Quality Analysis</p>
      </div>

      <div className="dp-controls-row">
        {/* Upload Area */}
        <div className="dp-upload-section">
          <div
            className="dp-upload-area"
            onClick={() => fileInputRef.current.click()}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" className="dp-upload-preview" />
            ) : (
              <div className="dp-upload-placeholder">
                <span className="dp-upload-icon">📷</span>
                <p className="dp-upload-text">Click or drag to upload</p>
                <p className="dp-upload-hint">JPG, JPEG, PNG supported</p>
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
          {/* Camera Capture Button */}
          <div className="dp-capture-buttons">
            <button className="dp-camera-btn" onClick={() => cameraInputRef.current.click()}>
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
            <button className="dp-phone-button" onClick={handleLoadFromPhone}>
              📱 From Phone
            </button>
          </div>
        </div>

        {/* Settings Panel */}
        <div className="dp-settings-panel">
          <h3>Detection Settings</h3>

          <ModelSelector
            models={yoloModels}
            selectedModel={selectedModel}
            onSelect={setSelectedModel}
            label="Detection Model"
          />

          <div className="dp-setting">
            <label>Confidence Threshold: <strong>{confidence.toFixed(2)}</strong></label>
            <input
              type="range"
              min="0.10"
              max="0.90"
              step="0.05"
              value={confidence}
              onChange={(e) => setConfidence(parseFloat(e.target.value))}
              className="dp-slider"
            />
            <div className="dp-slider-labels">
              <span>0.10 (Sensitive)</span>
              <span>0.90 (Strict)</span>
            </div>
          </div>

          <div className="dp-setting">
            <label className="dp-checkbox-label">
              <input
                type="checkbox"
                checked={useSahi}
                onChange={(e) => setUseSahi(e.target.checked)}
              />
              <span>Use SAHI (better for small objects)</span>
            </label>
          </div>

          <div className="dp-button-row">
            <button
              className="dp-detect-button"
              onClick={handleDetect}
              disabled={!selectedFile || loading}
            >
              {loading ? (
                <span className="dp-spinner">Detecting...</span>
              ) : (
                'Detect'
              )}
            </button>
            {selectedFile && (
              <button className="dp-reset-button" onClick={handleReset}>
                Reset
              </button>
            )}
          </div>


          {/* Class Legend */}
          <div className="dp-legend">
            <h4>Detection Classes</h4>
            <div className="dp-legend-items">
              {Object.entries(CLASS_COLORS).map(([cls, color]) => (
                <div key={cls} className="dp-legend-item">
                  <span className="dp-legend-dot" style={{ backgroundColor: color }} />
                  <span>{cls.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {error && <div className="dp-error">{error}</div>}

      {/* TeaVision Metadata Card */}
      {teavisionMeta && (teavisionMeta.measurement || teavisionMeta.light_analysis) && (
        <div className="dp-teavision-card">
          <div className="dp-tv-header">
            <span className="dp-tv-badge">📱 TeaVision Capture</span>
            {teavisionMeta.device?.model && (
              <span className="dp-tv-device">{teavisionMeta.device.manufacturer} {teavisionMeta.device.model}</span>
            )}
          </div>

          {/* TeaVision Light Analysis */}
          {teavisionMeta.light_analysis?.score != null && (
            <div className="dp-tv-light-row">
              <span className="dp-tv-light-icon">
                {teavisionMeta.light_analysis.level === 'good' ? '☀️' :
                  teavisionMeta.light_analysis.level === 'bright' ? '🌤️' :
                    teavisionMeta.light_analysis.level === 'poor' ? '🌙' :
                      teavisionMeta.light_analysis.level === 'too_dark' ? '🌑' : '🔆'}
              </span>
              <span className="dp-tv-light-label" style={{
                color: teavisionMeta.light_analysis.level === 'good' ? '#4CAF50' :
                  teavisionMeta.light_analysis.level === 'bright' ? '#8BC34A' :
                    teavisionMeta.light_analysis.level === 'poor' ? '#FF9800' : '#F44336'
              }}>
                {teavisionMeta.light_analysis.label} ({teavisionMeta.light_analysis.score}/100)
              </span>
              <span className="dp-tv-light-method">Device Sensor</span>
            </div>
          )}

          <div className="dp-tv-metrics">
            {teavisionMeta.light_analysis?.score != null && (
              <>
                <div className="dp-tv-metric">
                  <span className="dp-tv-val">{teavisionMeta.light_analysis.score}</span>
                  <span className="dp-tv-lbl">Light Score</span>
                </div>
                <div className="dp-tv-metric">
                  <span className="dp-tv-val">{teavisionMeta.light_analysis.bg_brightness?.toFixed(0)}</span>
                  <span className="dp-tv-lbl">BG Bright</span>
                </div>
              </>
            )}
            {teavisionMeta.measurement?.calibrated && (
              <>
                {teavisionMeta.measurement.leaf_width_cm && (
                  <div className="dp-tv-metric">
                    <span className="dp-tv-val">{teavisionMeta.measurement.leaf_width_cm.toFixed(1)} cm</span>
                    <span className="dp-tv-lbl">Width</span>
                  </div>
                )}
                {teavisionMeta.measurement.leaf_height_cm && (
                  <div className="dp-tv-metric">
                    <span className="dp-tv-val">{teavisionMeta.measurement.leaf_height_cm.toFixed(1)} cm</span>
                    <span className="dp-tv-lbl">Height</span>
                  </div>
                )}
                {teavisionMeta.measurement.leaf_area_cm2 && (
                  <div className="dp-tv-metric">
                    <span className="dp-tv-val">{teavisionMeta.measurement.leaf_area_cm2.toFixed(1)} cm²</span>
                    <span className="dp-tv-lbl">Area</span>
                  </div>
                )}
              </>
            )}
            {teavisionMeta.color_analysis?.greenness != null && (
              <div className="dp-tv-metric">
                <span className="dp-tv-val">{(teavisionMeta.color_analysis.greenness * 100).toFixed(0)}%</span>
                <span className="dp-tv-lbl">Greenness</span>
              </div>
            )}
            {teavisionMeta.color_analysis?.uniformity != null && (
              <div className="dp-tv-metric">
                <span className="dp-tv-val">{(teavisionMeta.color_analysis.uniformity * 100).toFixed(0)}%</span>
                <span className="dp-tv-lbl">Uniformity</span>
              </div>
            )}
            {teavisionMeta.quality?.blur_score != null && (
              <div className="dp-tv-metric">
                <span className="dp-tv-val">{teavisionMeta.quality.blur_score.toFixed(0)}</span>
                <span className="dp-tv-lbl">Sharpness</span>
              </div>
            )}
            {teavisionMeta.measurement?.segmentation_confidence != null && (
              <div className="dp-tv-metric">
                <span className="dp-tv-val">{(teavisionMeta.measurement.segmentation_confidence * 100).toFixed(0)}%</span>
                <span className="dp-tv-lbl">Seg. Conf.</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="dp-results">
          {/* Metrics Row */}
          <div className="dp-metrics-row">
            <div className="dp-metric-card">
              <span className="dp-metric-value">{result.total_detections}</span>
              <span className="dp-metric-label">Total Detections</span>
            </div>
            <div
              className="dp-metric-card dp-grade-card"
              style={{ borderTopColor: getGradeStyle(result.quality_grade).bg }}
            >
              <span
                className="dp-metric-value"
                style={{ color: getGradeStyle(result.quality_grade).bg }}
              >
                {result.quality_grade.split(' - ')[0]}
              </span>
              <span className="dp-metric-label">
                {result.quality_grade.split(' - ')[1] || 'Quality Grade'}
              </span>
            </div>
            <div className="dp-metric-card">
              <span className="dp-metric-value">
                {result.sahi_used ? 'SAHI' : 'Standard'}
              </span>
              <span className="dp-metric-label">Detection Mode</span>
            </div>
          </div>

          {/* Images Side by Side */}
          <div className="dp-images-row">
            <div className="dp-image-panel">
              <h3>Original Image</h3>
              <img src={previewUrl} alt="Original" />
            </div>
            <div className="dp-image-panel">
              <h3>Detection Result</h3>
              <img
                src={`data:image/jpeg;base64,${result.annotated_image}`}
                alt="Detection Result"
              />
            </div>
          </div>

          {/* Download Button */}
          <div className="dp-download-row">
            <button className="dp-download-btn" onClick={handleDownloadResult}>
              📥 Download Annotated Image
            </button>
          </div>

          {/* Details Row */}
          <div className="dp-details-row">
            {/* Class Counts */}
            <div className="dp-detail-card">
              <h3>Detection Breakdown</h3>
              <div className="dp-class-counts">
                {Object.entries(result.class_counts)
                  .filter(([, count]) => count > 0)
                  .sort(([, a], [, b]) => b - a)
                  .map(([cls, count]) => (
                    <div key={cls} className="dp-class-row">
                      <span
                        className="dp-class-dot"
                        style={{ backgroundColor: CLASS_COLORS[cls] }}
                      />
                      <span className="dp-class-name">{cls.replace(/_/g, ' ')}</span>
                      <span className="dp-class-count">{count}</span>
                    </div>
                  ))}
                {Object.values(result.class_counts).every(c => c === 0) && (
                  <p className="dp-no-detections">No objects detected. Try lowering the confidence threshold.</p>
                )}
              </div>
            </div>

            {/* Quality Breakdown */}
            {result.total_detections > 0 && (
              <div className="dp-detail-card">
                <h3>Quality Breakdown</h3>
                <div className="dp-quality-bars">
                  {['good', 'moderate', 'poor'].map(quality => (
                    <div key={quality} className="dp-quality-row">
                      <span
                        className="dp-quality-label"
                        style={{ color: QUALITY_LABELS[quality].color }}
                      >
                        {QUALITY_LABELS[quality].label}
                      </span>
                      <div className="dp-bar-container">
                        <div
                          className="dp-bar-fill"
                          style={{
                            width: `${result.quality_breakdown[quality + '_pct']}%`,
                            backgroundColor: QUALITY_LABELS[quality].color
                          }}
                        />
                      </div>
                      <span className="dp-quality-value">
                        {result.quality_breakdown[quality]} ({result.quality_breakdown[quality + '_pct'].toFixed(1)}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Disease Detection on Damaged Leaves */}
          {result.disease_analysis && result.disease_analysis.total_damaged_crops > 0 && (
            <div className="dp-disease-section">
              <h2 className="dp-disease-title">Disease Detection on Damaged Leaves</h2>
              <p className="dp-disease-subtitle">
                Found <strong>{result.disease_analysis.total_damaged_crops}</strong> damaged leaf region(s) — each analyzed by the Disease CNN model
              </p>
              <div className="dp-disease-grid">
                {result.disease_analysis.crops.map((crop) => (
                  <div key={crop.crop_index} className={`dp-disease-card ${crop.has_disease ? 'dp-disease-card--sick' : 'dp-disease-card--healthy'}`}>
                    <div className="dp-disease-card-img">
                      <img
                        src={`data:image/jpeg;base64,${crop.crop_image}`}
                        alt={`Crop #${crop.crop_index}`}
                      />
                      <span className="dp-disease-crop-badge">
                        #{crop.crop_index} — {crop.detection_class.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="dp-disease-card-body">
                      <div className={`dp-disease-verdict ${crop.has_disease ? 'dp-verdict-sick' : 'dp-verdict-healthy'}`}>
                        <span className="dp-verdict-icon">{crop.has_disease ? '⚠️' : '✅'}</span>
                        <span className="dp-verdict-name">{crop.disease}</span>
                        <span className="dp-verdict-conf">{crop.disease_confidence}%</span>
                      </div>
                      <div className="dp-disease-probs">
                        {Object.entries(crop.all_probabilities)
                          .sort(([, a], [, b]) => b - a)
                          .map(([cls, prob]) => (
                            <div key={cls} className="dp-prob-row">
                              <span className="dp-prob-name">{cls}</span>
                              <div className="dp-prob-bar-bg">
                                <div
                                  className="dp-prob-bar-fill"
                                  style={{
                                    width: `${prob}%`,
                                    backgroundColor: cls === crop.disease ? (crop.has_disease ? '#F44336' : '#4CAF50') : '#ccc'
                                  }}
                                />
                              </div>
                              <span className="dp-prob-val">{prob}%</span>
                            </div>
                          ))}
                      </div>
                      {crop.treatment && (
                        <div className="dp-disease-treatment">
                          <h4>Recommended Treatment</h4>
                          <div className="dp-treatment-tags">
                            <div className="dp-treat-group">
                              <span className="dp-treat-label">🌿 Organic</span>
                              <p>{crop.treatment.organic[0]}</p>
                            </div>
                            <div className="dp-treat-group">
                              <span className="dp-treat-label">✂️ Manual</span>
                              <p>{crop.treatment.manual[0]}</p>
                            </div>
                            <div className="dp-treat-group">
                              <span className="dp-treat-label">🧪 Chemical</span>
                              <p>{crop.treatment.chemical[0]}</p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No damaged leaves message */}
          {result.disease_analysis && result.disease_analysis.total_damaged_crops === 0 && result.total_detections > 0 && (
            <div className="dp-disease-healthy-msg">
              ✅ No damaged leaves found — all detected leaves appear healthy!
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default DetectionPage
