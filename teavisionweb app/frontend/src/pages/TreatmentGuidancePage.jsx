import React, { useState } from "react";
import axios from "axios";
import "./TreatmentGuidancePage.css";

function TreatmentGuidancePage() {
  const [formData, setFormData] = useState({
    disease: "Blister Blight",
    spot_color: "None",
    severity: "Low",
    spread_rate: "Slow",
    weather: "Dry",
    leaf_stage: "Young",
    preferred_method: "Organic"
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const getRecommendation = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(
        "http://localhost:8000/recommend-treatment",
        formData
      );
      setResult(response.data);
    } catch (err) {
      console.error(err);
      setError("Failed to get recommendation. Please check if the backend is running.");
    }
    setLoading(false);
  };

  return (
    <div className="tgp-container">
      <div className="tgp-header">
        <h1>🍃 Tea Leaf Treatment Guidance System</h1>
        <p>Rule-Based Expert System for Tea Disease Management</p>
      </div>

      <div className="tgp-main-grid">
        {/* Left Column: Form */}
        <div className="tgp-form-card">
          <h2 className="tgp-section-title">🧪 Disease & Field Information</h2>
          
          <div className="tgp-form-group">
            <label>Detected Disease</label>
            <select name="disease" value={formData.disease} onChange={handleChange}>
              <option>Blister Blight</option>
              <option>Red Rust</option>
              <option>Brown Blight</option>
              <option>Shot Hole Borer</option>
              <option>Healthy</option>
            </select>
          </div>

          <div className="tgp-form-group">
            <label>Spot Color</label>
            <select name="spot_color" value={formData.spot_color} onChange={handleChange}>
              <option>None</option>
              <option>Grey</option>
              <option>White</option>
              <option>Orange</option>
              <option>Reddish</option>
              <option>Dark Brown</option>
              <option>Brown</option>
              <option>Black</option>
            </select>
          </div>

          <div className="tgp-form-group">
            <label>Severity Level</label>
            <select name="severity" value={formData.severity} onChange={handleChange}>
              <option>Low</option>
              <option>Moderate</option>
              <option>High</option>
            </select>
          </div>

          <div className="tgp-form-group">
            <label>Spread Rate</label>
            <select name="spread_rate" value={formData.spread_rate} onChange={handleChange}>
              <option>Slow</option>
              <option>Moderate</option>
              <option>Fast</option>
            </select>
          </div>

          <div className="tgp-form-group">
            <label>Weather Conditions</label>
            <select name="weather" value={formData.weather} onChange={handleChange}>
              <option>Dry</option>
              <option>Moderate</option>
              <option>Wet</option>
            </select>
          </div>

          <div className="tgp-form-group">
            <label>Leaf Stage</label>
            <select name="leaf_stage" value={formData.leaf_stage} onChange={handleChange}>
              <option>Young</option>
              <option>Mature</option>
              <option>Old</option>
            </select>
          </div>

          <div className="tgp-form-group">
            <label>Preferred Treatment Method</label>
            <select name="preferred_method" value={formData.preferred_method} onChange={handleChange}>
              <option>Organic</option>
              <option>Manual</option>
              <option>Chemical</option>
            </select>
          </div>

          <button className="tgp-submit-btn" onClick={getRecommendation} disabled={loading}>
            {loading ? "Processing..." : "🌱 Get Treatment Recommendation"}
          </button>
          
          {error && <div className="tgp-error-msg">{error}</div>}
        </div>

        {/* Right Column: Results */}
        <div className="tgp-result-area">
          <h2 className="tgp-section-title">💊 Treatment Recommendation</h2>
          
          {!result && !loading && (
            <div className="tgp-empty-state">
              <p>Please select all required inputs and click Get Treatment Recommendation.</p>
            </div>
          )}

          {result && (
            <div className="tgp-result-content">
              <div className="tgp-summary-box">
                <p>{result.summary}</p>
              </div>

              <div className="tgp-treatment-categories">
                <div className="tgp-cat-card organic">
                  <div className="tgp-cat-header">
                    <span className="tgp-cat-icon">🌿</span>
                    <h3>Organic Treatments</h3>
                  </div>
                  <ul>
                    {result.organic.map((item, idx) => <li key={idx}>{item}</li>)}
                  </ul>
                </div>

                <div className="tgp-cat-card manual">
                  <div className="tgp-cat-header">
                    <span className="tgp-cat-icon">🧤</span>
                    <h3>Manual & Cultural</h3>
                  </div>
                  <ul>
                    {result.manual.map((item, idx) => <li key={idx}>{item}</li>)}
                  </ul>
                </div>

                <div className="tgp-cat-card chemical">
                  <div className="tgp-cat-header">
                    <span className="tgp-cat-icon">🧪</span>
                    <h3>Chemical Solutions</h3>
                  </div>
                  <ul>
                    {result.chemical.map((item, idx) => <li key={idx}>{item}</li>)}
                  </ul>
                </div>

              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TreatmentGuidancePage;