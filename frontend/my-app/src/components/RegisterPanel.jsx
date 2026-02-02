import React from 'react';
import '../styles/RegisterPanel.css';

export default function RegisterPanel({ state }) {
  if (!state) return null;

  const registers = state.registers || {};
  const flags = state.flags || {};

  const formatHex = (value) => '0x' + value.toString(16).toUpperCase().padStart(2, '0');
  const formatBin = (value) => value.toString(2).padStart(8, '0');

  return (
    <div className="register-panel">
      <div className="register-section">
        <h3>Registers</h3>
        <div className="register-grid">
          {Object.entries(registers).map(([name, value]) => (
            <div key={name} className="register-item">
              <div className="register-name">{name}</div>
              <div className="register-value">
                <div className="hex">{formatHex(value)}</div>
                <div className="dec">{value}</div>
                <div className="bin">{formatBin(value)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="register-section">
        <h3>Flags</h3>
        <div className="flags-grid">
          {Object.entries(flags).map(([name, value]) => (
            <div key={name} className={`flag-item ${value ? 'set' : 'clear'}`}>
              <span className="flag-name">{name}</span>
              <span className="flag-value">{value ? '1' : '0'}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="register-section">
        <h3>Pointers</h3>
        <div className="pointer-grid">
          <div className="pointer-item">
            <div className="pointer-name">PC (Program Counter)</div>
            <div className="pointer-value">{state.pc || 0}</div>
          </div>
          <div className="pointer-item">
            <div className="pointer-name">SP (Stack Pointer)</div>
            <div className="pointer-value">{formatHex(state.sp || 0)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
