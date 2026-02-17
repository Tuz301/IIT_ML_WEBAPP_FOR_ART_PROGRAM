/**
 * useApiCall Hook
 * 
 * Custom hook for making API calls with comprehensive error handling:
 * - Automatic retry with exponential backoff
 * - Request cancellation on component unmount
 * - Loading state management
 * - Error handling and reporting
 * - Offline detection and queuing
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { handleApiError, isOnline, waitForOnline } from '@/lib/api-error-handler';
import { captureException, addBreadcrumb } from '@/lib/sentry';
import { toast } from '@/hooks/use-toast';

// ============================================================================
// Types
// ============================================================================

interface ApiCallState<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  isRetrying: boolean;
  retryCount: number;
  isOffline: boolean;
}

interface ApiCallOptions {
  retry?: boolean;
  retryConfig?: {
    maxRetries?: number;
    retryDelay?: number;
  };
  timeout?: number;
  enableQueue?: boolean;
  onSuccess?: (data: unknown) => void;
  onError?: (error: Error) => void;
  showToast?: boolean;
  immediate?: boolean;
}

interface UseApiCallReturn<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  isRetrying: boolean;
  retryCount: number;
  isOffline: boolean;
  execute: (...args: unknown[]) => Promise<T>;
  reset: () => void;
  refetch: () => Promise<void>;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Custom hook for making API calls with error handling
 * 
 * @param apiFn - The API function to call
 * @param options - Configuration options
 * @returns Object containing state and control functions
 */
export function useApiCall<T>(
  apiFn: (...args: unknown[]) => Promise<T>,
  options: ApiCallOptions = {}
): UseApiCallReturn<T> {
  const {
    retry = true,
    retryConfig = {},
    timeout = 30000,
    enableQueue = false,
    onSuccess,
    onError,
    showToast = true,
    immediate = false,
  } = options;

  // State management
  const [state, setState] = useState<ApiCallState<T>>({
    data: null,
    isLoading: false,
    error: null,
    isRetrying: false,
    retryCount: 0,
    isOffline: !isOnline(),
  });

  // Refs for cleanup and tracking
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);
  const lastArgsRef = useRef<unknown[]>([]);

  /**
   * Update state safely (only if mounted)
   */
  const safeSetState = useCallback((updates: Partial<ApiCallState<T>>) => {
    if (isMountedRef.current) {
      setState((prev) => ({ ...prev, ...updates }));
    }
  }, []);

  /**
   * Execute the API call
   */
  const execute = useCallback(
    async (...args: unknown[]): Promise<T> => {
      // Store args for potential retry
      lastArgsRef.current = args;

      // Check if offline
      if (!isOnline()) {
        safeSetState({ isOffline: true, isLoading: false });
        
        if (showToast) {
          toast({
            title: 'Offline',
            description: 'You are currently offline. Please check your connection.',
            variant: 'destructive',
          });
        }

        // Try to wait for online
        const cameOnline = await waitForOnline(10000);
        if (cameOnline) {
          safeSetState({ isOffline: false });
          if (showToast) {
            toast({
              title: 'Back Online',
              description: 'Your connection has been restored.',
            });
          }
        } else {
          throw new Error('No internet connection');
        }
      }

      // Start loading
      safeSetState({ isLoading: true, error: null, isRetrying: state.retryCount > 0 });

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();
      const { signal } = abortControllerRef.current;

      try {
        // Add breadcrumb for tracking
        addBreadcrumb('API call started', 'api', 'info', {
          function: apiFn.name || 'anonymous',
          args: JSON.stringify(args).substring(0, 100),
        });

        // Make the API call with error handling
        const result = await handleApiError(
          () => apiFn(...args),
          {
            retry: retry ? retryConfig : undefined,
            timeout,
            enableQueue,
            onError: (error) => {
              safeSetState({ error });
              if (onError) {
                onError(error);
              }
            },
          }
        );

        // Success
        if (isMountedRef.current) {
          safeSetState({
            data: result,
            isLoading: false,
            error: null,
            isRetrying: false,
            retryCount: 0,
          });

          if (onSuccess) {
            onSuccess(result);
          }

          addBreadcrumb('API call succeeded', 'api', 'info');
        }

        return result;
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));

        // Update state with error
        if (isMountedRef.current) {
          safeSetState({
            isLoading: false,
            error: err,
            isRetrying: false,
          });
        }

        // Log to Sentry
        captureException(err, {
          context: 'useApiCall',
          function: apiFn.name,
          args: JSON.stringify(args).substring(0, 100),
        });

        // Show toast error
        if (showToast) {
          toast({
            title: 'Request Failed',
            description: err.message || 'An error occurred while making the request',
            variant: 'destructive',
          });
        }

        throw err;
      }
    },
    [apiFn, retry, retryConfig, timeout, enableQueue, onSuccess, onError, showToast, state.retryCount, safeSetState]
  );

  /**
   * Reset state to initial values
   */
  const reset = useCallback(() => {
    safeSetState({
      data: null,
      isLoading: false,
      error: null,
      isRetrying: false,
      retryCount: 0,
    });
  }, [safeSetState]);

  /**
   * Refetch data using the last arguments
   */
  const refetch = useCallback(async () => {
    if (lastArgsRef.current.length > 0) {
      await execute(...lastArgsRef.current);
    }
  }, [execute]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      
      // Abort any pending request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  /**
   * Monitor online/offline status
   */
  useEffect(() => {
    const handleOnline = () => {
      safeSetState({ isOffline: false });
      
      if (showToast) {
        toast({
          title: 'Back Online',
          description: 'Your connection has been restored.',
        });
      }

      // Refetch if we had an error
      if (state.error && state.data === null) {
        refetch();
      }
    };

    const handleOffline = () => {
      safeSetState({ isOffline: true });
      
      if (showToast) {
        toast({
          title: 'Offline',
          description: 'You are currently offline.',
          variant: 'destructive',
        });
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [state.error, state.data, refetch, safeSetState, showToast]);

  /**
   * Execute immediately if requested
   */
  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [immediate, execute]);

  return {
    data: state.data,
    isLoading: state.isLoading,
    error: state.error,
    isRetrying: state.isRetrying,
    retryCount: state.retryCount,
    isOffline: state.isOffline,
    execute,
    reset,
    refetch,
  };
}

// ============================================================================
// Specialized Hooks
// ============================================================================

/**
 * Hook for making API calls with manual trigger
 */
export function useLazyApiCall<T>(
  apiFn: (...args: unknown[]) => Promise<T>,
  options?: ApiCallOptions
) {
  return useApiCall(apiFn, { ...options, immediate: false });
}

/**
 * Hook for making API calls immediately on mount
 */
export function useImmediateApiCall<T>(
  apiFn: (...args: unknown[]) => Promise<T>,
  options?: ApiCallOptions
) {
  return useApiCall(apiFn, { ...options, immediate: true });
}

/**
 * Hook for polling API calls
 */
export function usePollingApiCall<T>(
  apiFn: () => Promise<T>,
  options: ApiCallOptions & { interval?: number } = {}
): UseApiCallReturn<T> {
  const { interval = 30000, ...apiOptions } = options;
  const apiCall = useApiCall(apiFn, { ...apiOptions, immediate: true });

  useEffect(() => {
    if (!apiCall.isLoading && !apiCall.error) {
      const intervalId = setInterval(() => {
        apiCall.refetch();
      }, interval);

      return () => clearInterval(intervalId);
    }
  }, [apiCall, interval]);

  return apiCall;
}

// ============================================================================
// Export
// ============================================================================

export type { ApiCallOptions, ApiCallState, UseApiCallReturn };
