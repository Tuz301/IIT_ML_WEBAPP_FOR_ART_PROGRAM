import { apiClient } from '../../services/api';
import { Patient, IITPrediction } from '../../services/api';

// Mock fetch globally
global.fetch = jest.fn() as jest.MockedFunction<typeof fetch>;

const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('ApiClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('Authentication', () => {
    it('should login successfully', async () => {
      const mockResponse = {
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await apiClient.login('testuser', 'testpass');

      expect(result.data).toEqual(mockResponse);
      expect(result.error).toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/auth/login',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ username: 'testuser', password: 'testpass' }),
        })
      );
    });

    it('should handle login failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' }),
      } as Response);

      const result = await apiClient.login('wrong', 'wrong');

      expect(result.data).toBeUndefined();
      expect(result.error).toBe('Invalid credentials');
      expect(result.status).toBe(401);
    });

    it('should refresh token', async () => {
      const mockResponse = {
        access_token: 'new-token',
        token_type: 'bearer',
        expires_in: 3600,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await apiClient.refreshToken();

      expect(result.data).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/auth/refresh',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('Patient Management', () => {
    beforeEach(() => {
      // Set auth token for protected endpoints
      apiClient.setToken('test-token');
    });

    it('should fetch patients list', async () => {
      const mockPatients = [
        {
          patient_uuid: '123',
          given_name: 'John',
          family_name: 'Doe',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ patients: mockPatients, total: 1 }),
      } as Response);

      const result = await apiClient.getPatients();

      expect(result.data?.patients).toEqual(mockPatients);
      expect(result.data?.total).toBe(1);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/patients?skip=0&limit=100',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
          }),
        })
      );
    });

    it('should create a new patient', async () => {
      const newPatient = {
        given_name: 'Jane',
        family_name: 'Smith',
        birthdate: '1990-01-01',
        gender: 'F',
      };

      const mockResponse = {
        ...newPatient,
        patient_uuid: '456',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await apiClient.createPatient(newPatient);

      expect(result.data).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/patients',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newPatient),
        })
      );
    });

    it('should update patient', async () => {
      const updates = { phone_number: '+1234567890' };
      const mockResponse = {
        patient_uuid: '123',
        given_name: 'John',
        family_name: 'Doe',
        phone_number: '+1234567890',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await apiClient.updatePatient('123', updates);

      expect(result.data).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/patients/123',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(updates),
        })
      );
    });

    it('should delete patient', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      const result = await apiClient.deletePatient('123');

      expect(result.error).toBeUndefined();
      expect(result.status).toBe(200);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/patients/123',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('Prediction Management', () => {
    beforeEach(() => {
      apiClient.setToken('test-token');
    });

    it('should create prediction', async () => {
      const predictionRequest = {
        patient_uuid: '123',
        features: { age: 30, viral_load: 1000 },
      };

      const mockResponse: IITPrediction = {
        id: 1,
        patient_uuid: '123',
        risk_score: 0.75,
        risk_level: 'high',
        confidence: 0.85,
        features_used: predictionRequest.features,
        model_version: '1.0.0',
        prediction_timestamp: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await apiClient.createPrediction(predictionRequest);

      expect(result.data).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/predictions',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(predictionRequest),
        })
      );
    });

    it('should fetch predictions with filters', async () => {
      const mockPredictions: IITPrediction[] = [
        {
          id: 1,
          patient_uuid: '123',
          risk_score: 0.75,
          risk_level: 'high',
          confidence: 0.85,
          features_used: {},
          model_version: '1.0.0',
          prediction_timestamp: '2024-01-01T00:00:00Z',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ predictions: mockPredictions, total: 1 }),
      } as Response);

      const result = await apiClient.getPredictions(0, 10, '123', 'high');

      expect(result.data?.predictions).toEqual(mockPredictions);
      expect(result.data?.total).toBe(1);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/predictions?skip=0&limit=10&patient_uuid=123&risk_level=high',
        expect.any(Object)
      );
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await apiClient.getHealth();

      expect(result.data).toBeUndefined();
      expect(result.error).toBe('Network error or server unavailable');
      expect(result.status).toBe(0);
    });

    it('should handle server errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal server error' }),
      } as Response);

      const result = await apiClient.getHealth();

      expect(result.data).toBeUndefined();
      expect(result.error).toBe('Internal server error');
      expect(result.status).toBe(500);
    });
  });

  describe('Token Management', () => {
    it('should store token in localStorage on login', async () => {
      const mockResponse = {
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      await apiClient.login('user', 'pass');

      expect(localStorage.getItem('auth_token')).toBe('test-token');
    });

    it('should clear token on logout', () => {
      apiClient.setToken('test-token');
      apiClient.logout();

      expect(localStorage.getItem('auth_token')).toBeNull();
    });

    it('should check token expiry', () => {
      // Set an expired token
      const expiredTime = Date.now() - 1000;
      localStorage.setItem('token_expiry', expiredTime.toString());

      expect(apiClient.isTokenExpired()).toBe(true);
    });
  });
});
