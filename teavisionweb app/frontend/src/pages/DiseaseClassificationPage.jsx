import React, { useState } from "react";
import axios from "axios";
import "./DiseaseClassificationPage.css";

function DiseaseClassificationPage() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Google search state
  const [googleResults, setGoogleResults] = useState([])
  const [googleLoading, setGoogleLoading] = useState(false)
  const [googleError, setGoogleError] = useState(null)

  const fileInputRef = React.useRef(null)

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setResult(null)
      setError(null)
      setGoogleResults([])
      setGoogleError(null)
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
      setGoogleResults([])
      setGoogleError(null)
    }
  }

  const fetchGoogleResults = async (diseaseName) => {
    if (diseaseName === 'Healthy') return
    setGoogleLoading(true)
    setGoogleError(null)
    try {
      const res = await axios.get(
        `http://localhost:8000/google-disease-search?disease=${encodeURIComponent(diseaseName)}&num_results=6`
      )
      if (res.data.error) {
        setGoogleError(res.data.error)
        setGoogleResults([])
      } else {
        setGoogleResults(res.data.results || [])
      }
    } catch (err) {
      console.error('Google search failed:', err)
      setGoogleError('Could not fetch web results. Backend may be unreachable.')
    }
    setGoogleLoading(false)
  }

  const handlePredict = async () => {
    if (!selectedFile) return
    setLoading(true)
    setError(null)
    setGoogleResults([])

    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await axios.post(
        'http://localhost:8000/predict-disease',
        formData
      )
      setResult(response.data)
      // Automatically fetch Google results for detected disease
      if (response.data.has_issue) {
        fetchGoogleResults(response.data.predicted_disease)
      }
    } catch (err) {
      console.error(err)
      setError('Prediction failed. Please make sure the backend is running.')
    }
    setLoading(false)
  }

  const handleReset = () => {
    setSelectedFile(null)
    setPreviewUrl(null)
    setResult(null)
    setError(null)
    setGoogleResults([])
    setGoogleError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="disease-page">
      <div className="dsp-header">
        <h1>Tea Leaf Disease Classification</h1>
        <p>Premium AI-driven analysis for tea plantation health monitoring</p>
      </div>

      <div className="dsp-controls-row">
        {/* Upload Section */}
        <div className="dsp-upload-section">
          <div
            className="dsp-upload-area"
            onClick={() => fileInputRef.current.click()}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" className="dsp-upload-preview" />
            ) : (
              <div className="dsp-upload-placeholder">
                <span className="dsp-upload-icon">🍃</span>
                <p>Click or drag to upload leaf image</p>
                <p className="dsp-upload-hint">JPG, JPEG, PNG</p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>
        </div>

        {/* Settings & Detection Panel */}
        <div className="dsp-settings-panel">
          <h3>Classification Panel</h3>

          <div className="dsp-button-row">
            <button
              className="dsp-predict-button"
              onClick={handlePredict}
              disabled={!selectedFile || loading}
            >
              {loading ? 'Analyzing...' : 'Predict Disease'}
            </button>
            {selectedFile && (
              <button className="dsp-reset-button" onClick={handleReset}>
                Reset
              </button>
            )}
          </div>

          <div className="dsp-info-box">
            <h4>Diagnostic Engine</h4>
            <div className="dsp-info-text">
              Our CNN model analyzes patterns to identify common tea leaf and pest pathologies with high precision.
              <br /><br />
              • Accuracy-optimized (94%+)
              <br />
              • Real-time edge inference
              <br />
              • Google-powered web research
            </div>
          </div>
        </div>
      </div>

      {error && <div className="dsp-error">{error}</div>}

      {/* Results Section */}
      {result && (
        <div className="dsp-results-container">
          <div className="dsp-main-result-card">
            <div className="dsp-card-glow"></div>

            <div className="dsp-result-layout">
              {/* Circular Gauge Section */}
              <div className="dsp-gauge-section">
                <div className="dsp-circular-gauge">
                  <svg viewBox="0 0 100 100">
                    <circle className="gauge-bg" cx="50" cy="50" r="45" />
                    <circle
                      className="gauge-fill"
                      cx="50" cy="50" r="45"
                      style={{
                        strokeDasharray: `${result.confidence * 283} 283`,
                        stroke: result.confidence > 0.8 ? '#a8e063' : '#fbbf24'
                      }}
                    />
                  </svg>
                  <div className="gauge-content">
                    <span className="gauge-value">{(result.confidence * 100).toFixed(0)}%</span>
                    <span className="gauge-label">Confidence</span>
                  </div>
                </div>
              </div>

              {/* Verdict Text Section */}
              <div className="dsp-verdict-details">
                <div className="dsp-status-badge">
                  {!result.has_issue ? 'HEALTHY' : 'PATHOLOGY DETECTED'}
                </div>
                <h2 className="dsp-disease-name">{result.predicted_disease}</h2>
                <p className="dsp-disease-desc">
                  {!result.has_issue
                    ? 'AI analysis confirms your tea crop is currently in optimal condition.'
                    : 'A potential health issue has been identified. Immediate action is recommended to prevent spreading.'}
                </p>

                <div className="dsp-meta-grid">
                  <div className="meta-item">
                    <span className="meta-icon">CNN</span>
                    <div>
                      <strong>Analysis</strong>
                      <span>Real-time CNN Inferred</span>
                    </div>
                  </div>
                  <div className="meta-item">
                    <span className="meta-icon">TIME</span>
                    <div>
                      <strong>Checked</strong>
                      <span>{new Date().toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>

          {/* XAI Heatmap Card (Dedicated) */}
          <div className="dsp-xai-card">
            <div className="xai-header">
              <span className="xai-badge">EXPLAINABLE AI (XAI)</span>
              <h4>            </h4>
              <h4>Model Interpretability: Grad-CAM Analysis</h4>
            </div>

            {!result.heatmap ? (
              <div className="xai-no-data">
                <span className="xai-warning-icon">!</span>
                <p>Detailed interpretability data is still processing or not available for this specific diagnosis.</p>
              </div>
            ) : (
              <div className="xai-content-grid">
                <div className="xai-image-container">
                  <div className="xai-image-label">AI Focused Regions</div>
                  <img
                    src={`data:image/jpeg;base64,${result.heatmap}`}
                    alt="AI Focus Map"
                    className="xai-main-heatmap"
                  />
                </div>

                <div className="xai-text-logic">
                  <h5>How the AI "Thinks"</h5>
                  <p>
                    The <strong>Gradient-weighted Class Activation Mapping (Grad-CAM)</strong> visualization highlights the AI's exact focus. The model identifies the disease by targeting the patterns shown in warm colors (red/yellow).
                  </p>
                  <ul className="xai-features">
                    <li><strong>Red/Orange:</strong> The core problem area (the disease lesion or pest).</li>
                    <li><strong>Yellow:</strong> Supporting textures and secondary indicators.</li>
                    <li><strong>Blue/Green:</strong> Healthy leaf and background that the AI ignored.</li>
                  </ul>
                  <div className="xai-tech-tag">Technology: Model-Agnostic Interpretability Engine</div>
                </div>
              </div>
            )}
          </div>

          {result.has_issue && (
            <div className="dsp-guidance-grid">
              <div className="dsp-guidance-card treatment">
                <div className="card-header">
                  <span className="card-icon">Rx</span>
                  <h3>Treatment Guidance</h3>
                </div>
                <p>{result.treatment}</p>
              </div>

              <div className="dsp-guidance-card prevention">
                <div className="card-header">
                  <span className="card-icon">DEF</span>
                  <h3>Prevention Strategy</h3>
                </div>
                <p>{result.prevention}</p>
              </div>
            </div>
          )}

          {/* Google Web Research Section */}
          {result.has_issue && (
            <div className="dsp-google-section">
              <div className="dsp-google-header">
                <h3>Web Research: {result.predicted_disease}</h3>
                <span className="dsp-google-badge">Google Search API</span>
              </div>

              {googleLoading && (
                <div className="dsp-google-loading">
                  <div className="dsp-google-spinner" />
                  <p>Searching the web for "{result.predicted_disease}"...</p>
                </div>
              )}

              {googleError && (
                <div className="dsp-google-error">
                  <p>{googleError}</p>
                  <button
                    className="dsp-google-retry"
                    onClick={() => fetchGoogleResults(result.predicted_disease)}
                  >
                    Retry Search
                  </button>
                </div>
              )}

              {!googleLoading && googleResults.length > 0 && (
                <div className="dsp-google-grid">
                  {googleResults.map((item, idx) => (
                    <a
                      key={idx}
                      href={item.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="dsp-google-card"
                    >
                      <div className="dsp-google-card-header">
                        <span className="dsp-google-source">{item.source}</span>
                        <span className="dsp-google-arrow">-></span>
                      </div>
                      <h4>{item.title}</h4>
                      <p>{item.snippet}</p>
                    </a>
                  ))}
                </div>
              )}

              {!googleLoading && !googleError && googleResults.length === 0 && (
                <div className="dsp-google-empty">
                  <p>No web results available. Configure GOOGLE_API_KEY in .env to enable.</p>
                  <button
                    className="dsp-google-retry"
                    onClick={() => fetchGoogleResults(result.predicted_disease)}
                  >
                    Search Now
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default DiseaseClassificationPage;
