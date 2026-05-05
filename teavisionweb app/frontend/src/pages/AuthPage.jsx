import { useState } from 'react'
import './AuthPage.css'

const API_URL = 'http://localhost:8000'

const AuthPage = ({ onLogin }) => {
  const [isSignup, setIsSignup] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const endpoint = isSignup ? '/auth/signup' : '/auth/login'
    const body = isSignup ? { name, email, password } : { email, password }

    try {
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Something went wrong')
        setLoading(false)
        return
      }

      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
      onLogin(data.user)
    } catch (err) {
      setError('Cannot connect to server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <span className="auth-logo">🍃</span>
          <h1>TeaVision</h1>
          <p>Smart Tea Estate Assistant</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>{isSignup ? 'Create Account' : 'Welcome Back'}</h2>

          {isSignup && (
            <div className="auth-field">
              <label>Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your full name"
                required
              />
            </div>
          )}

          <div className="auth-field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <div className="auth-field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              minLength={6}
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? 'Please wait...' : isSignup ? 'Sign Up' : 'Log In'}
          </button>
        </form>

        <div className="auth-toggle">
          {isSignup ? (
            <p>Already have an account? <button onClick={() => { setIsSignup(false); setError('') }}>Log In</button></p>
          ) : (
            <p>Don't have an account? <button onClick={() => { setIsSignup(true); setError('') }}>Sign Up</button></p>
          )}
        </div>
      </div>
    </div>
  )
}

export default AuthPage
