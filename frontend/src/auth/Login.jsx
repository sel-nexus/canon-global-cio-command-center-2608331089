import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

/** Present credentials and show authentication errors inline. */
export default function Login() {
  const { user, login, restoreError } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  if (user) return <Navigate to="/account" replace />;

  async function submit(event) {
    event.preventDefault();
    setPending(true);
    setError('');
    try {
      await login(username, password);
      navigate('/account', { replace: true });
    } catch (failure) {
      setError(failure.response?.status === 401 ? 'Invalid username or password.' : 'Unable to sign in. Please try again.');
    } finally { setPending(false); }
  }

  return (
    <section className="auth-panel">
      <p className="eyebrow">Secure access</p>
      <h1>Sign in</h1>
      <p className="muted">Access your executive command center account.</p>
      {(error || restoreError) && <p role="alert" className="error">{error || restoreError}</p>}
      <form onSubmit={submit}>
        <label htmlFor="username">Username</label>
        <input id="username" autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
        <button type="submit" disabled={pending}>{pending ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <p className="muted">Need an account? <Link to="/register">Register</Link></p>
    </section>
  );
}
