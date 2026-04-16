import React from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="landing-container">
      <div className="landing-content">
        <h1 className="landing-title">Opsis</h1>
        <p className="landing-subtitle">The Ultimate Assembly Experience</p>
        
        <div className="landing-buttons">
          <button 
            className="landing-btn primary"
            onClick={() => navigate('/auth')}
          >
            Login / Sign Up
          </button>
          
          <button 
            className="landing-btn secondary"
            onClick={() => navigate('/editor', { state: { isGuest: true } })}
          >
            Continue as Guest
          </button>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
