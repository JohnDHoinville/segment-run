import React, { useState } from 'react';
import { API_URL } from '../config';

function LoginForm({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const endpoint = isRegistering ? '/auth/register' : '/auth/login';
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          username: username.trim(),
          password: password
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Server error');
      }

      const data = await response.json();
      console.log('Login response:', data);
      if (data.user_id) {
        onLogin(data.user_id, username);
      } else {
        throw new Error('No user ID received from server');
      }
    } catch (error) {
      console.error('Login error:', error);
      setError(error.message || 'Failed to connect to server');
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>{isRegistering ? 'Create Account' : 'Welcome Back'}</h2>
        <p className="login-subtitle">
          {isRegistering 
            ? 'Create an account to start analyzing your runs' 
            : 'Sign in to access your running analytics'}
        </p>
        
        {error && <div className="login-error">{error}</div>}
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button type="submit" className="login-button">
            {isRegistering ? 'Create Account' : 'Sign In'}
          </button>
        </form>
        
        <div className="login-footer">
          <button 
            onClick={() => setIsRegistering(!isRegistering)}
            className="toggle-auth-button"
          >
            {isRegistering 
              ? 'Already have an account? Sign In' 
              : 'Need an account? Create one'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default LoginForm; 