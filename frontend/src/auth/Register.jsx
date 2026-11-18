import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

/** Create an account and direct the user to sign in. */
export default function Register() {
  const [values, setValues] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);
  function update(event) { setValues({ ...values, [event.target.name]: event.target.value }); }
  async function submit(event) {
    event.preventDefault();
    setPending(true);
    setError('');
    try {
      await api.post('/auth/register', values);
      setDone(true);
      setValues({ username: '', email: '', password: '' });
    } catch (failure) {
      setError(failure.response?.status === 409 ? 'Username or email is already registered.' : failure.response?.status === 422 ? 'Check your details. Passwords must be 8–72 UTF-8 bytes.' : 'Unable to register. Please try again.');
    } finally { setPending(false); }
  }
  return (
    <section className="auth-panel">
      <p className="eyebrow">Secure access</p>
      <h1>Create account</h1>
      {done ? <p role="status">Account created. <Link to="/login">Sign in</Link></p> : (
        <>
          <p className="muted">Register to access the command center.</p>
          {error && <p role="alert" className="error">{error}</p>}
          <form onSubmit={submit}>
            <label htmlFor="new-username">Username</label>
            <input id="new-username" name="username" autoComplete="username" required minLength="3" maxLength="50" value={values.username} onChange={update} />
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" autoComplete="email" required maxLength="100" value={values.email} onChange={update} />
            <label htmlFor="new-password">Password</label>
            <input id="new-password" name="password" type="password" autoComplete="new-password" required minLength="8" maxLength="72" value={values.password} onChange={update} />
            <button type="submit" disabled={pending}>{pending ? 'Creating account…' : 'Create account'}</button>
          </form>
        </>
      )}
      {!done && <p className="muted">Already registered? <Link to="/login">Sign in</Link></p>}
    </section>
  );
}
