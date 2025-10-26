import React, { useState, useEffect } from 'react';
import logo from './logo.svg';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface ApiResponse {
  message: string;
}

interface ProduceResponse {
  status: string;
}

function App() {
  const [apiMessage, setApiMessage] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [messageText, setMessageText] = useState<string>('');
  const [produceStatus, setProduceStatus] = useState<string>('');

  // Fetch root endpoint on component mount
  useEffect(() => {
    fetchApiRoot();
  }, []);

  const fetchApiRoot = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: ApiResponse = await response.json();
      setApiMessage(data.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch from API');
    } finally {
      setLoading(false);
    }
  };

  const handleProduceMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    setProduceStatus('');
    setError('');

    try {
      const response = await fetch(`${API_URL}/produce`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: messageText }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ProduceResponse = await response.json();
      setProduceStatus(data.status);
      setMessageText('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <h1>FastAPI + React + Kafka</h1>

        {loading && <p>Loading...</p>}

        {apiMessage && (
          <div style={{ margin: '20px 0' }}>
            <h2>Backend Status:</h2>
            <p style={{ color: '#61dafb' }}>{apiMessage}</p>
          </div>
        )}

        {error && (
          <div style={{ color: '#ff6b6b', margin: '20px 0' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        <div style={{ margin: '30px 0', width: '400px' }}>
          <h3>Send Message to Kafka</h3>
          <form onSubmit={handleProduceMessage}>
            <input
              type="text"
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              placeholder="Enter message"
              style={{
                padding: '10px',
                fontSize: '16px',
                width: '100%',
                marginBottom: '10px',
                borderRadius: '4px',
                border: '1px solid #61dafb',
              }}
            />
            <button
              type="submit"
              style={{
                padding: '10px 20px',
                fontSize: '16px',
                backgroundColor: '#61dafb',
                color: '#282c34',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Send Message
            </button>
          </form>

          {produceStatus && (
            <p style={{ color: '#4caf50', marginTop: '10px' }}>{produceStatus}</p>
          )}
        </div>

        <button
          onClick={fetchApiRoot}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#282c34',
            color: '#61dafb',
            border: '2px solid #61dafb',
            borderRadius: '4px',
            cursor: 'pointer',
            marginTop: '20px',
          }}
        >
          Refresh Backend Status
        </button>
      </header>
    </div>
  );
}

export default App;
