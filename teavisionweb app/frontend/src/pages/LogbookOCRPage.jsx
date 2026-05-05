import { useState, useRef, useCallback, useEffect } from 'react'
import MobileConnect from '../components/MobileConnect'
import './LogbookOCRPage.css'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : `http://${window.location.hostname}:8000`

const COL_ORDER = [
  'No', 'Month', 'Yield_Mo', 'Todate', 'Annual',
  'Mixture', 'N', 'P', 'K', 'Mg/MOP',
  'Zinc', 'Urea', "C'cal", "M'ual", 'Weeding',
  'Rainfall', 'Remarks'
]

const EMPTY_ROW = () => COL_ORDER.reduce((acc, col) => ({ ...acc, [col]: '' }), {})

const PROGRESS_STAGES = [
  { label: 'Uploading image...', icon: '📤', pct: 5 },
  { label: 'Perspective correction & grid detection...', icon: '📐', pct: 15 },
  { label: 'Splitting tables...', icon: '📊', pct: 25 },
  { label: 'Running cell-by-cell OCR (this takes the longest)...', icon: '🔍', pct: 40 },
  { label: 'Post-processing with fuzzy matching...', icon: '🧠', pct: 75 },
  { label: 'Building structured output...', icon: '📋', pct: 90 },
  { label: 'Finalizing...', icon: '✅', pct: 95 },
]

/* ── Resize large images client-side before upload to reduce OCR time ── */
const MAX_CLIENT_UPLOAD_DIM = 5000
const RESIZED_UPLOAD_QUALITY = 0.98

function prepareImageForUpload(file, maxDim = MAX_CLIENT_UPLOAD_DIM) {
  return new Promise((resolve) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(url)
      const { width, height } = img
      if (width <= maxDim && height <= maxDim) {
        resolve(file) // Already small enough
        return
      }
      const scale = maxDim / Math.max(width, height)
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(width * scale)
      canvas.height = Math.round(height * scale)
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      canvas.toBlob((blob) => {
        if (!blob) {
          resolve(file)
          return
        }
        const outType = file.type && file.type.startsWith('image/') ? file.type : 'image/jpeg'
        const resized = new File([blob], file.name, { type: outType })
        resolve(resized)
      }, file.type || 'image/jpeg', RESIZED_UPLOAD_QUALITY)
    }
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file) }
    img.src = url
  })
}

