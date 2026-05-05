import './LearningPanel.css'

export default function LearningPanel({ learnMessage }) {
  if (!learnMessage) return null

  return (
    <div className="learning-panel">
      <h2 className="learning-panel__title">Learning Result</h2>
      <p className="learning-panel__message">{learnMessage}</p>
    </div>
  )
}