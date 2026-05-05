import { useState, useRef, useEffect } from 'react'
import './ModelSelector.css'

const ModelSelector = ({ models, selectedModel, onSelect, label }) => {
  const [open, setOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selected = models.find(m => m.id === selectedModel) || models[0]

  return (
    <div className="model-selector" ref={dropdownRef}>
      <button className="ms-trigger" onClick={() => setOpen(!open)}>
        <div className="ms-trigger-left">
          <span className="ms-label">{label}</span>
          <span className="ms-selected-name">{selected?.name}</span>
        </div>
        <div className="ms-trigger-right">
          {selected?.tag && (
            <span className="ms-tag">{selected.tag}</span>
          )}
          <span className={`ms-arrow ${open ? 'open' : ''}`}>&#9662;</span>
        </div>
      </button>

      {open && (
        <div className="ms-dropdown">
          <div className="ms-dropdown-header">Select Model</div>
          {models.map((model) => (
            <button
              key={model.id}
              className={`ms-option ${model.id === selectedModel ? 'active' : ''} ${!model.available ? 'disabled' : ''}`}
              onClick={() => {
                if (model.available) {
                  onSelect(model.id)
                  setOpen(false)
                }
              }}
            >
              <div className="ms-option-left">
                <div className="ms-option-name">
                  {model.name}
                  {model.id === selectedModel && <span className="ms-check">&#10003;</span>}
                </div>
                <div className="ms-option-desc">{model.description}</div>
              </div>
              <div className="ms-option-right">
                {model.tag && <span className="ms-tag">{model.tag}</span>}
                {model.test_acc && (
                  <span className="ms-accuracy">{model.test_acc}%</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default ModelSelector
