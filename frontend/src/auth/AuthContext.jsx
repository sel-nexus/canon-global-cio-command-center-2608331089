import { createContext, useContext, useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { api, TOKEN_KEY } from '../api/client';

const AuthContext = createContext(null);

/** Maintain a verified session across page refreshes within the current tab. */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(sessionStorage.getItem(TOKEN_KEY)));
  const [restoreError, setRestoreError] = useState('');

  useEffect(() => {
    const expired = () => setUser(null);
    window.addEventListener('session-expired', expired);
    if (sessionStorage.getItem(TOKEN_KEY)) {
      api.get('/auth/me').then(({ data }) => setUser(data)).catch((error) => {
        if (error.response?.status !== 401) setRestoreError('Could not verify your session. Please sign in again.');
        sessionStorage.removeItem(TOKEN_KEY);
      }).finally(() => setLoading(false));
    }
    return () => window.removeEventListener('session-expired', expired);
  }, []);

  async function login(username, password) {
    const { data } = await api.post('/auth/login', { username, password });
    sessionStorage.setItem(TOKEN_KEY, data.access_token);
    setRestoreError('');
    setUser(data.user);
  }

  async function logout() {
    await api.post('/auth/logout');
    sessionStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, restoreError, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
AuthProvider.propTypes = { children: PropTypes.node.isRequired };

/** Return the active authentication context. */
export function useAuth() { return useContext(AuthContext); }
