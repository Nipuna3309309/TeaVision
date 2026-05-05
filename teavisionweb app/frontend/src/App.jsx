import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import MobileConnect from './components/MobileConnect'
import DashboardPage from './pages/DashboardPage'
import DetectionPage from './pages/DetectionPage'
import GradingPage from './pages/GradingPage'
import KnowledgePage from './pages/KnowledgePage'
import MobileCapturePage from './pages/MobileCapturePage'
import YieldPredictionPage from './pages/YieldPredictionPage'
import LogbookOCRPage from './pages/LogbookOCRPage'
import DiseaseClassificationPage from './pages/DiseaseClassificationPage'
import InvasiveSpeciesPage from './pages/InvasiveSpeciesPage'
import SeasonalPredictionPage from './pages/SeasonalPredictionPage'
import TreatmentGuidancePage from './pages/TreatmentGuidancePage'
import ChatPage from './pages/ChatPage'
import SmartAuctionSimulationPage from './pages/SmartAuctionSimulationPage'
import TeaPriceForecastPage from './pages/TeaPriceForecastPage'
import AuthPage from './pages/AuthPage'
import './App.css'

function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [showMobileConnect, setShowMobileConnect] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [user, setUser] = useState(null)

  useEffect(() => {
    // Check if opened on mobile via QR code (#mobile in URL)
    if (window.location.hash === '#mobile') {
      setIsMobile(true)
    }

    // Check for existing auth token
    const token = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    if (token && savedUser) {
      setUser(JSON.parse(savedUser))
    }
  }, [])

  const handleLogin = (userData) => {
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  // If mobile mode, render the mobile capture page (no sidebar)
  if (isMobile) {
    return <MobileCapturePage />
  }

  // If not logged in, show auth page
  if (!user) {
    return <AuthPage onLogin={handleLogin} />
  }

  return (
    <div className="app-layout">
      <Sidebar
        activePage={activePage}
        onPageChange={setActivePage}
        onConnectPhone={() => setShowMobileConnect(true)}
        user={user}
        onLogout={handleLogout}
      />
      <main className="main-content">
        {activePage === 'dashboard' && <DashboardPage onNavigate={setActivePage} />}
        {activePage === 'detection' && <DetectionPage />}
        {activePage === 'grading' && <GradingPage />}
        {activePage === 'knowledge' && <KnowledgePage />}
        {activePage === 'yield' && <YieldPredictionPage />}
        {activePage === 'ocr' && <LogbookOCRPage />}
        {activePage === 'disease' && <DiseaseClassificationPage />}
        {activePage === 'invasive' && <InvasiveSpeciesPage />}
        {activePage === 'seasonal' && <SeasonalPredictionPage />}
        {activePage === 'treatment' && <TreatmentGuidancePage />}
        {activePage === 'chat' && <ChatPage />}
        {activePage === 'smart-auction-simulation' && <SmartAuctionSimulationPage />}
        {activePage === 'tea-price-forecast' && <TeaPriceForecastPage />}
      </main>

      {showMobileConnect && (
        <MobileConnect onClose={() => setShowMobileConnect(false)} />
      )}
    </div>
  )
}

export default App