function LogbookOCRPage() {
  const [mode, setMode] = useState('ocr')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [activeTable, setActiveTable] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [progressStage, setProgressStage] = useState(0)
  const [showMobileConnect, setShowMobileConnect] = useState(false)
  const [ocrAvailable, setOcrAvailable] = useState(null)
  const [manualRows, setManualRows] = useState(() => Array.from({ length: 12 }, EMPTY_ROW))
  const fileRef = useRef(null)
  const abortRef = useRef(null)
  const timerRef = useRef(null)
  


  // Check OCR status on mount
  useEffect(() => {
    fetch(`${API_BASE}/ocr/status`)
      .then(r => r.json())
      .then(d => setOcrAvailable(d.available))
      .catch(() => setOcrAvailable(false))
  }, [])


  


  const handleFileSelect = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)
    setResult(null)
    setError(null)
    const reader = new FileReader()
    reader.onload = (ev) => setPreview(ev.target.result)
    reader.readAsDataURL(f)
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    const f = e.dataTransfer?.files?.[0]
    if (!f || !f.type.startsWith('image/')) return
    setFile(f)
    setResult(null)
    setError(null)
    const reader = new FileReader()
    reader.onload = (ev) => setPreview(ev.target.result)
    reader.readAsDataURL(f)
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
  }, [])

  const downloadExcelFromResult = async (data) => {
    try {
      const res = await fetch(`${API_BASE}/ocr/extract-excel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (!res.ok) return
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'logbook_ocr_output.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* silent */ }
  }

  const handleCancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setLoading(false)
    setElapsed(0)
    setProgressStage(0)
    setError('Extraction cancelled.')
  }, [])



  const handleLoadFromPhone = async () => {
    try {
      const res = await fetch(`${API_BASE}/mobile/latest`)
      const data = await res.json()
      if (!data.available) {
        setError('No image from phone yet. Scan the QR code and use the mobile interface first.')
        return
      }
      
      const byteStr = atob(data.image)
      const bytes = new Uint8Array(byteStr.length)
      for (let i = 0; i < byteStr.length; i++) bytes[i] = byteStr.charCodeAt(i)
      const blob = new Blob([bytes], { type: 'image/jpeg' })
      const mFile = new File([blob], data.filename || 'phone_logbook.jpg', { type: 'image/jpeg' })
      
      setFile(mFile)
      setResult(null)
      setError(null)
      const reader = new FileReader()
      reader.onload = (ev) => setPreview(ev.target.result)
      reader.readAsDataURL(mFile)
    } catch {
      setError('Could not load phone image. Check backend connection.')
    }
  }

  const handleExtract = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    setElapsed(0)
    setProgressStage(0)

    const controller = new AbortController()
    abortRef.current = controller

    // Keep original resolution for OCR unless the image is extremely large
    const processedFile = await prepareImageForUpload(file)

    // Start elapsed timer & progress simulation
    const t0 = Date.now()
    timerRef.current = setInterval(() => {
      const sec = Math.floor((Date.now() - t0) / 1000)
      setElapsed(sec)
      // Simulate progress stages based on elapsed time
      if (sec < 3) setProgressStage(0)
      else if (sec < 8) setProgressStage(1)
      else if (sec < 15) setProgressStage(2)
      else if (sec < 120) setProgressStage(3)
      else if (sec < 180) setProgressStage(4)
      else if (sec < 240) setProgressStage(5)
      else setProgressStage(6)
    }, 1000)

    const formData = new FormData()
    formData.append('file', processedFile)

    try {
      const res = await fetch(`${API_BASE}/ocr/extract`, {
        method: 'POST',
        body: formData,
        signal: controller.signal
      })

      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(
          res.status === 500
            ? 'Backend processing error — the OCR engine encountered an issue with this image. Try uploading a clearer photo.'
            : res.status === 422
              ? 'Invalid file format. Please upload a JPEG or PNG image.'
              : `Server error (${res.status}). ${text.slice(0, 200)}`
        )
      }

      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        setProgressStage(6) // Done
        setResult(data)
        const tables = Object.keys(data.tables || {})
        if (tables.length > 0) setActiveTable(tables[0])
        downloadExcelFromResult(data)
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Extraction cancelled.')
      } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        setError('Cannot connect to backend server (port 8000). Make sure the server is running.')
      } else {
        setError(err.message || 'OCR extraction failed.')
      }
    } finally {
      clearInterval(timerRef.current)
      timerRef.current = null
      abortRef.current = null
      setLoading(false)
    }
  }

  const handleDownloadExcel = async () => {
    if (!result) return
    setDownloading(true)
    try {
      const res = await fetch(`${API_BASE}/ocr/extract-excel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(result)
      })
      if (!res.ok) throw new Error('Download failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'logbook_ocr_output.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('Excel download failed.')
    }
    setDownloading(false)
  }

  // ── Manual Entry helpers ──
  const updateManualCell = (rowIdx, col, value) => {
    setManualRows(prev => {
      const copy = [...prev]
      copy[rowIdx] = { ...copy[rowIdx], [col]: value }
      return copy
    })
  }

  const addManualRow = () => setManualRows(prev => [...prev, EMPTY_ROW()])

  const removeManualRow = (idx) => {
    setManualRows(prev => prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev)
  }

  const downloadManualCSV = () => {
    const filled = manualRows.filter(r => Object.values(r).some(v => v.trim()))
    if (!filled.length) return
    const header = COL_ORDER.join(',')
    const body = filled.map(r => COL_ORDER.map(c => `"${(r[c] || '').replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([header + '\n' + body], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'logbook_manual_entry.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadManualExcel = async () => {
    setDownloading(true)
    try {
      const payload = {
        tables: {
          'Manual_Entry': {
            rows: manualRows.filter(r => Object.values(r).some(v => v.trim())),
            data_rows: manualRows.filter(r => Object.values(r).some(v => v.trim())).length
          }
        }
      }
      const res = await fetch(`${API_BASE}/ocr/extract-excel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!res.ok) throw new Error()
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'logbook_manual_entry.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      downloadManualCSV() // fallback
    }
    setDownloading(false)
  }

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`
  }

  const currentRows = result?.tables?.[activeTable]?.rows || []
  const stage = PROGRESS_STAGES[progressStage] || PROGRESS_STAGES[0]

  return (
    <div className="ocr-page">
      <div className="ocr-header">
        <h1>Logbook OCR Extraction</h1>

        <span className="ocr-badge">
          Digitize Tea Yield Book Images
        </span>
      </div>

      {/* Mode Toggle */}
      <div className="ocr-mode-toggle">
        <button
          className={`ocr-mode-btn ${mode === 'ocr' ? 'active' : ''}`}
          onClick={() => { setMode('ocr'); setError(null) }}
        >
          <span className="ocr-mode-icon">📷</span>
          OCR Scan
          <span className="ocr-mode-tag primary">Primary</span>
        </button>
        <button
          className={`ocr-mode-btn ${mode === 'manual' ? 'active' : ''}`}
          onClick={() => { setMode('manual'); setError(null) }}
        >
          <span className="ocr-mode-icon">✏️</span>
          Manual Entry
          <span className="ocr-mode-tag">Fallback</span>
        </button>
      </div>

      {/* OCR Status Banner */}
      {mode === 'ocr' && ocrAvailable === false && (
        <div className="ocr-warning">
          <span>⚠️</span>
          <span>OCR engine is not available. Start the backend server first (<code>python main.py</code>).</span>
        </div>
      )}
      {mode === 'ocr' && ocrAvailable === true && !loading && !result && (
        <div className="ocr-ready-banner">
          <span>✅</span>
          <span>OCR Engine ready-Upload a logbook image to extract data automatically</span>
        </div>
      )}

      {error && (
        <div className="ocr-error">
          <span className="ocr-error-icon">⚠️</span>
          <div>
            <div className="ocr-error-text">{error}</div>
            {mode === 'ocr' && !error.includes('cancelled') && (
              <button className="ocr-switch-mode-link" onClick={() => { setMode('manual'); setError(null) }}>
                Or use Manual Entry as fallback →
              </button>
            )}
          </div>
        </div>
      )}

      {/* ─── OCR MODE ─── */}
      {mode === 'ocr' && (
        <>
          <div className="ocr-upload-section">
            <div className="ocr-upload-left">
              <div
                className={`ocr-dropzone ${preview ? 'has-image' : ''}`}
                onClick={() => fileRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
              >
                {preview ? (
                  <img src={preview} alt="Logbook" className="ocr-preview-img" />
                ) : (
                  <div className="ocr-dropzone-inner">
                    <span className="ocr-drop-icon">📄</span>
                    <span className="ocr-drop-text">Drop logbook image here or click to upload</span>
                    <span className="ocr-drop-sub">JPEG, PNG supported • Original resolution preserved for OCR</span>
                  </div>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
                <button 
                  className="ocr-mode-btn" 
                  onClick={() => setShowMobileConnect(true)}
                  style={{ flex: 1, justifyContent: 'center' }}
                >
                  <span className="ocr-mode-icon">📱</span> QR Connect
                </button>
                <button 
                  className="ocr-extract-btn" 
                  onClick={handleLoadFromPhone}
                  style={{ flex: 1, margin: 0, padding: '10px' }}
                >
                   From Phone
                </button>
              </div>
              {file && (
                <div className="ocr-file-info">
                  📎 {file.name} ({(file.size / 1024).toFixed(0)} KB)
                </div>
              )}
            </div>

            <div className="ocr-upload-right">
              <div className="ocr-pipeline-info">
                <h3>🔬 OCR Pipeline-How It Works</h3>
                <div className="ocr-steps">
                  {[
                    { num: 1, title: 'Image & Grid' },
                    { num: 2, title: 'Cell OCR', },
                    { num: 3, title: 'Post-Processing', },
                    { num: 4, title: 'Structured Output', },
                  ].map(s => (
                    <div className="ocr-step" key={s.num}>
                      <span className="ocr-step-num">{s.num}</span>
                      <div>
                        <strong>{s.title}</strong>
                        <p>{s.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {!loading ? (
                <button
                  className="ocr-extract-btn"
                  onClick={handleExtract}
                  disabled={!file || ocrAvailable === false}
                >
                  🚀 Extract Table Data
                </button>
              ) : (
                <div className="ocr-progress-panel">
                  <div className="ocr-progress-header">
                    <span className="ocr-spinner" />
                    <span>Processing — {formatTime(elapsed)}</span>
                    <button className="ocr-cancel-btn" onClick={handleCancel}>Cancel</button>
                  </div>
                  <div className="ocr-progress-bar-track">
                    <div className="ocr-progress-bar-fill" style={{ width: `${stage.pct}%` }} />
                  </div>
                  <div className="ocr-progress-stage">
                    <span>{stage.icon}</span>
                    <span>{stage.label}</span>
                  </div>
                  {elapsed > 60 && (
                    <div className="ocr-progress-tip">
                      💡 Tip: OCR processes each cell individually — larger tables take longer. This is normal.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* OCR Results */}
          {result && (
            <div className="ocr-results">
              <div className="ocr-success-banner">
                ✅ Extraction complete — {Object.values(result.tables).reduce((s, t) => s + t.data_rows, 0)} data rows extracted in {formatTime(elapsed)}
              </div>

              <div className="ocr-summary-row">
                <div className="ocr-summary-card">
                  <span className="ocr-summary-val">{result.layout}</span>
                  <span className="ocr-summary-lbl">Layout Detected</span>
                </div>
                <div className="ocr-summary-card">
                  <span className="ocr-summary-val">{result.total_tables}</span>
                  <span className="ocr-summary-lbl">Tables Found</span>
                </div>
                <div className="ocr-summary-card">
                  <span className="ocr-summary-val">{result.image_size}</span>
                  <span className="ocr-summary-lbl">Image Size (px)</span>
                </div>
                <div className="ocr-summary-card">
                  <span className="ocr-summary-val">
                    {Object.values(result.tables).reduce((s, t) => s + t.data_rows, 0)}
                  </span>
                  <span className="ocr-summary-lbl">Data Rows Extracted</span>
                </div>
              </div>

              <div className="ocr-download-row">
                <button
                  className="ocr-download-btn"
                  onClick={handleDownloadExcel}
                  disabled={downloading}
                >
                  {downloading ? 'Generating...' : '📥 Download as Excel (.xlsx)'}
                </button>
              </div>

              {Object.keys(result.tables).length > 1 && (
                <div className="ocr-table-tabs">
                  {Object.keys(result.tables).map(tbl => (
                    <button
                      key={tbl}
                      className={`ocr-tab ${activeTable === tbl ? 'active' : ''}`}
                      onClick={() => setActiveTable(tbl)}
                    >
                      {tbl} ({result.tables[tbl].data_rows} rows)
                    </button>
                  ))}
                </div>
              )}

              <div className="ocr-data-card">
                <h3>
                  {activeTable} — {result.tables[activeTable]?.data_rows} data rows
                  {result.tables[activeTable]?.grid_size && ` • ${result.tables[activeTable].grid_size} grid`}
                </h3>
                <div className="ocr-table-wrap">
                  <table className="ocr-table">
                    <thead>
                      <tr>
                        {COL_ORDER.map(col => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {currentRows.map((row, i) => (
                        <tr key={i}>
                          {COL_ORDER.map(col => {
                            const val = row[col] || ''
                            const conf = row[`${col}_conf`]
                            const isLowConf = conf !== undefined && conf < 0.55
                            return (
                              <td
                                key={col}
                                className={`${isLowConf ? 'ocr-low-conf' : ''} ${col === 'Month' ? 'ocr-month-cell' : ''}`}
                                title={conf !== undefined ? `Confidence: ${(conf * 100).toFixed(0)}%` : ''}
                              >
                                {val}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ─── MANUAL ENTRY MODE (Fallback) ─── */}
      {mode === 'manual' && (
        <div className="ocr-manual-section">
          <div className="ocr-manual-header">
            <div>
              <h3>Manual Data Entry (Fallback)</h3>
              <p className="ocr-manual-sub">
                Enter logbook data directly if OCR is unavailable. {manualRows.length} rows.
              </p>
            </div>
            <div className="ocr-manual-actions">
              <button className="ocr-add-row-btn" onClick={addManualRow}>+ Add Row</button>
              <button className="ocr-download-btn" onClick={downloadManualExcel}
                disabled={downloading || !manualRows.some(r => Object.values(r).some(v => v.trim()))}>
                {downloading ? 'Downloading...' : 'Download Excel'}
              </button>
              <button className="ocr-csv-btn" onClick={downloadManualCSV}
                disabled={!manualRows.some(r => Object.values(r).some(v => v.trim()))}>
                Download CSV
              </button>
            </div>
          </div>

          <div className="ocr-table-wrap">
            <table className="ocr-table ocr-editable-table">
              <thead>
                <tr>
                  <th className="ocr-row-action-th">#</th>
                  {COL_ORDER.map(col => <th key={col}>{col}</th>)}
                  <th className="ocr-row-action-th"></th>
                </tr>
              </thead>
              <tbody>
                {manualRows.map((row, ri) => (
                  <tr key={ri}>
                    <td className="ocr-row-num">{ri + 1}</td>
                    {COL_ORDER.map(col => (
                      <td key={col} className="ocr-edit-cell">
                        <input
                          type="text"
                          value={row[col]}
                          onChange={(e) => updateManualCell(ri, col, e.target.value)}
                          placeholder={col === 'Month' ? 'Jan' : col === 'No' ? `${ri + 1}` : '—'}
                          className="ocr-cell-input"
                        />
                      </td>
                    ))}
                    <td className="ocr-row-action">
                      <button className="ocr-remove-row-btn" onClick={() => removeManualRow(ri)} title="Remove row">×</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showMobileConnect && (
        <MobileConnect onClose={() => setShowMobileConnect(false)} />
      )}
    </div>
  )
}

export default LogbookOCRPage
