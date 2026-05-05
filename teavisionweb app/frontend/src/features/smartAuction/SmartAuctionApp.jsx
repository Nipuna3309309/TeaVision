import { useEffect, useState } from 'react'
import api from './api/client'

import './styles/index.css'
import './styles/App.css'

import InputPanel from './components/InputPanel'
import SummaryCards from './components/SummaryCards'
import AuctionResultCard from './components/AuctionResultCard'
import BuyerPanel from './components/BuyerPanel'
import FactoryPanel from './components/FactoryPanel'
import BrokerPanel from './components/BrokerPanel'
import LearningPanel from './components/LearningPanel'
import LoadingOverlay from './components/LoadingOverlay'
import TeaPriceTab from './components/TeaPriceTab'

import teaBg from './assets/tea-bg.png'

const MIN_SIMULATION_LOADER_MS = 2000

const initialForm = {
  lot_volume: 10000,
  elevation: 'Low',
  grade: '',
  use_current_price: false,
  current_price: 0,
  storage_cost: 5,
  demand: 'Medium',
  competition: 'Medium',
  use_production_cost: false,
  production_cost: 0,
  year: 2026,
  month: 1,
  week_in_month: 1,
  buyer_online_steps: 400,
  factory_online_steps: 0,
  broker_online_steps: 0,
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export default function SmartAuctionApp({ initialTab = 'mas' }) {
  const [activeTab, setActiveTab] = useState(initialTab)

  const [form, setForm] = useState(initialForm)
  const [grades, setGrades] = useState([])
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [learning, setLearning] = useState(false)
  const [error, setError] = useState('')
  const [learnMessage, setLearnMessage] = useState('')
  const [showGuide, setShowGuide] = useState(false)

  useEffect(() => {
    fetchGrades(form.elevation)
  }, [form.elevation])

  useEffect(() => {
    setActiveTab(initialTab)
  }, [initialTab])

  async function fetchGrades(elevation) {
    try {
      setError('')
      const res = await api.get(`/grades/${elevation}`)
      const gradeList = res.data?.grades || []
      setGrades(gradeList)

      setForm((prev) => ({
        ...prev,
        grade: gradeList.includes(prev.grade) ? prev.grade : gradeList[0] || '',
      }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load grades')
    }
  }

  async function handleRun() {
    try {
      setRunning(true)
      setError('')
      setLearnMessage('')

      const requestPromise = api.post('/simulate', form)
      const timerPromise = sleep(MIN_SIMULATION_LOADER_MS)

      const [res] = await Promise.all([requestPromise, timerPromise])
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Simulation failed')
    } finally {
      setRunning(false)
    }
  }

  async function handleLearn() {
    try {
      setLearning(true)
      setError('')
      setLearnMessage('')

      const res = await api.post('/learn', form)
      setLearnMessage(
        res.data?.message || 'Online learning completed successfully.'
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'Learning failed')
    } finally {
      setLearning(false)
    }
  }

  async function handleReload() {
    try {
      setError('')
      await api.post('/reload')
      await fetchGrades(form.elevation)
      setResult(null)
      setLearnMessage(
        'Models, grades, and price forecast resources reloaded successfully.'
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'Reload failed')
    }
  }

  return (
    <div className="smart-auction-root">
      <div className="sa-background" aria-hidden="true">
        <div className="sa-background-gradient" />
        <div className="sa-background-glow" />
        <img src={teaBg} alt="" className="sa-background-image" />
        <div className="sa-background-overlay" />
      </div>

      <LoadingOverlay
        show={running || learning}
        text={running ? 'Running simulation...' : 'Running online learning...'}
      />

      <div className="sa-page">
        <header className="sa-header panel-appear delay-0">
          <div className="sa-header-row">
            <div className="sa-header-copy">
              <h1 className="sa-title">
                Smart Auction Simulation &amp; Price Forecasting
              </h1>

              <p className="sa-subtitle">
                Simulate auction outcomes, compare agent decisions, and check
                future tea price trends before a sale.
              </p>
            </div>

            <div className="sa-header-actions">
              <button
                type="button"
                onClick={() => setShowGuide((prev) => !prev)}
                className="sa-guide-btn"
              >
                {showGuide ? 'Hide Guide' : 'How to Use'}
              </button>

              <button
                className={`tab-pill ${
                  activeTab === 'mas' ? 'tab-pill-active' : ''
                }`}
                onClick={() => setActiveTab('mas')}
              >
                MAS Auction Simulation
              </button>

              <button
                className={`tab-pill ${
                  activeTab === 'tea-price' ? 'tab-pill-active' : ''
                }`}
                onClick={() => setActiveTab('tea-price')}
              >
                Tea Price Forecast
              </button>
            </div>
          </div>

          {showGuide && (
            <div className="sa-guide-panel">
              <div className="sa-guide-grid">
                <div className="sa-guide-card">
                  <div className="sa-guide-step">Step 1</div>
                  <p className="sa-guide-text">
                    Select elevation, tea grade, lot volume, and market
                    conditions.
                  </p>
                </div>

                <div className="sa-guide-card">
                  <div className="sa-guide-step">Step 2</div>
                  <p className="sa-guide-text">
                    Run the auction simulation to see reserve price, bid, sold
                    volume, and agent decisions.
                  </p>
                </div>

                <div className="sa-guide-card">
                  <div className="sa-guide-step">Step 3</div>
                  <p className="sa-guide-text">
                    Review factory profit, broker profit, and buyer action
                    before making a selling decision.
                  </p>
                </div>

                <div className="sa-guide-card">
                  <div className="sa-guide-step">Step 4</div>
                  <p className="sa-guide-text">
                    Open Tea Price Forecast to check expected market range and
                    timing for the upcoming sale.
                  </p>
                </div>
              </div>
            </div>
          )}
        </header>

        {error && activeTab === 'mas' && (
          <div className="sa-error panel-appear delay-0">{error}</div>
        )}

        {activeTab === 'mas' ? (
          <div className="sa-main-grid">
            <div className="sa-sidebar-col panel-appear-left delay-1">
              <InputPanel
                form={form}
                setForm={setForm}
                grades={grades}
                onRun={handleRun}
                onLearn={handleLearn}
                onReload={handleReload}
                running={running}
                learning={learning}
              />
            </div>

            <div className="sa-content">
              <div className="panel-appear delay-2">
                <SummaryCards result={result} />
              </div>

              <div className="panel-appear delay-3">
                <LearningPanel learnMessage={learnMessage} />
              </div>

              <div className="panel-appear delay-3">
                <AuctionResultCard result={result} lotVolume={form.lot_volume} />
              </div>

              <div className="sa-agent-grid">
                <div className="panel-appear delay-4 sa-panel-stretch">
                  <BuyerPanel result={result} />
                </div>

                <div className="panel-appear delay-4 sa-panel-stretch">
                  <FactoryPanel result={result} />
                </div>

                <div className="panel-appear delay-5 sa-panel-stretch">
                  <BrokerPanel result={result} />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="panel-appear delay-1">
            <TeaPriceTab />
          </div>
        )}
      </div>
    </div>
  )
}