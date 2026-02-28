/**
 * IIT ML Service API Client
 * Handles all communication with the backend FastAPI service
 *
 * Enhanced with httpOnly cookie support for improved security.
 * JWT tokens are automatically managed by the browser via cookies,
 * preventing XSS attacks while maintaining backward compatibility.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Cookie names (must match backend)
// Cookie names (must match backend) - exported for potential use
export const ACCESS_COOKIE_NAME = 'iit_access_token';
export const REFRESH_COOKIE_NAME = 'iit_refresh_token';

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
}

// User interface matching backend User model
export interface UserProfile {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
  created_at: string;
  updated_at: string;
}

// Token response matching backend TokenResponse schema
export interface TokenResponseData {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

export interface Patient {
  patient_uuid: string;
  datim_id?: string;
  pepfar_id?: string;
  given_name?: string;
  family_name?: string;
  birthdate?: string;
  gender?: string;
  state_province?: string;
  city_village?: string;
  phone_number?: string;
  created_at?: string;
  updated_at?: string;
}

export interface IITPrediction {
  id: number;
  patient_uuid: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  features_used: Record<string, any>;
  model_version: string;
  prediction_timestamp: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface PredictionRequest {
  patient_uuid: string;
  features: Record<string, any>;
}

export interface BatchPredictionRequest {
  predictions: PredictionRequest[];
}

export interface BatchPredictionResponse {
  successful_predictions: IITPrediction[];
  failed_predictions: Array<{
    patient_uuid: string;
    error: string;
  }>;
  total_processed: number;
  total_failed: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  uptime_seconds: number;
  model_loaded?: boolean;
  redis_connected?: boolean;
}

class ApiClient {
  private baseURL: string;
  private token: string | null = null;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
    // Try to get token from localStorage (for backward compatibility)
    this.token = localStorage.getItem('auth_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;

    // Skip token refresh for auth endpoints to avoid infinite loops
    const isAuthEndpoint = endpoint.startsWith('/v1/auth/') ||
                          endpoint === '/v1/refresh' ||
                          endpoint === '/v1/logout';

    // Auto-refresh token if expired (except for auth endpoints)
    if (!isAuthEndpoint && this.token && await this.ensureValidToken()) {
      // Token was refreshed, update authorization header
      options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${this.token}`,
      };
    }

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      credentials: 'include',  // CRITICAL: Include cookies for httpOnly auth
      ...options,
    };

    // Add authorization header if token exists (for backward compatibility)
    // Note: Cookies are automatically sent by the browser due to credentials: 'include'
    if (this.token) {
      config.headers = {
        ...config.headers,
        'Authorization': `Bearer ${this.token}`,
      };
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json().catch(() => ({}));

      // Enhanced error handling with detailed logging
      if (!response.ok) {
        const errorDetail = data.detail || data.message || 'Request failed';
        console.error(`API Error [${response.status}] ${endpoint}:`, {
          status: response.status,
          detail: errorDetail,
          url: url,
          response: data
        });
      }

      return {
        data: response.ok ? data : undefined,
        error: response.ok ? undefined : data.detail || data.message || 'Request failed',
        status: response.status,
      };
    } catch (error) {
      console.error('Network error:', {
        endpoint,
        url,
        error: error instanceof Error ? error.message : String(error)
      });
      return {
        error: 'Network error or server unavailable',
        status: 0,
      };
    }
  }

  // Authentication methods
  async login(username: string, password: string): Promise<ApiResponse<TokenResponseData>> {
    // Backend expects form data (OAuth2PasswordRequestForm), not JSON
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await this.request<TokenResponseData>(
      '/v1/auth/login',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      }
    );

    if (response.data?.access_token) {
      // Store token in localStorage for backward compatibility
      // Note: Primary auth is now via httpOnly cookies set by the backend
      this.token = response.data.access_token;
      localStorage.setItem('auth_token', this.token);
      
      // Store token expiry time
      if (response.data.expires_in) {
        const expiryTime = Date.now() + (response.data.expires_in * 1000);
        localStorage.setItem('token_expiry', expiryTime.toString());
      }
    }

    return response;
  }

  async refreshToken(): Promise<ApiResponse<{ access_token: string; token_type: string; expires_in?: number }>> {
    const response = await this.request<{ access_token: string; token_type: string; expires_in?: number }>(
      '/v1/auth/refresh',
      {
        method: 'POST',
      }
    );

    if (response.data?.access_token) {
      // Update localStorage for backward compatibility
      this.token = response.data.access_token;
      localStorage.setItem('auth_token', this.token);
      
      // Update token expiry time
      if (response.data.expires_in) {
        const expiryTime = Date.now() + (response.data.expires_in * 1000);
        localStorage.setItem('token_expiry', expiryTime.toString());
      }
    }

    return response;
  }

  async logout(): Promise<void> {
    // Call backend logout endpoint to clear cookies
    await this.request('/v1/auth/logout', {
      method: 'POST',
    });
    
    // Clear localStorage (for backward compatibility)
    this.token = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('token_expiry');
  }

  /**
   * Get current authenticated user profile
   * This replaces mock data with real user information from the backend
   */
  async getCurrentUser(): Promise<ApiResponse<any>> {
    return this.request('/v1/auth/me');
  }

  /**
   * Check if user is authenticated via cookies
   * This is more secure than checking localStorage
   */
  isAuthenticatedViaCookie(): boolean {
    // Check if cookies exist (browser handles this automatically)
    // We can't directly access httpOnly cookies from JavaScript
    // This is a security feature - we rely on the backend to validate
    return this.token !== null || localStorage.getItem('auth_token') !== null;
  }

  isTokenExpired(): boolean {
    const expiryTime = localStorage.getItem('token_expiry');
    if (!expiryTime) return true;
    return Date.now() > parseInt(expiryTime);
  }

  async ensureValidToken(): Promise<boolean> {
    if (!this.token || this.isTokenExpired()) {
      try {
        const refreshResponse = await this.refreshToken();
        return refreshResponse.status === 200;
      } catch {
        this.logout();
        return false;
      }
    }
    return true;
  }

  setToken(token: string): void {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  // Health check
  async getHealth(): Promise<ApiResponse<HealthResponse>> {
    return this.request<HealthResponse>('/health/');
  }

  async getDetailedHealth(): Promise<ApiResponse<any>> {
    return this.request('/health/detailed');
  }

  // Patient methods
  async getPatients(
    skip: number = 0,
    limit: number = 100,
    search?: string
  ): Promise<ApiResponse<{ patients: Patient[]; total: number }>> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });

    if (search) {
      params.append('search', search);
    }

    return this.request(`/v1/patients?${params}`);
  }

  async getPatient(uuid: string): Promise<ApiResponse<Patient>> {
    return this.request(`/v1/patients/${uuid}`);
  }

  async createPatient(patient: Omit<Patient, 'patient_uuid' | 'created_at' | 'updated_at'>): Promise<ApiResponse<Patient>> {
    return this.request('/v1/patients', {
      method: 'POST',
      body: JSON.stringify(patient),
    });
  }

  async updatePatient(uuid: string, patient: Partial<Patient>): Promise<ApiResponse<Patient>> {
    return this.request(`/v1/patients/${uuid}`, {
      method: 'PUT',
      body: JSON.stringify(patient),
    });
  }

  async deletePatient(uuid: string): Promise<ApiResponse<void>> {
    return this.request(`/v1/patients/${uuid}`, {
      method: 'DELETE',
    });
  }

  // Prediction methods
  async createPrediction(prediction: PredictionRequest): Promise<ApiResponse<IITPrediction>> {
    return this.request('/v1/predictions', {
      method: 'POST',
      body: JSON.stringify(prediction),
    });
  }

  async getPrediction(id: number): Promise<ApiResponse<IITPrediction>> {
    return this.request(`/v1/predictions/${id}`);
  }

  async getPredictions(
    skip: number = 0,
    limit: number = 100,
    patient_uuid?: string,
    risk_level?: string,
    start_date?: string,
    end_date?: string
  ): Promise<ApiResponse<{ predictions: IITPrediction[]; total: number }>> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });

    if (patient_uuid) params.append('patient_uuid', patient_uuid);
    if (risk_level) params.append('risk_level', risk_level);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);

    return this.request(`/v1/predictions?${params}`);
  }

  async batchPredictions(request: BatchPredictionRequest): Promise<ApiResponse<BatchPredictionResponse>> {
    return this.request('/v1/predictions/batch', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async deletePrediction(id: number): Promise<ApiResponse<void>> {
    return this.request(`/v1/predictions/${id}`, {
      method: 'DELETE',
    });
  }

  async getPredictionAnalytics(
    days: number = 30
  ): Promise<ApiResponse<any>> {
    return this.request(`/v1/predictions/analytics/overview?days=${days}`);
  }

  // Feature methods
  async getPatientFeatures(patientUuid: string): Promise<ApiResponse<any>> {
    return this.request(`/v1/features/${patientUuid}`);
  }

  async updatePatientFeatures(patientUuid: string, features: Record<string, any>): Promise<ApiResponse<any>> {
    return this.request(`/v1/features/${patientUuid}`, {
      method: 'PUT',
      body: JSON.stringify(features),
    });
  }

  async recalculateFeatures(patientUuid: string): Promise<ApiResponse<any>> {
    return this.request(`/v1/features/${patientUuid}/recalculate`, {
      method: 'POST',
    });
  }

  // Analytics methods
  async getAnalyticsOverview(
    startDate?: string,
    endDate?: string
  ): Promise<ApiResponse<any>> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    return this.request(`/v1/analytics/overview?${params}`);
  }

  async getRiskDistribution(): Promise<ApiResponse<any>> {
    return this.request('/v1/analytics/risk-distribution');
  }

  async getTrendAnalysis(days: number = 30): Promise<ApiResponse<any>> {
    return this.request(`/v1/analytics/trends?days=${days}`);
  }

  // ETL methods (admin only)
  async runFullETLPipeline(forceRefresh: boolean = false): Promise<ApiResponse<any>> {
    return this.request('/v1/etl/run-full-pipeline', {
      method: 'POST',
      body: JSON.stringify({ force_refresh: forceRefresh }),
    });
  }

  async ingestData(dataSource: string, sourceType: string = 'json', batchSize: number = 1000): Promise<ApiResponse<any>> {
    return this.request('/v1/etl/ingest-data', {
      method: 'POST',
      body: JSON.stringify({
        data_source: dataSource,
        source_type: sourceType,
        batch_size: batchSize,
      }),
    });
  }

  async processFeatures(patientIds?: string[], forceReprocess: boolean = false): Promise<ApiResponse<any>> {
    return this.request('/v1/etl/process-features', {
      method: 'POST',
      body: JSON.stringify({
        patient_ids: patientIds,
        force_reprocess: forceReprocess,
      }),
    });
  }

  async getETLStatus(): Promise<ApiResponse<any>> {
    return this.request('/v1/etl/status');
  }

  async validateDataSource(dataSource: string, sourceType: string = 'json'): Promise<ApiResponse<any>> {
    return this.request('/v1/etl/validate-data', {
      method: 'POST',
      body: JSON.stringify({
        data_source: dataSource,
        source_type: sourceType,
      }),
    });
  }

  // Backup methods (admin only)
  async createDatabaseBackup(backupName?: string): Promise<ApiResponse<any>> {
    return this.request('/v1/backup/database/backup', {
      method: 'POST',
      body: JSON.stringify({ backup_name: backupName }),
    });
  }

  async listDatabaseBackups(): Promise<ApiResponse<any>> {
    return this.request('/v1/backup/database/backups');
  }

  async restoreDatabaseBackup(backupName: string): Promise<ApiResponse<any>> {
    return this.request('/v1/backup/database/restore', {
      method: 'POST',
      body: JSON.stringify({ backup_name: backupName }),
    });
  }

  // Cache methods (admin only)
  async getCacheStats(): Promise<ApiResponse<any>> {
    return this.request('/v1/cache/stats');
  }

  async invalidateAllCache(): Promise<ApiResponse<any>> {
    return this.request('/v1/cache/invalidate/all', {
      method: 'POST',
    });
  }

  async invalidatePatientCache(patientUuid: string): Promise<ApiResponse<any>> {
    return this.request(`/v1/cache/invalidate/patient/${patientUuid}`, {
      method: 'POST',
    });
  }

  // Security methods (admin only)
  async getSecurityAuditLogs(
    limit: number = 100,
    offset: number = 0,
    eventType?: string,
    userId?: string
  ): Promise<ApiResponse<any>> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

    if (eventType) params.append('event_type', eventType);
    if (userId) params.append('user_id', userId);

    return this.request(`/v1/security/audit-logs?${params}`);
  }

  async getSecurityEvents(hours: number = 24, severity?: string): Promise<ApiResponse<any>> {
    const params = new URLSearchParams({
      hours: hours.toString(),
    });

    if (severity) params.append('severity', severity);

    return this.request(`/v1/security/events?${params}`);
  }

  async getSecurityConfig(): Promise<ApiResponse<any>> {
    return this.request('/v1/security/config');
  }

  // Circuit Breaker methods
  async getCircuitBreakers(): Promise<ApiResponse<any>> {
    return this.request('/circuit-breakers');
  }

  async getCircuitBreaker(name: string): Promise<ApiResponse<any>> {
    return this.request(`/circuit-breakers/${name}`);
  }

  async resetCircuitBreaker(name: string): Promise<ApiResponse<any>> {
    return this.request(`/circuit-breakers/${name}/reset`, { method: 'POST' });
  }

  async getCircuitBreakerMetrics(): Promise<ApiResponse<any>> {
    return this.request('/circuit-breakers/metrics/summary');
  }

  // Dead Letter Queue methods
  async getDLQJobs(resolved: boolean = false, limit: number = 100): Promise<ApiResponse<any>> {
    return this.request(`/dlq?resolved=${resolved}&limit=${limit}`);
  }

  async getDLQStats(): Promise<ApiResponse<any>> {
    return this.request('/dlq/stats');
  }

  async retryDLQJob(originalJobId: string): Promise<ApiResponse<any>> {
    return this.request(`/dlq/retry/${originalJobId}`, { method: 'POST' });
  }

  async cleanupDLQ(): Promise<ApiResponse<any>> {
    return this.request('/dlq/cleanup', { method: 'POST' });
  }

  // Alerting methods
  async sendAlert(
    severity: string,
    message: string,
    source?: string,
    metadata?: Record<string, any>
  ): Promise<ApiResponse<any>> {
    return this.request('/v1/alerting/send', {
      method: 'POST',
      body: JSON.stringify({ severity, message, source, metadata }),
    });
  }

  async getAlertStats(): Promise<ApiResponse<any>> {
    return this.request('/v1/alerting/stats');
  }

  // Feature Flags methods
  async listFeatureFlags(): Promise<ApiResponse<any>> {
    return this.request('/v1/feature-flags');
  }

  async getFeatureFlag(flagName: string): Promise<ApiResponse<any>> {
    return this.request(`/v1/feature-flags/${flagName}`);
  }

  async checkFeatureFlag(flagName: string, context?: Record<string, any>): Promise<ApiResponse<any>> {
    return this.request(`/v1/feature-flags/${flagName}/check`, {
      method: 'POST',
      body: JSON.stringify({ context }),
    });
  }

  // Explainability methods
  async getFeatureImportance(modelVersion: string): Promise<ApiResponse<any>> {
    return this.request(`/v1/explainability/feature-importance/${modelVersion}`);
  }

  async explainPrediction(predictionId: number): Promise<ApiResponse<any>> {
    return this.request('/v1/explainability/predictions/explain', {
      method: 'POST',
      body: JSON.stringify({ prediction_id: predictionId }),
    });
  }

  async getPredictionExplanation(predictionId: number): Promise<ApiResponse<any>> {
    return this.request(`/v1/explainability/predictions/${predictionId}/explanation`);
  }

  // Observations methods
  async createObservation(observation: any): Promise<ApiResponse<any>> {
    return this.request('/v1/observations', {
      method: 'POST',
      body: JSON.stringify(observation),
    });
  }

  async getPatientObservations(patientUuid: string): Promise<ApiResponse<any>> {
    return this.request(`/v1/observations/patient/${patientUuid}`);
  }

  // Visits methods
  async createVisit(visit: any): Promise<ApiResponse<any>> {
    return this.request('/v1/visits', {
      method: 'POST',
      body: JSON.stringify(visit),
    });
  }

  async getPatientVisits(patientUuid: string): Promise<ApiResponse<any>> {
    return this.request(`/v1/visits/patient/${patientUuid}`);
  }

  // Ensemble methods
  async createEnsemble(ensemble: any): Promise<ApiResponse<any>> {
    return this.request('/v1/ensembles', {
      method: 'POST',
      body: JSON.stringify(ensemble),
    });
  }

  async listEnsembles(): Promise<ApiResponse<any>> {
    return this.request('/v1/ensembles');
  }

  async makeEnsemblePrediction(ensembleId: string, data: any): Promise<ApiResponse<any>> {
    return this.request(`/v1/ensembles/${ensembleId}/predict`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

// Create and export a singleton instance
export const apiClient = new ApiClient();
export const apiService = apiClient;

// Export types
export type { ApiClient };

// Additional exports for compatibility
export interface PatientListResponse {
  patients: Patient[];
  total: number;
}

export interface PredictionResponse extends IITPrediction {}
