import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom/vitest';
import App from '../App';
import { api, TOKEN_KEY } from '../api/client';

afterEach(() => { cleanup(); vi.restoreAllMocks(); sessionStorage.clear(); });
beforeEach(() => { window.history.replaceState({}, '', '/login'); });

describe('identity screens', () => {
  it('shows invalid credentials without navigating away', async () => {
    vi.spyOn(api, 'post').mockRejectedValue({ response: { status: 401 } });
    render(<App />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Username'), 'alice');
    await user.type(screen.getByLabelText('Password'), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid username or password');
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('signs in, displays the profile and signs out', async () => {
    vi.spyOn(api, 'post').mockImplementation((url) => url === '/auth/login'
      ? Promise.resolve({ data: { access_token: 'signed', user: { username: 'alice', email: 'alice@example.com', role: 'executive' } } })
      : Promise.resolve({}));
    render(<App />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Username'), 'alice');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('heading', { name: 'Welcome, alice' })).toBeInTheDocument();
    expect(sessionStorage.getItem(TOKEN_KEY)).toBe('signed');
    await user.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it('shows registration conflict and success', async () => {
    const post = vi.spyOn(api, 'post').mockRejectedValueOnce({ response: { status: 409 } }).mockResolvedValueOnce({ data: {} });
    window.history.replaceState({}, '', '/register');
    render(<App />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Username'), 'alice');
    await user.type(screen.getByLabelText('Email'), 'alice@example.com');
    await user.type(screen.getByLabelText('Password'), 'password123');
    await user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('already registered');
    await user.click(screen.getByRole('button', { name: 'Create account' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Account created');
    expect(post).toHaveBeenCalledTimes(2);
  });

  it('redirects a protected route without a token', async () => {
    window.history.replaceState({}, '', '/account');
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
  });
});
