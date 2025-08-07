// src/App.tsx
import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState<{ type: string; content: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const chatWindowRef = useRef<HTMLDivElement>(null);

  // Scroll to the bottom of the chat window
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);

    const userMessage = { type: 'human', content: question };
    setChatHistory(prevHistory => [...prevHistory, userMessage]);

    try {
      const response = await fetch('http://127.0.0.1:5000/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        alert(errorData.error || 'Something went wrong.');
        return;
      }

      const data = await response.json();
      setChatHistory(data.chat_history);
      setQuestion('');

    } catch (error) {
      console.error('Error sending question:', error);
      alert('Server error. Check console.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>FBref Chatbot</h1>
      </div>
      <div className="chat-window" ref={chatWindowRef}>
        {chatHistory.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.type}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="loading-indicator">Thinking...</div>}
      </div>
      <form className="chat-input-area" onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about soccer data..."
        />
        <button type="submit" disabled={loading}>
          {loading ? '...' : 'Ask'}
        </button>
      </form>
    </div>
  );
}

export default App;