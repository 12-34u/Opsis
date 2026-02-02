import React from 'react';
import '../styles/OutputPanel.css';

export default function OutputPanel({ output = [], error = null, instructionCount = 0, isRunning = false }) {
  return (
    <div className="output-panel">
      <div className="output-header">
        <h3>Execution Output</h3>
        {isRunning && <span className="running-indicator">● Running...</span>}
        {instructionCount > 0 && (
          <span className="instruction-count">{instructionCount} instructions</span>
        )}
      </div>

      {error && (
        <div className="error-box">
          <div className="error-title">❌ Error</div>
          <div className="error-message">{error}</div>
        </div>
      )}

      {output.length === 0 && !error ? (
        <div className="output-empty">
          <p>No output yet. Run assembly code to see results.</p>
        </div>
      ) : (
        <div className="output-list">
          {output.map((item, idx) => (
            <div key={idx} className="output-item">
              <span className="output-index">#{idx + 1}</span>
              <div className="output-content">
                <div className="output-type">{item.type || 'Output'}</div>
                <div className="output-values">
                  <span className="value hex" title="Hexadecimal">{item.hex}</span>
                  <span className="value dec" title="Decimal">{item.decimal}</span>
                  <span className="value bin" title="Binary">{item.binary}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
