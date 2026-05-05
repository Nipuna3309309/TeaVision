import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './ChatPage.css';

const API_BASE = 'http://localhost:8000';

function ChatPage() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am your Tea AI Assistant. How can I help you today with your plantation or tea leaf issues?',
      actions: [
        'What is Blister Blight?', 
        'How to treat Red Rust?', 
        'What causes Brown Blight?',
        'How do I identify Grey Blight?',
        'Is Helopeltis dangerous?',
        'Symptoms of Shot Hole Borer',
        'Organic treatment for fungi',
        'Best fertilizers for tea',
        'Managing soil drainage',
        'Check plantation status'
      ],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const chatEndRef = useRef(null);

  // Setup Speech Recognition
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = useRef(SpeechRecognition ? new SpeechRecognition() : null).current;

  if (recognition) {
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
  }

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const speak = (text) => {
    if (!window.speechSynthesis || isMuted) return;
    
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    utterance.pitch = 1;
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!recognition) return;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onresult = (event) => {
      const result = event.results[0][0].transcript;
      handleSend(result);
    };
    recognition.onerror = (event) => {
      console.error("STT Error:", event.error);
      setIsListening(false);
    };

    return () => {
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      recognition.stop();
    };
  }, [recognition]);

  const toggleListening = () => {
    if (!recognition) return;
    if (isListening) {
      recognition.stop();
    } else {
      stopSpeaking();
      recognition.start();
    }
  };

  const handleSend = async (text) => {
    const query = text || input;
    if (!query.trim() || loading) return;

    const userMsg = {
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    stopSpeaking();

    try {
      const response = await axios.post(`${API_BASE}/chat`, { message: query });
      const data = response.data;

      const aiMsg = {
        role: 'assistant',
        content: data.response,
        source: data.source,
        actions: data.actions,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, aiMsg]);
      
      // Speak the response if not muted
      const cleanSpeech = data.response.replace(/\[.*?\]/g, '').replace(/\*+/g, '');
      speak(cleanSpeech);
      
    } catch (err) {
      console.error(err);
      const errorMsg = 'Sorry, I am having trouble connecting to my knowledge base right now.';
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMsg,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
      speak(errorMsg);
    }
    setLoading(false);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-info">
          <span className="chat-bot-icon">🤖</span>
          <div>
            <h1>Tea AI Assistant</h1>
            <p>Powered by Treatment Recommendation Engine</p>
          </div>
        </div>
        <div className="chat-header-controls">
          <button 
            className={`mute-btn ${isMuted ? 'muted' : ''}`} 
            onClick={() => {
              const newMuted = !isMuted;
              setIsMuted(newMuted);
              if (newMuted) stopSpeaking();
            }}
            title={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? '🔇' : '🔊'}
          </button>
          <div className="chat-status">
            <span className="status-dot"></span> Online
          </div>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message-bubble-row ${msg.role}`}>
            <div className={`message-bubble ${msg.role}`}>
              <div className="message-header">
                <div className="message-content">{msg.content}</div>
                {msg.role === 'assistant' && !isMuted && isSpeaking && i === messages.length - 1 && (
                  <span className="speaking-indicator">🗣️</span>
                )}
              </div>
              
              {msg.source && (
                <div className="message-source">
                  <span>Source: {msg.source}</span>
                </div>
              )}

              {msg.actions && msg.actions.length > 0 && (
                <div className="message-actions">
                  {msg.actions.map((action, j) => (
                    <button 
                      key={j} 
                      className="chat-action-pill"
                      onClick={() => handleSend(action)}
                    >
                      {action}
                    </button>
                  ))}
                </div>
              )}
              
              <div className="message-time">{msg.timestamp}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="message-bubble-row assistant">
            <div className="message-bubble assistant typing">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="chat-input-wrap">
          <button 
            className={`chat-mic-btn ${isListening ? 'listening' : ''}`} 
            onClick={toggleListening}
            title={isListening ? "Stop listening" : "Ask by voice"}
          >
            {isListening ? '⏹️' : '🎤'}
          </button>
          <input
            type="text"
            placeholder={isListening ? "Listening..." : "Ask anything about tea diseases..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={isListening}
          />
          <button className="chat-send-btn" onClick={() => handleSend()} disabled={!input.trim() || loading || isListening}>
            {loading ? '...' : '✈️'}
          </button>
        </div>
        <p className="chat-disclaimer">Expert system providing general botanical guidance.</p>
      </div>
    </div>
  );
}

export default ChatPage;
