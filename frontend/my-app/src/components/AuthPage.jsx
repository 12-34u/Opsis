import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../firebase';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword 
} from 'firebase/auth';
import './AuthPage.css';

const AuthPage = () => {
  const navigate = useNavigate();
  const [isSignUP, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Validate password strength
  const validatePassword = (pwd) => {
    if (pwd.length < 8) return "Password must be at least 8 characters long.";
    if (!/\d/.test(pwd)) return "Password must contain at least 1 number.";
    if (!/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]+/.test(pwd)) return "Password must contain at least 1 special character.";
    return null;
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setError('');
    
    if (isSignUP) {
      const pwdError = validatePassword(password);
      if (pwdError) {
        setError(pwdError);
        return;
      }
    }

    setLoading(true);
    try {
      if (isSignUP) {
        await createUserWithEmailAndPassword(auth, email, password);
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      // Successful auth -> route to editor
      navigate('/editor', { state: { isGuest: false } });
    } catch (err) {
      setError(err.message.replace('Firebase: ', '')); // Polish error message
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2 className="auth-title">
          {isSignUP ? 'Create an Account' : 'Welcome Back'}
        </h2>
        
        {error && <div className="auth-error">{error}</div>}
        
        <form onSubmit={handleAuth} className="auth-form">
          <div className="input-group">
            <label>Email</label>
            <input 
              type="email" 
              required 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
            />
          </div>
          
          <div className="input-group">
            <label>Password</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
          </div>
          
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? 'Processing...' : (isSignUP ? 'Sign Up' : 'Login')}
          </button>
        </form>

        <div className="auth-toggle">
          <span>
            {isSignUP ? 'Already have an account? ' : "Don't have an account? "}
          </span>
          <button 
            type="button" 
            className="toggle-btn"
            onClick={() => {
              setIsSignUp(!isSignUP);
              setError('');
            }}
          >
            {isSignUP ? 'Log In' : 'Sign Up'}
          </button>
        </div>
        
        <button 
          className="guest-bypass" 
          onClick={() => navigate('/editor', { state: { isGuest: true } })}
        >
          Or continue as Guest
        </button>
      </div>
    </div>
  );
};

export default AuthPage;
