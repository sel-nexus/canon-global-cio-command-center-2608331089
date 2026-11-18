import { useState } from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth/AuthContext';
import Login from './auth/Login';
import Register from './auth/Register';
import Strategic from './dashboard/Strategic';
import Regional from './dashboard/Regional';
import Business from './dashboard/Business';
import Operations from './dashboard/Operations';
import Governance from './dashboard/Governance';
import Innovation from './dashboard/Innovation';
import Partnerships from './dashboard/Partnerships';

/** Show the verified account and revoke its session on request. */
function Account() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
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
      <nav aria-label="Dashboard" className="dashboard-nav">
        <Link to="/dashboard/strategic" aria-current={['/account', '/dashboard/strategic'].includes(location.pathname) ? 'page' : undefined}>Strategic Command</Link>
        <Link to="/dashboard/executive-summary" aria-current={location.pathname === '/dashboard/executive-summary' ? 'page' : undefined}>Executive Summary</Link>
        <Link to="/dashboard/business" aria-current={location.pathname === '/dashboard/business' ? 'page' : undefined}>Business Impact</Link>
        <Link to="/dashboard/operations" aria-current={location.pathname === '/dashboard/operations' ? 'page' : undefined}>Operations</Link>
        <Link to="/dashboard/governance" aria-current={location.pathname === '/dashboard/governance' ? 'page' : undefined}>Risk &amp; Governance</Link>
        <Link to="/dashboard/innovation" aria-current={location.pathname === '/dashboard/innovation' ? 'page' : undefined}>Innovation</Link>
        <Link to="/dashboard/partnerships" aria-current={location.pathname === '/dashboard/partnerships' ? 'page' : undefined}>Partnerships</Link>
      </nav>
      {location.pathname === '/dashboard/executive-summary' ? <Regional /> : location.pathname === '/dashboard/business' ? <Business /> : location.pathname === '/dashboard/operations' ? <Operations /> : location.pathname === '/dashboard/governance' ? <Governance /> : location.pathname === '/dashboard/innovation' ? <Innovation /> : location.pathname === '/dashboard/partnerships' ? <Partnerships /> : <Strategic />}
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
            <Route path="/dashboard/executive-summary" element={<Account />} />
            <Route path="/dashboard/business" element={<Account />} />
            <Route path="/dashboard/operations" element={<Account />} />
            <Route path="/dashboard/governance" element={<Account />} />
            <Route path="/dashboard/innovation" element={<Account />} />
            <Route path="/dashboard/partnerships" element={<Account />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </main>
      </AuthProvider>
    </BrowserRouter>
  );
}
