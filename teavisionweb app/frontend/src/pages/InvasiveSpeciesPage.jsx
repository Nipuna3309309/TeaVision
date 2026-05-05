import React, { useState, useRef } from 'react'
import axios from 'axios'
import './InvasiveSpeciesPage.css'

function InvasiveSpeciesPage() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const fileInputRef = useRef(null)

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setResult(null)
      setError(null)
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
    }
  }

  const handleDetect = async () => {
    if (!selectedFile) return
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await axios.post(
        'http://localhost:8000/predict-invasive',
        formData
      )
      setResult(response.data)
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
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="invasive-page">
      <div className="isp-header">
        <h1>Invasive Species Detection</h1>
        <p>CNN-based identification of invasive flora across tea plantations</p>
      </div>

      <div className="isp-controls-row">
        {/* Upload Section */}
        <div className="isp-upload-section">
          <div
            className="isp-upload-area"
            onClick={() => fileInputRef.current.click()}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            {previewUrl ? (
              <img src={previewUrl} alt="Preview" className="isp-upload-preview" />
            ) : (
              <div className="isp-upload-placeholder">
                <span className="isp-upload-icon">🪴</span>
                <p>Click or drag to upload</p>
                <p className="isp-upload-hint">JPG, JPEG, PNG</p>
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
        <div className="isp-settings-panel">
          <h3>Detection Panel</h3>

          <div className="isp-button-row">
            <button
              className="isp-detect-button"
              onClick={handleDetect}
              disabled={!selectedFile || loading}
            >
              {loading ? 'Detecting...' : 'Detect Species'}
            </button>
            {selectedFile && (
              <button className="isp-reset-button" onClick={handleReset}>
                Reset
              </button>
            )}
          </div>

          <div className="isp-info-box">
            <h4>Detection Engine</h4>
            <div className="isp-info-text">
              Predicting probabilities across 5 classes:
              <br />
              • Lantana Camara
              <br />
              • Mikania micrantha
              <br />
              • Mimosa diplotricha
              <br />
              • Sphagneticola trilobata
              <br />
              • Tridax Procumbens
            </div>
          </div>
        </div>
      </div>

      {error && <div className="isp-error">{error}</div>}

      {/* Results */}
      {result && (
        <div className="isp-results">
          <div className="isp-verdict">
            <div className="isp-verdict-icon">
              {result.confidence > 0.8 ? '✅' : '⚠️'}
            </div>
            <div className="isp-verdict-text">
              <span className="isp-verdict-label">
                {result.species}
              </span>
              <span className="isp-verdict-desc">
                Identified as the primary invasive species in the image.
              </span>
              <div className="isp-confidence-bar-wrap">
                <div className="isp-conf-label-row">
                  <span>Confidence Level</span>
                  <span>{(result.confidence * 100).toFixed(2)}%</span>
                </div>
                <div className="isp-conf-bg">
                  <div
                    className="isp-conf-fill"
                    style={{
                      width: `${(result.confidence * 100).toFixed(2)}%`,
                      backgroundColor: result.confidence > 0.8 ? '#4CAF50' : '#FF9800'
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="isp-solution-container">
            <h3>Expert Management Solutions</h3>
            <div className="isp-solution-grid">
              <div className="isp-solution-card manual">
                <div className="card-header">
                  <span className="card-icon">🛠️</span>
                  <h4>Manual Extraction</h4>
                </div>
                <p>{result.manual_sol}</p>
              </div>

              <div className="isp-solution-card organic">
                <div className="card-header">
                  <span className="card-icon">🍃</span>
                  <h4>Organic & Biological</h4>
                </div>
                <p>{result.organic_sol}</p>
              </div>

              <div className="isp-solution-card chemical">
                <div className="card-header">
                  <span className="card-icon">🧪</span>
                  <h4>Regulated Chemical</h4>
                </div>
                <p>{result.chemical_sol}</p>
              </div>

              <div className="isp-solution-card prevention">
                <div className="card-header">
                  <span className="card-icon">🛡️</span>
                  <h4>Long-term Prevention</h4>
                </div>
                <p>{result.prevention_sol}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default InvasiveSpeciesPage