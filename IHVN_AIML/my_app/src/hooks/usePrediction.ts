// src/hooks/usePrediction.ts - UPDATED
import { useState, useCallback } from 'react';
import { apiService, PredictionRequest, IITPrediction } from '../services/api';

interface PredictionState {
  loading: boolean;
  error: string | null;
  data: IITPrediction | null;
}

export const usePrediction = () => {
  const [state, setState] = useState<PredictionState>({
    loading: false,
    error: null,
    data: null,
  });

  const predict = useCallback(async (requestData: PredictionRequest) => {
    setState({ loading: true, error: null, data: null });

    try {
      const result = await apiService.createPrediction(requestData);
      setState({ loading: false, error: null, data: result.data || null });
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Prediction failed';
      setState({ loading: false, error: message, data: null });
      throw err;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ loading: false, error: null, data: null });
  }, []);

  return {
    predict,
    reset,
    ...state,
  };
};