import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState([])
  const [documents, setDocuments] = useState([])
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('search')

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

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    setLoading(true)
    setActiveTab('search')
    try {
      const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(searchQuery)}&top_k=10`)
      const data = await res.json()
      setResults(data.results || [])
    } catch (err) {
      console.error('Search failed:', err)
      setResults([])
    }
    setLoading(false)
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

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-icon">🍃</span>
            <h1>Ceylon Tea Knowledge</h1>
          </div>
          <p className="subtitle">Sri Lankan Tea RAG System - AI-Powered Knowledge Retrieval</p>
        </div>
      </header>

      <main className="main">
        <div className="search-section">
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tea knowledge... (e.g., 'TRI 2025', 'Nuwara Eliya', 'health benefits')"
              className="search-input"
            />
            <button type="submit" className="search-button" disabled={loading}>
              {loading ? '...' : '🔍 Search'}
            </button>
          </form>
        </div>

        {stats && (
          <div className="stats-bar">
            <span>📚 {stats.total_documents} Documents</span>
            <span>📝 {stats.total_chunks} Chunks</span>
            <span>📁 {stats.total_categories} Categories</span>
          </div>
        )}

        <div className="tabs">
          <button
            className={`tab ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            🔍 Search Results
          </button>
          <button
            className={`tab ${activeTab === 'browse' ? 'active' : ''}`}
            onClick={() => { setActiveTab('browse'); fetchDocuments(selectedCategory); }}
          >
            📖 Browse Documents
          </button>
          <button
            className={`tab ${activeTab === 'categories' ? 'active' : ''}`}
            onClick={() => setActiveTab('categories')}
          >
            📁 Categories
          </button>
        </div>

        <div className="content-area">
          {activeTab === 'search' && (
            <div className="results-section">
              {loading ? (
                <div className="loading">Searching...</div>
              ) : results.length > 0 ? (
                <>
                  <h2>Found {results.length} results for "{searchQuery}"</h2>
                  <div className="results-grid">
                    {results.map((result, idx) => (
                      <div
                        key={idx}
                        className="result-card"
                        onClick={() => setSelectedDocument(result)}
                      >
                        <div className="result-header">
                          <span
                            className="category-badge"
                            style={{ backgroundColor: getCategoryColor(result.category) }}
                          >
                            {getCategoryIcon(result.category)} {result.category}
                          </span>
                          <span className="score">Score: {result.score.toFixed(1)}</span>
                        </div>
                        <h3>{result.title}</h3>
                        <p className="content-preview">{result.content}</p>
                        <div className="tags">
                          {result.tags.slice(0, 4).map((tag, i) => (
                            <span key={i} className="tag">{tag}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : searchQuery ? (
                <div className="no-results">
                  <p>No results found for "{searchQuery}"</p>
                  <p>Try different keywords or browse by category</p>
                </div>
              ) : (
                <div className="welcome-message">
                  <h2>Welcome to Ceylon Tea Knowledge Base</h2>
                  <p>Search for information about Sri Lankan tea cultivars, regions, grades, processing methods, and more.</p>
                  <div className="quick-searches">
                    <h3>Quick Searches:</h3>
                    <div className="quick-buttons">
                      {['TRI 2025', 'Nuwara Eliya', 'health benefits', 'black tea', 'blister blight'].map(term => (
                        <button
                          key={term}
                          className="quick-search-btn"
                          onClick={() => { setSearchQuery(term); }}
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
            <div className="browse-section">
              <div className="category-filter">
                <button
                  className={`filter-btn ${selectedCategory === '' ? 'active' : ''}`}
                  onClick={() => handleCategorySelect('')}
                >
                  All
                </button>
                {categories.map(cat => (
                  <button
                    key={cat.category}
                    className={`filter-btn ${selectedCategory === cat.category ? 'active' : ''}`}
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
                <div className="loading">Loading documents...</div>
              ) : (
                <div className="documents-grid">
                  {documents.map((doc, idx) => (
                    <div
                      key={idx}
                      className="document-card"
                      onClick={() => setSelectedDocument(doc)}
                    >
                      <div className="doc-header">
                        <span
                          className="category-badge"
                          style={{ backgroundColor: getCategoryColor(doc.category) }}
                        >
                          {getCategoryIcon(doc.category)} {doc.category}
                        </span>
                      </div>
                      <h3>{doc.title}</h3>
                      <p className="content-preview">
                        {doc.content.substring(0, 200)}...
                      </p>
                      <div className="tags">
                        {doc.tags.slice(0, 3).map((tag, i) => (
                          <span key={i} className="tag">{tag}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'categories' && (
            <div className="categories-section">
              <h2>Knowledge Categories</h2>
              <div className="categories-grid">
                {categories.map(cat => (
                  <div
                    key={cat.category}
                    className="category-card"
                    style={{ borderLeftColor: getCategoryColor(cat.category) }}
                    onClick={() => handleCategorySelect(cat.category)}
                  >
                    <div className="category-header">
                      <span className="category-icon">{getCategoryIcon(cat.category)}</span>
                      <h3>{cat.category}</h3>
                      <span className="count">{cat.count} docs</span>
                    </div>
                    <ul className="doc-list">
                      {cat.documents.slice(0, 3).map((title, i) => (
                        <li key={i}>{title}</li>
                      ))}
                      {cat.documents.length > 3 && (
                        <li className="more">+{cat.documents.length - 3} more...</li>
                      )}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {selectedDocument && (
          <div className="modal-overlay" onClick={() => setSelectedDocument(null)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <button className="close-btn" onClick={() => setSelectedDocument(null)}>×</button>
              <div className="modal-header">
                <span
                  className="category-badge large"
                  style={{ backgroundColor: getCategoryColor(selectedDocument.category) }}
                >
                  {getCategoryIcon(selectedDocument.category)} {selectedDocument.category}
                </span>
              </div>
              <h2>{selectedDocument.title}</h2>
              <div className="modal-content">
                <p>{selectedDocument.content}</p>
              </div>
              <div className="modal-tags">
                {selectedDocument.tags.map((tag, i) => (
                  <span key={i} className="tag">{tag}</span>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <p>Tea RAG System | Project 25-26J-133 | SLIIT</p>
        <p>Data Source: Tea Research Institute of Sri Lanka (TRI)</p>
      </footer>
    </div>
  )
}

export default App
