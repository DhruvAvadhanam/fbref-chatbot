// src/App.tsx
import React, { useState } from 'react';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState<{ type: string; content: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Save the user's question to display immediately
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

      // Update the state with the bot's response, keeping previous messages
      setChatHistory(data.chat_history);

      // Clear the input field
      setQuestion('');

    } catch (error) {
      console.error('Error sending question:', error);
      alert('Server error. Check console.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: '2rem auto', padding: '1rem' }}>
      <h1>FBref Chatbot</h1>

      <div style={{ marginBottom: '1rem' }}>
        {chatHistory.map((msg, idx) => (
          <div key={idx} style={{ marginBottom: '0.5rem' }}>
            <strong>{msg.type === 'human' ? 'You' : 'Bot'}:</strong> {msg.content}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask something..."
          style={{ width: '80%', padding: '0.5rem' }}
        />
        <button type="submit" disabled={loading} style={{ padding: '0.5rem', marginLeft: '0.5rem' }}>
          {loading ? 'Asking...' : 'Ask'}
        </button>
      </form>
    </div>
  );
}

export default App;
