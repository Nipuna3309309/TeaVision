import { useState, useEffect } from 'react'
import './DashboardPage.css'

const API_BASE = `http://${window.location.hostname}:8000`

const QUICK_ACTIONS = [
  {
    id: 'detection',
    icon: '📸',
    title: 'Quick Leaf Scan',
    description: 'Take a photo and instantly identify leaf types, freshness, and damage',
    color: '#4CAF50',
    gradient: 'linear-gradient(135deg, #2E7D32, #4CAF50)',
  },
  {
    id: 'grading',
    icon: '⭐',
    title: 'Grade My Tea',
    description: 'Upload a photo to get an AI-powered quality assessment',
    color: '#FF9800',
    gradient: 'linear-gradient(135deg, #E65100, #FF9800)',
  },
  {
    id: 'disease',
    icon: '🔍',
    title: 'Disease Check',
    description: 'Scan a leaf to check for blister blight, red rust, or other diseases',
    color: '#f44336',
    gradient: 'linear-gradient(135deg, #C62828, #f44336)',
  },
  {
    id: 'yield',
    icon: '📊',
    title: 'Yield Forecast and Digitization',
    description: 'See predicted tea yield for your fields next month and yield book digitize',
    color: '#9C27B0',
    gradient: 'linear-gradient(135deg, #6A1B9A, #9C27B0)',
  },
  {
    id: 'smart-auction-simulation',
    icon: '💹',
    title: 'Market & Auction Strategy',
    description: 'Simulate auctions and forecast tea prices to maximize your profit',
    color: '#2196F3',
    gradient: 'linear-gradient(135deg, #1976D2, #2196F3)',
  },
]

const OBJECTIVES = [
  {
    num: 1,
    student: 'IT22154576',
    title: 'Tea Freshness Grading & Classification',
    desc: 'Automated quality assessment using computer vision and ML',
    pages: ['detection', 'grading', 'knowledge'],
    labels: ['Inspect Leaves', 'Grade Quality', 'Tea Handbook'],
    color: '#4CAF50',
    stats: [
      { label: 'ML Accuracy', value: '96.36%' },
      { label: 'YOLO Classes', value: '7' },
      { label: 'Knowledge Docs', value: '156' },
    ],
  },
  {
    num: 2,
    student: 'IT22222268',
    title: 'Tea Yield Forecasting & Digitization',
    desc: 'Logbook OCR and monthly yield forecasting',
    pages: ['yield', 'ocr'],
    labels: ['Yield Forecast', 'Digitize Logbook'],
    color: '#9C27B0',
    stats: [
      { label: 'SARIMAX Models', value: '44' },
      { label: 'Fields Covered', value: '3 Divisions' },
      { label: 'OCR Method', value: 'PaddleOCR' },
    ],
  },
  {
    num: 3,
    student: 'IT22247018',
    title: 'Market Demand Forecasting',
    desc: 'Smart auction planning and price prediction',
    pages: ['smart-auction-simulation', 'tea-price-forecast'],
    labels: ['Auction Simulation', 'Price Forecasting'],
    color: '#2196F3',
    stats: [
      { label: 'Data Rows', value: '1.5M+' },
      { label: 'Period', value: '2023-2025' },
      { label: 'Method', value: 'Ensemble ML' },
    ],
  },
  {
    num: 4,
    student: 'IT22142146',
    title: 'Disease, Pest & Invasive Detection',
    desc: 'AI disease identification with treatment guidance',
    pages: ['disease', 'invasive', 'seasonal', 'treatment', 'chat'],
    labels: ['Disease Check', 'Identify Weeds', 'Season Risk', 'Treatment', 'AI Chat'],
    color: '#FF5722',
    stats: [
      { label: 'Disease Classes', value: '6' },
      { label: 'Invasive Species', value: '2' },
      { label: 'Images', value: '7,500+' },
    ],
  },
]

function DashboardPage({ onNavigate }) {
  const [currentTip, setCurrentTip] = useState(0)

  const tips = [
    '💡 Pluck only "two leaves and a bud" for the highest quality tea.',
    '🌧️ High humidity increases Blister Blight risk  spray early!',
    '📏 Maintain 2-3 foot spacing between bushes for air circulation.',
    '🍃 Fresh buds appear bright green  brown edges mean lower quality.',
    '🌡️ Best picking time is early morning when leaves have peak moisture.',
  ]

  useEffect(() => {
    const tipInterval = setInterval(() => {
      setCurrentTip((prev) => (prev + 1) % tips.length)
    }, 5000)
    return () => clearInterval(tipInterval)
  }, [])

  return (
    <div className="dashboard-page">
      {/* Hero Section */}
      <div className="dash-hero">
        <div className="dash-hero-content">
          <h1>🍃 TeaVision</h1>
          <p className="dash-hero-sub">
            Your smart assistant for tea estate management-powered by AI
          </p>
        </div>
        <div className="dash-tip-banner">
          <span className="dash-tip-icon">💡</span>
          <span className="dash-tip-text">{tips[currentTip]}</span>
        </div>
      </div>



      {/* Quick Actions */}
      <h2 className="dash-section-title">⚡ Quick Actions</h2>
      <div className="dash-quick-grid">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.id}
            className="dash-action-card"
            style={{ background: action.gradient }}
            onClick={() => onNavigate(action.id)}
          >
            <span className="dash-action-icon">{action.icon}</span>
            <h3>{action.title}</h3>
            <p>{action.description}</p>
            <span className="dash-action-arrow">→</span>
          </button>
        ))}
      </div>

      {/* Research Objectives */}
      <h2 className="dash-section-title">🎯 Research Objectives</h2>
      <div className="dash-objectives-grid">
        {OBJECTIVES.map((obj) => (
          <div key={obj.num} className="dash-objective-card" style={{ borderLeftColor: obj.color }}>
            <div className="dash-obj-header">
              <span className="dash-obj-num" style={{ background: obj.color }}>Obj {obj.num}</span>
              <span className="dash-obj-student">{obj.student}</span>
            </div>
            <h3>{obj.title}</h3>
            <p className="dash-obj-desc">{obj.desc}</p>
            {obj.pages.length > 0 && (
              <div className="dash-obj-links">
                {obj.pages.map((page, i) => (
                  <button
                    key={page}
                    className="dash-obj-link"
                    style={{ color: obj.color, borderColor: obj.color }}
                    onClick={() => onNavigate(page)}
                  >
                    {obj.labels[i]} →
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default DashboardPage
