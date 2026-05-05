import { useState, useEffect } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import './MobileConnect.css'

const API_BASE = 'http://localhost:8000'

function MobileConnect({ onClose }) {
  const [networkInfo, setNetworkInfo] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/network-info`)
      .then(r => r.json())
      .then(data => setNetworkInfo(data))
      .catch(() => {})
  }, [])

  const mobileUrl = networkInfo
    ? `http://${networkInfo.lan_ip}:${networkInfo.frontend_port}#mobile`
    : null

  const handleCopy = () => {
    if (mobileUrl) {
      navigator.clipboard.writeText(mobileUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="mc-overlay" onClick={onClose}>
      <div className="mc-modal" onClick={e => e.stopPropagation()}>
        <button className="mc-close" onClick={onClose}>X</button>

        <div className="mc-header">
          <span className="mc-phone-icon">📱</span>
          <h2>Connect Your Phone</h2>
          <p>Scan the QR code to capture images from your phone camera</p>
        </div>

        {mobileUrl ? (
          <div className="mc-qr-section">
            <div className="mc-qr-wrapper">
              <QRCodeSVG
                value={mobileUrl}
                size={220}
                bgColor="#ffffff"
                fgColor="#1a472a"
                level="M"
                includeMargin={true}
              />
            </div>

            <div className="mc-steps">
              <div className="mc-step">
                <span className="mc-step-num">1</span>
                <span>Open camera app on your phone</span>
              </div>
              <div className="mc-step">
                <span className="mc-step-num">2</span>
                <span>Scan the QR code above</span>
              </div>
              <div className="mc-step">
                <span className="mc-step-num">3</span>
                <span>Capture a tea leaf image</span>
              </div>
              <div className="mc-step">
                <span className="mc-step-num">4</span>
                <span>Click "Load from Phone" on any page</span>
              </div>
            </div>

            <div className="mc-url-row">
              <code className="mc-url">{mobileUrl}</code>
              <button className="mc-copy-btn" onClick={handleCopy}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>

            <p className="mc-note">
              Both devices must be on the same WiFi network
            </p>
          </div>
        ) : (
          <div className="mc-loading">
            <p>Connecting to backend...</p>
            <p className="mc-hint">Make sure the backend is running on port 8000</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default MobileConnect
