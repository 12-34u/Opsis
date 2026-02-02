import React, { useState } from 'react';
import '../styles/MemoryViewer.css';

export default function MemoryViewer({ memory = [], maxDisplay = 64 }) {
  const [startAddr, setStartAddr] = useState(0);

  const endAddr = Math.min(startAddr + maxDisplay, memory.length);
  const visibleMemory = memory.slice(startAddr, endAddr);

  const formatHex = (value) => value.toString(16).toUpperCase().padStart(2, '0');
  const formatAddr = (addr) => '0x' + addr.toString(16).toUpperCase().padStart(2, '0');

  const handleScroll = (direction) => {
    const step = 16;
    if (direction === 'up') {
      setStartAddr(Math.max(0, startAddr - step));
    } else {
      setStartAddr(Math.min(memory.length - maxDisplay, startAddr + step));
    }
  };

  return (
    <div className="memory-viewer">
      <div className="memory-header">
        <h3>Memory</h3>
        <div className="memory-controls">
          <button onClick={() => handleScroll('up')} className="scroll-btn">↑</button>
          <input
            type="number"
            value={startAddr}
            onChange={(e) => setStartAddr(Math.max(0, parseInt(e.target.value) || 0))}
            className="addr-input"
            placeholder="Address"
            min="0"
            max={Math.max(0, memory.length - 1)}
          />
          <button onClick={() => handleScroll('down')} className="scroll-btn">↓</button>
        </div>
      </div>

      <div className="memory-table">
        <div className="memory-row header">
          <div className="addr-col">Address</div>
          <div className="values-row">
            {Array.from({ length: 16 }).map((_, i) => (
              <div key={i} className="cell-header">{formatHex(i)}</div>
            ))}
          </div>
        </div>

        {Array.from({ length: Math.ceil(visibleMemory.length / 16) }).map((_, rowIdx) => {
          const rowStart = rowIdx * 16;
          const rowEnd = Math.min(rowStart + 16, visibleMemory.length);
          const rowAddr = startAddr + rowStart;

          return (
            <div key={rowIdx} className="memory-row">
              <div className="addr-col">{formatAddr(rowAddr)}</div>
              <div className="values-row">
                {Array.from({ length: 16 }).map((_, colIdx) => {
                  const value = visibleMemory[rowStart + colIdx];
                  const isValid = rowStart + colIdx < visibleMemory.length;
                  return (
                    <div
                      key={colIdx}
                      className={`memory-cell ${isValid ? '' : 'empty'} ${
                        value !== 0 ? 'populated' : 'zero'
                      }`}
                    >
                      {isValid ? formatHex(value) : '--'}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="memory-footer">
        <span className="memory-info">
          Showing: {startAddr}-{endAddr - 1} ({visibleMemory.length} bytes)
        </span>
      </div>
    </div>
  );
}
