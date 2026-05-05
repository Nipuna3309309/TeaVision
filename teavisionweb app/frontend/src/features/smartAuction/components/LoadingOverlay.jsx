import './LoadingOverlay.css'

export default function LoadingOverlay({ show, text = 'Loading...' }) {
  if (!show) return null

  return (
    <div className="loading-overlay">
      <div className="loading-overlay__card">
        <div className="loading-overlay__spinner" />
        <p className="loading-overlay__text">{text}</p>
      </div>
    </div>
  )
}