/**
 * Enhanced Error Boundary Component
 *
 * Provides comprehensive error handling with:
 * - Error logging to Sentry (with initialization check)
 * - User-friendly error display
 * - Automatic retry mechanisms
 * - Development mode error details
 * - Graceful fallback UI
 */

import React, { Component, ErrorInfo, ReactNode, useState, useCallback } from 'react';
import { captureException, addBreadcrumb, isSentryInitialized } from '@/lib/sentry';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, RefreshCw, Bug } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showDetails?: boolean;
  enableRetry?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  retryCount: number;
}

/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors anywhere in the component tree,
 * logs those errors, and displays a fallback UI
 */
export class ErrorBoundaryEnhanced extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  private maxRetries = 3;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(_error: Error): Partial<ErrorBoundaryState> {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error to Sentry (only if initialized)
    if (isSentryInitialized()) {
      captureException(error, {
        componentStack: errorInfo.componentStack,
        retryCount: this.state.retryCount,
      });

      // Add breadcrumb for context
      addBreadcrumb(
        'Error boundary caught an error',
        'error',
        'error',
        {
          error: error.message,
          componentStack: errorInfo.componentStack,
        }
      );
    } else {
      // Fallback console logging when Sentry is not available
      console.error('Error caught by boundary (Sentry not initialized):', error);
      console.error('Error info:', errorInfo);
    }

    // Update state with error details
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to console in development
    if (import.meta.env.DEV) {
      console.error('Error caught by boundary:', error);
      console.error('Error info:', errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0,
    });
  };

  handleRetry = () => {
    if (this.state.retryCount < this.maxRetries) {
      this.setState((prevState) => ({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: prevState.retryCount + 1,
      }));
    }
  };

  canRetry = () => {
    return this.props.enableRetry && this.state.retryCount < this.maxRetries;
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      const isDev = import.meta.env.DEV;
      const showDetails = this.props.showDetails ?? isDev;

      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-slate-900 dark:to-gray-800 p-4">
          <Card className="max-w-2xl w-full">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-full">
                  <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <CardTitle className="text-red-600 dark:text-red-400">
                    Something went wrong
                  </CardTitle>
                  <CardDescription>
                    {this.canRetry()
                      ? `An error occurred (Attempt ${this.state.retryCount + 1}/${this.maxRetries})`
                      : 'An unexpected error occurred'}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-muted-foreground">
                <p>
                  We're sorry for the inconvenience. Our team has been notified and
                  is working to fix the issue.
                </p>
                {this.canRetry() && (
                  <p className="mt-2">You can try again or refresh the page.</p>
                )}
              </div>

              {showDetails && this.state.error && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2">
                    <Bug className="h-4 w-4" />
                    Error Details (Development Mode)
                  </summary>
                  <div className="mt-3 p-4 bg-slate-100 dark:bg-slate-800 rounded-md overflow-auto max-h-96">
                    <div className="space-y-2 text-xs font-mono">
                      <div>
                        <strong>Error:</strong> {this.state.error.toString()}
                      </div>
                      {this.state.error.stack && (
                        <div>
                          <strong>Stack Trace:</strong>
                          <pre className="whitespace-pre-wrap mt-1 text-red-600 dark:text-red-400">
                            {this.state.error.stack}
                          </pre>
                        </div>
                      )}
                      {this.state.errorInfo && (
                        <div>
                          <strong>Component Stack:</strong>
                          <pre className="whitespace-pre-wrap mt-1 text-blue-600 dark:text-blue-400">
                            {this.state.errorInfo.componentStack}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </details>
              )}

              <div className="flex flex-wrap gap-2 pt-4">
                {this.canRetry() && (
                  <Button
                    onClick={this.handleRetry}
                    variant="default"
                    className="flex-1"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Try Again
                  </Button>
                )}
                <Button
                  onClick={this.handleReset}
                  variant="outline"
                  className="flex-1"
                >
                  Go to Home
                </Button>
                <Button
                  onClick={() => window.location.reload()}
                  variant="ghost"
                  className="flex-1"
                >
                  Refresh Page
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Functional wrapper for easier usage
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundaryEnhanced {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundaryEnhanced>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}

/**
 * Return type for useErrorBoundary hook
 */
export interface UseErrorBoundaryReturn {
  /**
   * Set an error state that can be handled by the error boundary
   *
   * @note This does NOT throw an error. React Error Boundaries only catch
   * errors thrown during rendering, lifecycle methods, and constructors.
   * Errors thrown in event handlers, async functions, or timeouts will NOT
   * be caught by Error Boundaries.
   *
   * To handle errors in event handlers, use this method to set the error state
   * and conditionally render an error UI, or use `handleError` to log to Sentry.
   *
   * @example
   * ```tsx
   * const { setError } = useErrorBoundary();
   *
   * const handleClick = () => {
   *   try {
   *     riskyOperation();
   *   } catch (err) {
   *     setError(err as Error);
   *   }
   * };
   * ```
   */
  setError: (error: Error) => void;
  
  /**
   * Clear any currently set error
   */
  clearError: () => void;
  
  /**
   * Log an error to Sentry without affecting the UI
   *
   * Use this for errors that don't need to interrupt the user flow
   * but should still be tracked for monitoring.
   *
   * @example
   * ```tsx
   * const { handleError } = useErrorBoundary();
   *
   * const handleAsyncError = async () => {
   *   try {
   *     await asyncOperation();
   *   } catch (err) {
   *     handleError(err as Error);
   *     // Show a toast notification instead
   *     toast.error('Operation failed');
   *   }
   * };
   * ```
   */
  handleError: (error: Error, context?: Record<string, any>) => void;
  
  /**
   * The current error, if one has been set via setError
   */
  error: Error | null;
}

/**
 * Hook to programmatically handle errors
 *
 * ## Important Limitations
 *
 * React Error Boundaries **do not catch** errors thrown in:
 * - Event handlers (onClick, onChange, etc.)
 * - Async functions (promises, setTimeout, etc.)
 * - Server-side rendering
 *
 * This hook provides a state-based approach to handle errors in these scenarios:
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { error, setError, clearError, handleError } = useErrorBoundary();
 *
 *   const handleClick = () => {
 *     try {
 *       riskyOperation();
 *     } catch (err) {
 *       // Set error state to conditionally render error UI
 *       setError(err as Error);
 *     }
 *   };
 *
 *   const handleAsyncClick = async () => {
 *     try {
 *       await asyncOperation();
 *     } catch (err) {
 *       // Log to Sentry without interrupting flow
 *       handleError(err as Error, { action: 'asyncClick' });
 *       toast.error('Operation failed');
 *     }
 *   };
 *
 *   if (error) {
 *     return <ErrorFallback error={error} reset={clearError} />;
 *   }
 *
 *   return <button onClick={handleClick}>Click me</button>;
 * }
 * ```
 */
export function useErrorBoundary(): UseErrorBoundaryReturn {
  const [error, setError] = useState<Error | null>(null);
  
  const clearError = useCallback(() => {
    setError(null);
  }, []);
  
  const handleError = useCallback((error: Error, context?: Record<string, any>) => {
    // Log to Sentry (with built-in initialization check)
    captureException(error, {
      source: 'useErrorBoundary',
      ...context,
    });
    
    // Also log to console for development
    if (import.meta.env.DEV) {
      console.error('Error logged via useErrorBoundary:', error);
    }
  }, []);
  
  return {
    error,
    setError,
    clearError,
    handleError,
  };
}

export default ErrorBoundaryEnhanced;
