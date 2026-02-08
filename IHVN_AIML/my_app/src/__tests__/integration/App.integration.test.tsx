import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import App from '../../App';
import { ApiProvider } from '../../contexts/ApiContext';

// Mock the API context
jest.mock('../../contexts/ApiContext', () => ({
  ApiProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useApi: () => ({
    login: jest.fn(),
    logout: jest.fn(),
    isAuthenticated: false,
    user: null,
    loading: false,
  }),
}));

// Mock the Navigation component
jest.mock('../../components/Navigation', () => ({
  Navigation: () => <nav>Navigation</nav>,
}));

// Mock all lazy-loaded components
jest.mock('../../pages/Login', () => ({
  __esModule: true,
  default: () => <div>Login Page</div>,
}), { virtual: true });

jest.mock('../../pages/Dashboard', () => ({
  __esModule: true,
  default: () => <div>Dashboard Page</div>,
}), { virtual: true });

jest.mock('../../pages/ModelMetrics', () => ({
  __esModule: true,
  default: () => <div>Model Metrics Page</div>,
}), { virtual: true });

jest.mock('../../pages/PredictionForm', () => ({
  __esModule: true,
  default: () => <div>Prediction Form Page</div>,
}), { virtual: true });

jest.mock('../../pages/PatientList', () => ({
  __esModule: true,
  default: () => <div>Patient List Page</div>,
}), { virtual: true });

jest.mock('../../pages/PatientDetail', () => ({
  __esModule: true,
  default: () => <div>Patient Detail Page</div>,
}), { virtual: true });

jest.mock('../../pages/PatientForm', () => ({
  __esModule: true,
  default: () => <div>Patient Form Page</div>,
}), { virtual: true });

jest.mock('../../pages/Reports', () => ({
  __esModule: true,
  default: () => <div>Reports Page</div>,
}), { virtual: true });

jest.mock('../../pages/Profile', () => ({
  __esModule: true,
  default: () => <div>Profile Page</div>,
}), { virtual: true });

// Mock ProtectedRoute
jest.mock('../../components/ProtectedRoute', () => ({
  __esModule: true,
  default: ({ children, requireAuth }: { children: React.ReactNode; requireAuth?: boolean }) => {
    if (requireAuth === false) {
      return <div>{children}</div>;
    }
    return <div>Protected: {children}</div>;
  },
}));

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <ApiProvider>
        {component}
      </ApiProvider>
    </BrowserRouter>
  );
};

describe('App Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the app with navigation', () => {
    renderWithProviders(<App />);

    expect(screen.getByText('Navigation')).toBeInTheDocument();
  });

  it('renders login page on /login route', () => {
    window.history.pushState({}, '', '/login');

    renderWithProviders(<App />);

    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('renders dashboard page on / route', () => {
    window.history.pushState({}, '', '/');

    renderWithProviders(<App />);

    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
  });

  it('renders model metrics page on /metrics route', () => {
    window.history.pushState({}, '', '/metrics');

    renderWithProviders(<App />);

    expect(screen.getByText('Model Metrics Page')).toBeInTheDocument();
  });

  it('renders prediction form page on /predict route', () => {
    window.history.pushState({}, '', '/predict');

    renderWithProviders(<App />);

    expect(screen.getByText('Prediction Form Page')).toBeInTheDocument();
  });

  it('renders patient list page on /patients route', () => {
    window.history.pushState({}, '', '/patients');

    renderWithProviders(<App />);

    expect(screen.getByText('Patient List Page')).toBeInTheDocument();
  });

  it('renders patient form page on /patients/new route', () => {
    window.history.pushState({}, '', '/patients/new');

    renderWithProviders(<App />);

    expect(screen.getByText('Patient Form Page')).toBeInTheDocument();
  });

  it('renders patient detail page on /patients/:uuid route', () => {
    window.history.pushState({}, '', '/patients/test-uuid');

    renderWithProviders(<App />);

    expect(screen.getByText('Patient Detail Page')).toBeInTheDocument();
  });

  it('renders patient edit form on /patients/:uuid/edit route', () => {
    window.history.pushState({}, '', '/patients/test-uuid/edit');

    renderWithProviders(<App />);

    expect(screen.getByText('Patient Form Page')).toBeInTheDocument();
  });

  it('renders reports page on /reports route', () => {
    window.history.pushState({}, '', '/reports');

    renderWithProviders(<App />);

    expect(screen.getByText('Reports Page')).toBeInTheDocument();
  });

  it('renders profile page on /profile route', () => {
    window.history.pushState({}, '', '/profile');

    renderWithProviders(<App />);

    expect(screen.getByText('Profile Page')).toBeInTheDocument();
  });

  it('shows loading spinner during lazy loading', async () => {
    // Mock a delay in the lazy component
    const originalLogin = jest.requireMock('../../pages/Login').default;
    jest.doMock('../../pages/Login', () => ({
      __esModule: true,
      default: () => {
        React.useEffect(() => {
          // Simulate loading delay
          setTimeout(() => {}, 100);
        }, []);
        return <div>Login Page</div>;
      },
    }));

    window.history.pushState({}, '', '/login');

    renderWithProviders(<App />);

    // The Suspense fallback should show initially
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('handles route changes correctly', async () => {
    const user = userEvent.setup();

    window.history.pushState({}, '', '/');

    renderWithProviders(<App />);

    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();

    // Simulate navigation (this would normally be handled by react-router)
    // In a real integration test, you'd use a router testing library
    window.history.pushState({}, '', '/patients');

    // Re-render to simulate route change
    renderWithProviders(<App />);

    expect(screen.getByText('Patient List Page')).toBeInTheDocument();
  });

  it('maintains app structure across routes', () => {
    window.history.pushState({}, '', '/login');

    renderWithProviders(<App />);

    // Navigation should always be present
    expect(screen.getByText('Navigation')).toBeInTheDocument();

    // Main content area should exist
    const mainElement = screen.getByRole('main');
    expect(mainElement).toBeInTheDocument();
  });

  it('handles invalid routes gracefully', () => {
    window.history.pushState({}, '', '/invalid-route');

    renderWithProviders(<App />);

    // Should render dashboard as default/fallback
    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
  });

  it('renders with proper semantic HTML structure', () => {
    renderWithProviders(<App />);

    // Should have proper heading structure
    const headings = screen.getAllByRole('heading');
    expect(headings.length).toBeGreaterThan(0);

    // Should have main content area
    expect(screen.getByRole('main')).toBeInTheDocument();

    // Should have navigation
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });
});
