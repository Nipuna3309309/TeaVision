import { useState, useEffect, useRef, useCallback } from 'react'
import './KnowledgePage.css'

const API_BASE = 'http://localhost:8000'

function KnowledgePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState([])
  const [documents, setDocuments] = useState([])
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('search')
  const [searchMethod, setSearchMethod] = useState('hybrid')

  // Voice search state
  const [isListening, setIsListening] = useState(false)
  const [voiceSupported, setVoiceSupported] = useState(false)
  const [voiceTranscript, setVoiceTranscript] = useState('')
  const recognitionRef = useRef(null)

  // Auto-scrape state
  const [scrapeStatus, setScrapeStatus] = useState(null)
  const [isScraping, setIsScraping] = useState(false)
  const scrapeIntervalRef = useRef(null)

  // AI Answer state
  const [aiAnswer, setAiAnswer] = useState(null)
  const [aiLoading, setAiLoading] = useState(false)

  // Feedback state
  const [feedbackGiven, setFeedbackGiven] = useState({})

  // Initialize voice recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      setVoiceSupported(true)
      const recognition = new SpeechRecognition()
      recognition.continuous = false
      recognition.interimResults = true
      recognition.lang = 'en-US'
      recognition.maxAlternatives = 1

      recognition.onresult = (event) => {
        let interimTranscript = ''
        let finalTranscript = ''

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += transcript
          } else {
            interimTranscript += transcript
          }
        }

        if (finalTranscript) {
          setSearchQuery(finalTranscript)
          setVoiceTranscript(finalTranscript)
          setIsListening(false)
          // Auto-submit search after voice input
          setTimeout(() => {
            doSearch(finalTranscript)
          }, 300)
        } else if (interimTranscript) {
          setVoiceTranscript(interimTranscript)
        }
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        setIsListening(false)
        if (event.error === 'not-allowed') {
          alert('Microphone access denied. Please allow microphone access in your browser settings.')
        }
      }

      recognitionRef.current = recognition
    }

    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop() } catch (e) {}
      }
      if (scrapeIntervalRef.current) {
        clearInterval(scrapeIntervalRef.current)
      }
    }
  }, [])

  useEffect(() => {
    fetchCategories()
    fetchStats()
    fetchDocuments()
  }, [])

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API_BASE}/categories`)
      const data = await res.json()
      setCategories(data)
    } catch (err) {
      console.error('Failed to fetch categories:', err)
    }
  }

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`)
      const data = await res.json()
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const fetchDocuments = async (category = '') => {
    setLoading(true)
    try {
      const url = category
        ? `${API_BASE}/documents?category=${category}&limit=50`
        : `${API_BASE}/documents?limit=50`
      const res = await fetch(url)
      const data = await res.json()
      setDocuments(data)
    } catch (err) {
      console.error('Failed to fetch documents:', err)
    }
    setLoading(false)
  }

  // Fetch AI-generated answer
  const fetchAiAnswer = async (query) => {
    setAiLoading(true)
    try {
      const res = await fetch(
        `${API_BASE}/generate-answer?q=${encodeURIComponent(query)}&method=${searchMethod}`
      )
      const data = await res.json()
      setAiAnswer(data)
    } catch (err) {
      console.error('AI answer failed:', err)
      setAiAnswer(null)
    }
    setAiLoading(false)
  }

  const doSearch = useCallback(async (query) => {
    if (!query || !query.trim()) return

    setLoading(true)
    setActiveTab('search')
    setAiAnswer(null)
    setFeedbackGiven({})
    try {
      const res = await fetch(
        `${API_BASE}/search?q=${encodeURIComponent(query)}&method=${searchMethod}&top_k=10`
      )
      const data = await res.json()
      setResults(data.results || [])
      // Also fetch AI answer
      fetchAiAnswer(query)
    } catch (err) {
      console.error('Search failed:', err)
      setResults([])
    }
    setLoading(false)
  }, [searchMethod])

  const handleSearch = async (e) => {
    e.preventDefault()
    doSearch(searchQuery)
  }

  const toggleVoice = () => {
    if (!recognitionRef.current) return

    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      setVoiceTranscript('')
      setIsListening(true)
      try {
        recognitionRef.current.start()
      } catch (e) {
        // Already started
        setIsListening(false)
      }
    }
  }

  // Feedback handler
  const sendFeedback = async (docId, title, type) => {
    try {
      await fetch(`${API_BASE}/search-feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          doc_id: docId,
          title: title,
          feedback: type,
        }),
      })
      setFeedbackGiven(prev => ({ ...prev, [docId]: type }))
    } catch (err) {
      console.error('Feedback failed:', err)
    }
  }

  // Highlight search terms in text
  const highlightText = (text, query) => {
    if (!query || !query.trim()) return text
    const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2)
    if (terms.length === 0) return text

    const regex = new RegExp(`(${terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi')
    const parts = text.split(regex)

    return parts.map((part, i) => {
      if (terms.some(t => part.toLowerCase() === t.toLowerCase())) {
        return <mark key={i} className="kp-highlight">{part}</mark>
      }
      return part
    })
  }

  // Auto-scrape functions
  const startScraping = async () => {
    try {
      setIsScraping(true)
      const res = await fetch(`${API_BASE}/scrape-and-update`, { method: 'POST' })
      const data = await res.json()

      if (data.status === 'already_running') {
        setScrapeStatus(data.progress)
      } else {
        setScrapeStatus({ phase: 'starting', progress: 0, message: 'Starting...' })
      }

      // Poll for status
      scrapeIntervalRef.current = setInterval(async () => {
        try {
          const statusRes = await fetch(`${API_BASE}/scrape-status`)
          const statusData = await statusRes.json()
          setScrapeStatus(statusData)

          if (statusData.completed || statusData.phase === 'error') {
            clearInterval(scrapeIntervalRef.current)
            setIsScraping(false)
            // Refresh stats and documents
            if (statusData.phase === 'done') {
              fetchStats()
              fetchDocuments(selectedCategory)
              fetchCategories()
            }
          }
        } catch (e) {
          console.error('Status poll failed:', e)
        }
      }, 2000)
    } catch (err) {
      console.error('Scrape failed:', err)
      setIsScraping(false)
    }
  }

  const handleCategorySelect = (category) => {
    setSelectedCategory(category)
    setActiveTab('browse')
    fetchDocuments(category)
  }

  const getCategoryColor = (category) => {
    const colors = {
      cultivar: '#4CAF50',
      region: '#2196F3',
      grade: '#FF9800',
      processing: '#9C27B0',
      health: '#E91E63',
      plucking: '#00BCD4',
      disease: '#F44336',
      ai_grading: '#3F51B5',
      quality: '#009688',
      economics: '#FF5722',
      sustainability: '#8BC34A',
      history: '#795548',
      trade: '#607D8B'
    }
    return colors[category] || '#757575'
  }

  const getCategoryIcon = (category) => {
    const icons = {
      cultivar: '🌱',
      region: '🗺️',
      grade: '⭐',
      processing: '⚙️',
      health: '💚',
      plucking: '✋',
      disease: '🦠',
      ai_grading: '🤖',
      quality: '🏆',
      economics: '💰',
      sustainability: '♻️',
      history: '📜',
      trade: '🌍'
    }
    return icons[category] || '📄'
  }

  const getScoreBar = (score, maxScore = 10) => {
    const pct = Math.min((score / maxScore) * 100, 100)
    return (
      <div className="kp-score-bar">
        <div className="kp-score-fill" style={{ width: `${pct}%` }} />
        <span className="kp-score-label">{score.toFixed(1)}</span>
      </div>
    )
  }

  return (
    <div className="knowledge-page">
      <div className="kp-header">
        <h1>Ceylon Tea Knowledge</h1>
        <p>AI-Powered Knowledge Retrieval with Voice Search & Auto-Scraping</p>
      </div>

      {/* Search Section */}
      <div className="kp-search-section">
        <form onSubmit={handleSearch} className="kp-search-form">
          <div className="kp-search-input-wrapper">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={isListening ? "Listening... speak now" : "Search tea knowledge... (e.g., 'TRI 2025', 'health benefits')"}
              className={`kp-search-input ${isListening ? 'listening' : ''}`}
            />
            {isListening && voiceTranscript && (
              <div className="kp-voice-preview">{voiceTranscript}</div>
            )}
          </div>

          {voiceSupported && (
            <button
              type="button"
              className={`kp-voice-btn ${isListening ? 'active' : ''}`}
              onClick={toggleVoice}
              title={isListening ? 'Stop listening' : 'Voice search'}
            >
              <span className="kp-mic-icon">
                {isListening ? (
                  <>
                    <span className="kp-pulse-ring" />
                    <span className="kp-pulse-ring delay" />
                    MIC
                  </>
                ) : 'MIC'}
              </span>
            </button>
          )}

          <button type="submit" className="kp-search-button" disabled={loading}>
            {loading ? 'Loading...' : 'Search'}
          </button>
        </form>

        {/* Search Method Toggle */}
        <div className="kp-method-toggle">
          <span className="kp-method-label">Search Mode:</span>
          {['keyword', 'semantic', 'hybrid'].map(method => (
            <button
              key={method}
              className={`kp-method-btn ${searchMethod === method ? 'active' : ''}`}
              onClick={() => setSearchMethod(method)}
            >
              {method === 'keyword' && 'ABC'}
              {method === 'semantic' && 'AI'}
              {method === 'hybrid' && 'HYB'}
              {' '}{method.charAt(0).toUpperCase() + method.slice(1)}
            </button>
          ))}
          {stats && stats.semantic_search_ready && (
            <span className="kp-semantic-badge">Semantic Ready</span>
          )}
          {stats && !stats.semantic_search_ready && searchMethod !== 'keyword' && (
            <span className="kp-semantic-badge warning">Loading models...</span>
          )}
        </div>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="kp-stats-bar">
          <span>{stats.total_documents} Documents</span>
          <span>{stats.total_chunks} Chunks</span>
          <span>{stats.total_categories} Categories</span>
          {stats.faiss_vectors > 0 && (
            <span>{stats.faiss_vectors} Vectors</span>
          )}
        </div>
      )}

      {/* Auto-Scrape Panel */}
      <div className="kp-scrape-panel">
        <div className="kp-scrape-header">
          <div className="kp-scrape-title">
            <span>Auto-Update Knowledge Base</span>
            <small>Automatically fetch tea content from Wikipedia & web sources</small>
          </div>
          <button
            className={`kp-scrape-btn ${isScraping ? 'running' : ''}`}
            onClick={startScraping}
            disabled={isScraping}
          >
            {isScraping ? 'Scraping...' : 'Fetch New Content'}
          </button>
        </div>

        {scrapeStatus && (
          <div className="kp-scrape-status">
            <div className="kp-progress-bar">
              <div
                className="kp-progress-fill"
                style={{ width: `${scrapeStatus.progress || 0}%` }}
              />
            </div>
            <div className="kp-scrape-info">
              <span className="kp-scrape-phase">
                {scrapeStatus.phase === 'done' && 'DONE'}
                {scrapeStatus.phase === 'error' && 'ERROR'}
                {scrapeStatus.phase !== 'done' && scrapeStatus.phase !== 'error' && 'WORKING'}
                {' '}{scrapeStatus.message || scrapeStatus.phase}
              </span>
              {scrapeStatus.new_documents > 0 && (
                <span className="kp-scrape-count">
                  +{scrapeStatus.new_documents} new docs (Total: {scrapeStatus.total_documents})
                </span>
              )}
            </div>
            {scrapeStatus.error && (
              <div className="kp-scrape-error">Error: {scrapeStatus.error}</div>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="kp-tabs">
        <button
          className={`kp-tab ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          Search Results
        </button>
        <button
          className={`kp-tab ${activeTab === 'browse' ? 'active' : ''}`}
          onClick={() => { setActiveTab('browse'); fetchDocuments(selectedCategory); }}
        >
          Browse Documents
        </button>
        <button
          className={`kp-tab ${activeTab === 'categories' ? 'active' : ''}`}
          onClick={() => setActiveTab('categories')}
        >
          Categories
        </button>
      </div>

      {/* Content Area */}
      <div className="kp-content-area">
        {activeTab === 'search' && (
          <div className="kp-results-section">
            {loading ? (
              <div className="kp-loading">
                <div className="kp-loading-spinner" />
                <p>Searching with {searchMethod} retrieval...</p>
              </div>
            ) : results.length > 0 ? (
              <>
                {/* AI-Generated Answer Section */}
                <div className="kp-ai-answer-section">
                  {aiLoading ? (
                    <div className="kp-ai-loading">
                      <div className="kp-ai-loading-dots">
                        <span /><span /><span />
                      </div>
                      <p>Generating AI answer...</p>
                    </div>
                  ) : aiAnswer ? (
                    <div className="kp-ai-answer-card">
                      <div className="kp-ai-answer-header">
                        <span className="kp-ai-badge">AI Answer</span>
                        <span className="kp-ai-confidence">
                          Confidence: {Math.round((aiAnswer.confidence || 0) * 100)}%
                        </span>
                      </div>
                      <p className="kp-ai-answer-text">{aiAnswer.answer}</p>
                      {aiAnswer.treatment && (
                        <div className="kp-ai-treatment">
                          <strong>Treatment for {aiAnswer.treatment.disease}:</strong>
                          <ul>
                            {aiAnswer.treatment.organic.map((t, i) => (
                              <li key={i} className="treatment-organic">{t}</li>
                            ))}
                            {aiAnswer.treatment.chemical.map((t, i) => (
                              <li key={`c${i}`} className="treatment-chemical">{t}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div className="kp-ai-sources">
                        <span>Sources:</span>
                        {aiAnswer.sources?.map((s, i) => (
                          <span key={i} className="kp-ai-source-tag">
                            {s.title} ({s.score?.toFixed(1)})
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>

                <h2>Found {results.length} results for "{searchQuery}" <small>({searchMethod} search)</small></h2>
                <div className="kp-results-grid">
                  {results.map((result, idx) => (
                    <div
                      key={idx}
                      className="kp-result-card"
                      onClick={() => setSelectedDocument(result)}
                    >
                      <div className="kp-result-header">
                        <span
                          className="kp-category-badge"
                          style={{ backgroundColor: getCategoryColor(result.category) }}
                        >
                          {getCategoryIcon(result.category)} {result.category}
                        </span>
                        {getScoreBar(result.score)}
                      </div>
                      <h3>{highlightText(result.title, searchQuery)}</h3>
                      <p className="kp-content-preview">
                        {highlightText(result.content, searchQuery)}
                      </p>
                      <div className="kp-result-footer">
                        <div className="kp-tags">
                          {result.tags.slice(0, 4).map((tag, i) => (
                            <span key={i} className="kp-tag">{tag}</span>
                          ))}
                        </div>
                        <div className="kp-feedback-buttons">
                          <button
                            className={`kp-feedback-btn up ${feedbackGiven[result.doc_id] === 'up' ? 'active' : ''}`}
                            onClick={(e) => {
                              e.stopPropagation()
                              sendFeedback(result.doc_id, result.title, 'up')
                            }}
                            disabled={!!feedbackGiven[result.doc_id]}
                            title="Helpful"
                          >
                            +
                          </button>
                          <button
                            className={`kp-feedback-btn down ${feedbackGiven[result.doc_id] === 'down' ? 'active' : ''}`}
                            onClick={(e) => {
                              e.stopPropagation()
                              sendFeedback(result.doc_id, result.title, 'down')
                            }}
                            disabled={!!feedbackGiven[result.doc_id]}
                            title="Not helpful"
                          >
                            -
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : searchQuery ? (
              <div className="kp-no-results">
                <p>No results found for "{searchQuery}"</p>
                <p>Try different keywords, switch search mode, or browse by category</p>
              </div>
            ) : (
              <div className="kp-welcome-message">
                <h2>Welcome to Ceylon Tea Knowledge Base</h2>
                <p>Search for information about Sri Lankan tea cultivars, regions, grades, processing methods, and more.</p>
                <p><strong>Try voice search!</strong> Click the MIC button and speak your query.</p>
                <div className="kp-quick-searches">
                  <h3>Quick Searches:</h3>
                  <div className="kp-quick-buttons">
                    {['TRI 2025', 'Nuwara Eliya', 'health benefits', 'black tea', 'blister blight', 'tea grading'].map(term => (
                      <button
                        key={term}
                        className="kp-quick-search-btn"
                        onClick={() => { setSearchQuery(term); doSearch(term); }}
                      >
                        {term}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'browse' && (
          <div className="kp-browse-section">
            <div className="kp-category-filter">
              <button
                className={`kp-filter-btn ${selectedCategory === '' ? 'active' : ''}`}
                onClick={() => handleCategorySelect('')}
              >
                All
              </button>
              {categories.map(cat => (
                <button
                  key={cat.category}
                  className={`kp-filter-btn ${selectedCategory === cat.category ? 'active' : ''}`}
                  onClick={() => handleCategorySelect(cat.category)}
                  style={{
                    borderColor: getCategoryColor(cat.category),
                    backgroundColor: selectedCategory === cat.category ? getCategoryColor(cat.category) : 'transparent'
                  }}
                >
                  {getCategoryIcon(cat.category)} {cat.category} ({cat.count})
                </button>
              ))}
            </div>

            {loading ? (
              <div className="kp-loading">Loading documents...</div>
            ) : (
              <div className="kp-documents-grid">
                {documents.map((doc, idx) => (
                  <div
                    key={idx}
                    className="kp-document-card"
                    onClick={() => setSelectedDocument(doc)}
                  >
                    <div className="kp-doc-header">
                      <span
                        className="kp-category-badge"
                        style={{ backgroundColor: getCategoryColor(doc.category) }}
                      >
                        {getCategoryIcon(doc.category)} {doc.category}
                      </span>
                    </div>
                    <h3>{doc.title}</h3>
                    <p className="kp-content-preview">
                      {doc.content.substring(0, 200)}...
                    </p>
                    <div className="kp-tags">
                      {doc.tags.slice(0, 3).map((tag, i) => (
                        <span key={i} className="kp-tag">{tag}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'categories' && (
          <div className="kp-categories-section">
            <h2>Knowledge Categories</h2>
            <div className="kp-categories-grid">
              {categories.map(cat => (
                <div
                  key={cat.category}
                  className="kp-category-card"
                  style={{ borderLeftColor: getCategoryColor(cat.category) }}
                  onClick={() => handleCategorySelect(cat.category)}
                >
                  <div className="kp-category-header">
                    <span className="kp-category-icon">{getCategoryIcon(cat.category)}</span>
                    <h3>{cat.category}</h3>
                    <span className="kp-count">{cat.count} docs</span>
                  </div>
                  <ul className="kp-doc-list">
                    {cat.documents.slice(0, 3).map((title, i) => (
                      <li key={i}>{title}</li>
                    ))}
                    {cat.documents.length > 3 && (
                      <li className="kp-more">+{cat.documents.length - 3} more...</li>
                    )}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Document Modal */}
      {selectedDocument && (
        <div className="kp-modal-overlay" onClick={() => setSelectedDocument(null)}>
          <div className="kp-modal" onClick={(e) => e.stopPropagation()}>
            <button className="kp-close-btn" onClick={() => setSelectedDocument(null)}>x</button>
            <div className="kp-modal-header">
              <span
                className="kp-category-badge large"
                style={{ backgroundColor: getCategoryColor(selectedDocument.category) }}
              >
                {getCategoryIcon(selectedDocument.category)} {selectedDocument.category}
              </span>
            </div>
            <h2>{selectedDocument.title}</h2>
            <div className="kp-modal-content">
              <p>{selectedDocument.content}</p>
            </div>
            <div className="kp-modal-tags">
              {selectedDocument.tags.map((tag, i) => (
                <span key={i} className="kp-tag">{tag}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default KnowledgePage
