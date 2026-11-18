import { useState } from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth/AuthContext';
import Login from './auth/Login';
import Register from './auth/Register';
import Strategic from './dashboard/Strategic';

/** Show the verified account and revoke its session on request. */
function Account() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  if (loading) return <p role="status">Verifying session…</p>;
  if (!user) return <Navigate to="/login" replace />;
  async function signOut() {
    setPending(true);
    setError('');
    try { await logout(); navigate('/login', { replace: true }); }
    catch { setError('Could not sign out. Please try again.'); }
    finally { setPending(false); }
  }
  return (
    <section>
      <p className="eyebrow">Verified session</p>
      <h1>Welcome, {user.username}</h1>
      <p className="muted">{user.email} · {user.role}</p>
      {error && <p role="alert" className="error">{error}</p>}
      <button type="button" disabled={pending} onClick={signOut}>{pending ? 'Signing out…' : 'Sign out'}</button>
      <nav aria-label="Dashboard"><Link to="/dashboard/strategic" aria-current="page">Strategic Command</Link></nav>
      <Strategic />
    </section>
  );
}

/** Route the identity screens through one verified-session provider. */
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <header>
          <Link className="brand" to="/">Canon <span>Global CIO Command Center</span></Link>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/account" element={<Account />} />
            <Route path="/dashboard/strategic" element={<Account />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </main>
      </AuthProvider>
    </BrowserRouter>
  );
}
