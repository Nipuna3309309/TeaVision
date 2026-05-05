import { useState } from 'react'
import './Sidebar.css'

const SECTIONS = [
  {
    group: 'Field Work',
    icon: '🍃',
    items: [
      { id: 'detection', icon: '🔬', label: 'Inspect My Leaves', desc: 'Scan & identify leaf types' },
      { id: 'grading', icon: '⭐', label: 'Grade My Tea', desc: 'Check freshness quality' },
      { id: 'disease', icon: '🔍', label: 'Check for Disease', desc: 'Identify leaf diseases' },
      { id: 'invasive', icon: '🌿', label: 'Identify Weeds', desc: 'Spot invasive species' },
    ],
  },
  {
    group: 'Guidance',
    icon: '💊',
    items: [
      { id: 'treatment', icon: '💊', label: 'What Should I Do?', desc: 'Treatment recommendations' },
      { id: 'seasonal', icon: '☁️', label: 'Season Risk Alert', desc: 'Outbreak prediction' },
      { id: 'chat', icon: '💬', label: 'Ask an Expert', desc: 'AI chat & voice' },
    ],
  },
  {
    group: 'My Estate Data',
    icon: '📊',
    items: [
      { id: 'yield', icon: '📈', label: 'Monthly Yield Forecast', desc: 'Monthly prediction' },
      { id: 'ocr', icon: '📝', label: 'Digitize Yield Logbook', desc: 'Scan handwritten records' },
      { id: 'knowledge', icon: '📖', label: 'Tea Handbook', desc: 'Search tea knowledge' },
    ],
  },
  {
    group: 'Market & Auction',
    icon: '💰',
    items: [
      { id: 'smart-auction-simulation', icon: '🤖', label: 'Auction Simulation', desc: 'MAS Decision System' },
      { id: 'tea-price-forecast', icon: '📈', label: 'Price Forecasting', desc: 'ARIMA Prediction' },
    ],
  },
]

const Sidebar = ({ activePage, onPageChange, onConnectPhone, user, onLogout }) => {
  const [collapsed, setCollapsed] = useState({})

  const toggleGroup = (group) => {
    setCollapsed((prev) => ({ ...prev, [group]: !prev[group] }))
  }

  return (
    <nav className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">🍃</span>
        <h2>TeaVision</h2>
        <p className="sidebar-subtitle">Smart Tea Estate Assistant</p>
      </div>

      <div className="sidebar-nav">
        {/* Dashboard */}
        <button
          className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
          onClick={() => onPageChange('dashboard')}
        >
          <span className="nav-icon">🏠</span>
          <div className="nav-text">
            <span className="nav-label">Home</span>
            <span className="nav-desc">Overview & Quick Actions</span>
          </div>
        </button>

        {/* Grouped Sections */}
        {SECTIONS.map((section) => (
          <div key={section.group} className="nav-section">
            <button
              className="nav-group-header"
              onClick={() => toggleGroup(section.group)}
            >
              <span className="nav-group-icon">{section.icon}</span>
              <span className="nav-group-label">{section.group}</span>
              <span className={`nav-group-arrow ${collapsed[section.group] ? 'collapsed' : ''}`}>
                ▾
              </span>
            </button>

            {!collapsed[section.group] && (
              <div className="nav-group-items">
                {section.items.map((item) => (
                  <button
                    key={item.id}
                    className={`nav-item nav-sub-item ${activePage === item.id ? 'active' : ''}`}
                    onClick={() => onPageChange(item.id)}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <div className="nav-text">
                      <span className="nav-label">{item.label}</span>
                      <span className="nav-desc">{item.desc}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        <div className="nav-section">
          <div className="nav-group-header nav-group-header-static">
            <span className="nav-group-icon">🛠️</span>
            <span className="nav-group-label">Tools</span>
          </div>
          <div className="nav-group-items">
            <button className="nav-item nav-sub-item nav-phone" onClick={onConnectPhone}>
              <span className="nav-icon">📱</span>
              <div className="nav-text">
                <span className="nav-label">Connect Phone</span>
                <span className="nav-desc">Scan QR to capture</span>
              </div>
            </button>
          </div>
        </div>
      </div>

      <div className="sidebar-footer">
        {user && (
          <div className="sidebar-user">
            <div className="sidebar-user-info">
              <span className="sidebar-user-icon">👤</span>
              <div>
                <p className="sidebar-user-name">{user.name}</p>
                <p className="sidebar-user-email">{user.email}</p>
              </div>
            </div>
            <button className="sidebar-logout-btn" onClick={onLogout}>
              Logout
            </button>
          </div>
        )}
        <div className="sidebar-team">
          <p>Project 25-26J-133 | SLIIT 2025</p>
        </div>
      </div>
    </nav>
  )
}

export default Sidebar
