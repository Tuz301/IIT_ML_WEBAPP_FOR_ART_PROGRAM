/**
 * Shared Type Definitions
 * 
 * This file contains all shared type definitions used across the application.
 * All types should be defined here to ensure consistency and avoid duplication.
 */

// ============================================================================
// User & Authentication Types
// ============================================================================

/**
 * User profile matching backend User model
 * This is the single source of truth for user types across the app
 */
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

/**
 * Token response from authentication endpoints
 */
export interface TokenResponseData {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

/**
 * Authentication context state
 */
export interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  lastActivity?: number;
}

// ============================================================================
// API Response Types
// ============================================================================

/**
 * Standard API response wrapper
 */
export interface ApiResponse<T = unknown> {
  data?: T;
  error?: string;
  status: number;
  message?: string;
  detail?: string;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

// ============================================================================
// Patient Types
// ============================================================================

/**
 * Patient entity matching backend Patient model
 */
export interface Patient {
  patient_uuid: string;
  datim_id?: string;
  pepfar_id?: string;
  given_name?: string;
  family_name?: string;
  birthdate?: string;
  gender?: 'M' | 'F' | 'Other';
  state_province?: string;
  city_village?: string;
  phone_number?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * Patient creation payload
 */
export type CreatePatientPayload = Omit<
  Patient,
  'patient_uuid' | 'created_at' | 'updated_at'
>;

/**
 * Patient update payload
 */
export type UpdatePatientPayload = Partial<CreatePatientPayload>;

// ============================================================================
// Prediction Types
// ============================================================================

/**
 * Risk levels for IIT predictions
 */
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

/**
 * IIT Prediction entity
 */
export interface IITPrediction {
  id: number;
  patient_uuid: string;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  features_used: Record<string, unknown>;
  model_version: string;
  prediction_timestamp: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Prediction request payload
 */
export interface PredictionRequest {
  patient_uuid: string;
  features: Record<string, unknown>;
}

/**
 * Batch prediction request
 */
export interface BatchPredictionRequest {
  predictions: PredictionRequest[];
}

/**
 * Batch prediction response
 */
export interface BatchPredictionResponse {
  successful_predictions: IITPrediction[];
  failed_predictions: Array<{
    patient_uuid: string;
    error: string;
  }>;
  total_processed: number;
  total_failed: number;
}

// ============================================================================
// Analytics Types
// ============================================================================

/**
 * Dashboard statistics
 */
export interface DashboardStats {
  totalPredictions: number;
  highRiskPatients: number;
  mediumRiskPatients: number;
  lowRiskPatients: number;
  criticalRiskPatients: number;
  predictionsToday: number;
  predictionsThisWeek: number;
  predictionsThisMonth: number;
}

/**
 * Risk distribution data
 */
export interface RiskDistribution {
  low_risk: number;
  low_risk_percentage: number;
  medium_risk: number;
  medium_risk_percentage: number;
  high_risk: number;
  high_risk_percentage: number;
  critical_risk: number;
  critical_risk_percentage: number;
}

/**
 * Trend analysis data point
 */
export interface TrendDataPoint {
  date: string;
  total: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  critical_risk: number;
}

// ============================================================================
// Health & System Types
// ============================================================================

/**
 * Health check response
 */
export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  service: string;
  version: string;
  timestamp: string;
  uptime_seconds: number;
  model_loaded?: boolean;
  redis_connected?: boolean;
  database_connected?: boolean;
}

// ============================================================================
// Feature Types
// ============================================================================

/**
 * Patient feature set
 */
export interface PatientFeatures {
  patient_uuid: string;
  features: Record<string, unknown>;
  calculated_at: string;
  version: number;
}

/**
 * Feature calculation result
 */
export interface FeatureCalculationResult {
  success: boolean;
  features?: Record<string, unknown>;
  error?: string;
  calculated_at: string;
}

// ============================================================================
// Error Types
// ============================================================================

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Network error
 */
export class NetworkError extends Error {
  constructor(message: string, public originalError?: unknown) {
    super(message);
    this.name = 'NetworkError';
  }
}

/**
 * Authentication error
 */
export class AuthError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = 'AuthError';
  }
}

/**
 * Validation error
 */
export class ValidationError extends Error {
  constructor(
    message: string,
    public field?: string,
    public value?: unknown
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}

// ============================================================================
// Form Types
// ============================================================================

/**
 * Form state interface
 */
export interface FormState<T> {
  data: T;
  errors: Partial<Record<keyof T, string>>;
  touched: Partial<Record<keyof T, boolean>>;
  isSubmitting: boolean;
  isValid: boolean;
}

/**
 * Form field configuration
 */
export interface FieldConfig<T> {
  name: keyof T;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'textarea' | 'checkbox';
  required?: boolean;
  placeholder?: string;
  options?: Array<{ value: string; label: string }>;
  validation?: (value: unknown) => string | undefined;
}

// ============================================================================
// Component Props Types
// ============================================================================

/**
 * Loading state props
 */
export interface LoadingProps {
  isLoading: boolean;
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

/**
 * Error display props
 */
export interface ErrorDisplayProps {
  error: Error | string | null;
  onRetry?: () => void;
  onDismiss?: () => void;
}

/**
 * Empty state props
 */
export interface EmptyStateProps {
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  icon?: React.ReactNode;
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Make specific properties optional
 */
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/**
 * Make specific properties required
 */
export type RequiredBy<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;

/**
 * Deep partial type
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Async function return type
 */
export type AsyncReturnType<T extends (...args: unknown[]) => Promise<unknown>> =
  T extends (...args: unknown[]) => Promise<infer R> ? R : never;

// ============================================================================
// Export all types
// ============================================================================

export type {
  // Re-export commonly used types for convenience
  UserProfile as User,
  TokenResponseData as TokenResponse,
  ApiResponse as APIResponse,
  IITPrediction as Prediction,
};
