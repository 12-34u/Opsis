import React, { useState } from 'react';
import { GoogleGenerativeAI } from '@google/generative-ai';
import './AIPanel.css';

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY || '';

const AIPanel = ({ code, isOpen, onClose }) => {
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeCode = async () => {
    if (!code || !code.trim()) {
      setError('No code to analyze. Write some code first.');
      return;
    }

    if (!GEMINI_API_KEY || GEMINI_API_KEY === 'YOUR_GEMINI_API_KEY') {
      setError('Gemini API key not configured. Add VITE_GEMINI_API_KEY to your .env file.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResponse('');

    try {
      const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);
      const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

      const prompt = `You are an expert 8085/8086 assembly language instructor. Analyze the following assembly code and provide:

1. A clear, concise one-paragraph explanation of what this code does.
2. If there are any obvious errors or issues, briefly point them out at the end.

Keep the response short and educational — no more than 5-6 sentences for the explanation. If there are no errors, don't mention errors at all.

Code:
\`\`\`
${code}
\`\`\``;

      const result = await model.generateContent(prompt);
      const text = result.response.text();
      setResponse(text);
    } catch (err) {
      console.error('Gemini API error:', err);
      if (err.message?.includes('API_KEY')) {
        setError('Invalid API key. Check your Gemini API key.');
      } else if (err.message?.includes('quota')) {
        setError('API quota exceeded. Try again later.');
      } else {
        setError(`AI analysis failed: ${err.message}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="ai-panel-overlay">
      <div className="ai-panel">
        <div className="ai-panel-header">
          <div className="ai-title">
            <span className="ai-icon">✨</span>
            <h3>AI Code Analysis</h3>
          </div>
          <button className="ai-close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="ai-panel-body">
          {!response && !isLoading && !error && (
            <div className="ai-prompt-area">
              <p className="ai-info">Send your current code to Gemini AI for a quick explanation and error check.</p>
              <button className="ai-analyze-btn" onClick={analyzeCode}>
                ✨ Analyze Code
              </button>
            </div>
          )}

          {isLoading && (
            <div className="ai-loading">
              <div className="ai-spinner"></div>
              <p>Analyzing your code...</p>
            </div>
          )}

          {error && (
            <div className="ai-error">
              <p>{error}</p>
              <button className="ai-retry-btn" onClick={analyzeCode}>Try Again</button>
            </div>
          )}

          {response && (
            <div className="ai-response">
              <div className="ai-response-text">{response}</div>
              <button className="ai-retry-btn" onClick={analyzeCode}>Analyze Again</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AIPanel;
