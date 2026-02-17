/**
 * Unit tests for usePrediction hook
 */
import { renderHook, act, waitFor } from '@testing-library/react';
import { usePrediction } from '../../hooks/usePrediction';
import * as api from '../../services/api';

// Mock the API service
jest.mock('../../services/api');

const mockApi = api as jest.Mocked<typeof api>;

describe('usePrediction Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('predict', () => {
    test('successfully makes prediction', async () => {
      const mockPrediction = {
        id: 1,
        patient_uuid: 'test-123',
        risk_score: 0.75,
        risk_level: 'high' as const,
        confidence: 0.85,
        features_used: {},
        model_version: '1.0.0',
        prediction_timestamp: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockApi.apiService.createPrediction = jest.fn().mockResolvedValue({
        data: mockPrediction,
        status: 200,
      });

      const { result } = renderHook(() => usePrediction());

      await act(async () => {
        await result.current.predict({
          patient_uuid: 'test-123',
          features: { age: 30, gender: 'F' },
        });
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toEqual(mockPrediction);
      expect(result.current.error).toBeNull();
    });

    test('handles prediction errors', async () => {
      mockApi.apiService.createPrediction = jest.fn().mockRejectedValue(
        new Error('Prediction failed')
      );

      const { result } = renderHook(() => usePrediction());

      await act(async () => {
        try {
          await result.current.predict({
            patient_uuid: 'test-123',
            features: { age: 30, gender: 'F' },
          });
        } catch (e) {
          // Expected error
        }
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBe('Prediction failed');
      expect(result.current.data).toBeNull();
    });

    test('sets loading to true during prediction', async () => {
      let resolvePrediction: (value: any) => void;
      const predictionPromise = new Promise((resolve) => {
        resolvePrediction = resolve;
      });

      mockApi.apiService.createPrediction = jest.fn().mockReturnValue(predictionPromise);

      const { result } = renderHook(() => usePrediction());

      act(() => {
        result.current.predict({
          patient_uuid: 'test-123',
          features: { age: 30, gender: 'F' },
        });
      });

      expect(result.current.loading).toBe(true);

      await act(async () => {
        resolvePrediction!({
          data: {
            id: 1,
            patient_uuid: 'test-123',
            risk_score: 0.5,
            risk_level: 'medium' as const,
            confidence: 0.8,
            features_used: {},
            model_version: '1.0.0',
            prediction_timestamp: '2024-01-01T00:00:00Z',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          status: 200,
        });
      });
    });
  });

  describe('reset', () => {
    test('resets state to initial values', async () => {
      const { result } = renderHook(() => usePrediction());

      // Set some state
      await act(async () => {
        try {
          await result.current.predict({
            patient_uuid: 'test-123',
            features: { age: 30, gender: 'F' },
          });
        } catch (e) {
          // Ignore
        }
      });

      // Reset
      act(() => {
        result.current.reset();
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.data).toBeNull();
    });
  });

  describe('initial state', () => {
    test('has correct initial values', () => {
      const { result } = renderHook(() => usePrediction());

      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.data).toBeNull();
      expect(typeof result.current.predict).toBe('function');
      expect(typeof result.current.reset).toBe('function');
    });
  });
});
