'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === 'alvina' && password === 'alvina123') {
      // Simulate setting an auth token / session for demo purposes
      document.cookie = "adminAuth=true; path=/";
      router.push('/admin/dashboard');
    } else {
      setError('Invalid username or password.');
    }
  };

  return (
    <main className="animate-fade-in" style={{ padding: '8rem 2rem', minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <div className="glass-panel" style={{ padding: '3rem', width: '100%', maxWidth: '400px', display: 'flex', flexDirection: 'column' }}>
        <h1 className="elegant-title" style={{ textAlign: 'center', fontSize: '2rem', marginBottom: '2rem' }}>
          Restricted Access
        </h1>
        
        {error && <div style={{ color: 'red', marginBottom: '1rem', textAlign: 'center' }}>{error}</div>}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label className="form-label" style={{ color: 'var(--text-main)', fontWeight: 'bold' }}>Username</label>
            <input 
              type="text" 
              className="input-field" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username" 
              required
            />
          </div>
          <div>
            <label className="form-label" style={{ color: 'var(--text-main)', fontWeight: 'bold' }}>Password</label>
            <input 
              type="password" 
              className="input-field" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password" 
              required
            />
          </div>
          
          <button type="submit" className="btn btn-primary" style={{ marginTop: '1rem' }}>
            Login to Dashboard
          </button>
        </form>
      </div>
    </main>
  );
}
