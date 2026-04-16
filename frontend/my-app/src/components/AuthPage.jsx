import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../firebase';
import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword,
  updateProfile
} from 'firebase/auth';
import './AuthPage.css';

const AuthPage = () => {
  const navigate = useNavigate();
  const [isSignUP, setIsSignUp] = useState(false);
  const [username, setUsername] = useState('');
  const [loginIdentifier, setLoginIdentifier] = useState(''); // Can be username or email
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
      if (!username.trim()) {
        setError("Username is required.");
        return;
      }
      const pwdError = validatePassword(password);
      if (pwdError) {
        setError(pwdError);
        return;
      }
    }

    setLoading(true);
    try {
      if (isSignUP) {
        // Sign Up Flow
        const userCredential = await createUserWithEmailAndPassword(auth, loginIdentifier, password);
        
        // Update user profile with Username
        await updateProfile(userCredential.user, {
          displayName: username
        });

        // Store mapping in localStorage so they can login with Username later locally
        localStorage.setItem(`opsis_username_email_${username}`, loginIdentifier);
        
        navigate('/editor', { state: { isGuest: false, userEmail: loginIdentifier } });
      } else {
        // Log In Flow
        let targetEmail = loginIdentifier;
        
        // If they didn't type an '@', assume it's a Username and lookup their email locally
        if (!targetEmail.includes('@')) {
          const cachedEmail = localStorage.getItem(`opsis_username_email_${targetEmail}`);
          if (cachedEmail) {
            targetEmail = cachedEmail;
          } else {
            throw new Error("Local username cache not found. Please log in using your Email Address.");
          }
        }
        
        await signInWithEmailAndPassword(auth, targetEmail, password);
        
        navigate('/editor', { state: { isGuest: false, userEmail: targetEmail } });
      }
    } catch (err) {
      setError(err.message.replace('Firebase: ', ''));
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
          {isSignUP && (
            <div className="input-group">
              <label>Username</label>
              <input 
                type="text" 
                required 
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Choose a username"
              />
            </div>
          )}
          
          <div className="input-group">
            <label>{isSignUP ? 'Email' : 'Username or Email'}</label>
            <input 
              type={isSignUP ? 'email' : 'text'} 
              required 
              value={loginIdentifier}
              onChange={(e) => setLoginIdentifier(e.target.value)}
              placeholder={isSignUP ? 'Enter your email' : 'Username or Email'}
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
              // Reset fields when toggling
              setLoginIdentifier('');
              setPassword('');
              setUsername('');
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
