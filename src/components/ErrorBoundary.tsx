// src/components/ErrorBoundary.tsx
import React from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
  errorId?: string;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; retry: () => void; errorId: string }>;
  onError?: (error: Error, errorInfo: React.ErrorInfo, errorId: string) => void;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryCount: number = 0;
  private maxRetries: number = 3;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Generate unique error ID for tracking
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    return { hasError: true, error, errorId };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const errorId = this.state.errorId || `error_${Date.now()}`;

    // Log error details
    console.error('Frontend Error:', {
      errorId,
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo, errorId);
    }

    // Report to error tracking service (if available)
    this.reportError(error, errorInfo, errorId);

    this.setState({ errorInfo });
  }

  private reportError = (error: Error, errorInfo: React.ErrorInfo, errorId: string) => {
    // In a real application, this would send to error tracking service
    // For now, we'll just store in localStorage for debugging
    try {
      const errorReport = {
        errorId,
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent,
        retryCount: this.retryCount
      };

      const existingReports = JSON.parse(localStorage.getItem('errorReports') || '[]');
      existingReports.push(errorReport);
      // Keep only last 10 error reports
      if (existingReports.length > 10) {
        existingReports.shift();
      }
      localStorage.setItem('errorReports', JSON.stringify(existingReports));
    } catch (e) {
      console.warn('Failed to store error report:', e);
    }
  };

  private handleRetry = () => {
    if (this.retryCount < this.maxRetries) {
      this.retryCount += 1;
      this.setState({ hasError: false, error: undefined, errorInfo: undefined });
    } else {
      // Max retries reached, redirect to home
      window.location.href = '/';
    }
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  private handleReportBug = () => {
    const errorId = this.state.errorId;
    const subject = `Bug Report: Application Error ${errorId}`;
    const body = `Error ID: ${errorId}\n\nPlease describe what you were doing when this error occurred:\n\n`;

    // Try to open email client or bug reporting system
    const mailtoLink = `mailto:support@iit-healthcare.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(mailtoLink, '_blank');
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return (
          <FallbackComponent
            error={this.state.error}
            retry={this.handleRetry}
            errorId={this.state.errorId || 'unknown'}
          />
        );
      }

      // Default error UI
      return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 max-w-lg w-full">
            <div className="text-center mb-6">
              <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mb-4">
                <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Something went wrong
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
                We apologize for the inconvenience. This error has been logged and reported.
              </p>
              {this.state.errorId && (
                <p className="text-xs text-gray-500 dark:text-gray-500 mb-4">
                  Error ID: {this.state.errorId}
                </p>
              )}
            </div>

            <div className="space-y-3">
              {this.retryCount < this.maxRetries ? (
                <button
                  onClick={this.handleRetry}
                  className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again ({this.maxRetries - this.retryCount} attempts left)
                </button>
              ) : (
                <button
                  onClick={this.handleGoHome}
                  className="w-full bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
                >
                  <Home className="w-4 h-4" />
                  Go to Home
                </button>
              )}

              <button
                onClick={this.handleReportBug}
                className="w-full bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-4 py-3 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center justify-center gap-2"
              >
                <Bug className="w-4 h-4" />
                Report Bug
              </button>
            </div>

            {/* Development error details */}
            {process.env.NODE_ENV === 'development' && (
              <details className="mt-6 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
                <summary className="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300">
                  Error Details (Development Only)
                </summary>
                <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                  <p><strong>Message:</strong> {this.state.error.message}</p>
                  <p><strong>Stack:</strong></p>
                  <pre className="whitespace-pre-wrap mt-1">{this.state.error.stack}</pre>
                  {this.state.errorInfo && (
                    <>
                      <p><strong>Component Stack:</strong></p>
                      <pre className="whitespace-pre-wrap mt-1">{this.state.errorInfo.componentStack}</pre>
                    </>
                  )}
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Higher-order component for wrapping components with error boundary
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: React.ComponentType<{ error: Error; retry: () => void; errorId: string }>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  return WrappedComponent;
}

// Hook for handling async errors in functional components
export function useErrorHandler() {
  return (error: Error, errorInfo?: { componentStack?: string }) => {
    console.error('Async error caught:', error, errorInfo);

    // In a real app, this might trigger the nearest error boundary
    // For now, we'll just log it
    const errorId = `async_error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    try {
      const errorReport = {
        errorId,
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo?.componentStack,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent,
        type: 'async'
      };

      const existingReports = JSON.parse(localStorage.getItem('errorReports') || '[]');
      existingReports.push(errorReport);
      if (existingReports.length > 10) {
        existingReports.shift();
      }
      localStorage.setItem('errorReports', JSON.stringify(existingReports));
    } catch (e) {
      console.warn('Failed to store async error report:', e);
    }
  };
}
