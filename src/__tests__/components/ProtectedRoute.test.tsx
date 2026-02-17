/**
 * Unit tests for ProtectedRoute component
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ProtectedRoute from '../../components/ProtectedRoute';

// Mock the AuthContext
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
    isLoading: false,
  }),
}));

const mockAuthContext = require('../../contexts/AuthContext');

describe('ProtectedRoute Component', () => {
  const renderWithRouter = (component: React.ReactNode) => {
    return render(
      <BrowserRouter>
        {component}
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('redirects to login when not authenticated', () => {
    mockAuthContext.useAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      isLoading: false,
    });

    renderWithRouter(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    // Should redirect to login
    expect(window.location.pathname).toBe('/login');
  });

  test('renders children when authenticated', () => {
    mockAuthContext.useAuth.mockReturnValue({
      isAuthenticated: true,
      user: { username: 'testuser', roles: ['healthcare_provider'] },
      isLoading: false,
    });

    renderWithRouter(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  test('shows loading spinner while checking auth', () => {
    mockAuthContext.useAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      isLoading: true,
    });

    renderWithRouter(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    );

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  test('renders children when requireAuth is false', () => {
    mockAuthContext.useAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      isLoading: false,
    });

    renderWithRouter(
      <ProtectedRoute requireAuth={false}>
        <div>Public Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Public Content')).toBeInTheDocument();
  });
});
