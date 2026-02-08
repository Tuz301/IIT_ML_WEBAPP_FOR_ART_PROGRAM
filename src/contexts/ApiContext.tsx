/**
 * API Context Provider for IIT ML Service
 * Manages API client state and authentication across the application
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { toast } from 'react-toastify';
import { apiClient, ApiResponse, Patient, IITPrediction, HealthResponse } from '../services/api';

interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
}

interface ApiContextType {
  // Authentication state
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // API methods
  login: (username: string, password: string) => Promise<ApiResponse>;
  logout: () => void;

  // Health check
  getHealth: () => Promise<ApiResponse<HealthResponse>>;

  // Patient methods
  getPatients: (skip?: number, limit?: number, search?: string) => Promise<ApiResponse>;
  getPatient: (uuid: string) => Promise<ApiResponse<Patient>>;
  createPatient: (patient: Omit<Patient, 'patient_uuid' | 'created_at' | 'updated_at'>) => Promise<ApiResponse<Patient>>;
  updatePatient: (uuid: string, patient: Partial<Patient>) => Promise<ApiResponse<Patient>>;
  deletePatient: (uuid: string) => Promise<ApiResponse>;

  // Prediction methods
  createPrediction: (prediction: any) => Promise<ApiResponse<IITPrediction>>;
  getPrediction: (id: number) => Promise<ApiResponse<IITPrediction>>;
  getPredictions: (params?: any) => Promise<ApiResponse>;
  batchPredictions: (request: any) => Promise<ApiResponse>;
  deletePrediction: (id: number) => Promise<ApiResponse>;
  getPredictionAnalytics: (days?: number) => Promise<ApiResponse>;

  // Feature methods
  getPatientFeatures: (patientUuid: string) => Promise<ApiResponse>;
  updatePatientFeatures: (patientUuid: string, features: Record<string, any>) => Promise<ApiResponse>;
  recalculateFeatures: (patientUuid: string) => Promise<ApiResponse>;

  // Analytics methods
  getAnalyticsOverview: (startDate?: string, endDate?: string) => Promise<ApiResponse>;
  getRiskDistribution: () => Promise<ApiResponse>;
  getTrendAnalysis: (days?: number) => Promise<ApiResponse>;

  // Admin methods
  runFullETLPipeline: (forceRefresh?: boolean) => Promise<ApiResponse>;
  ingestData: (dataSource: string, sourceType?: string, batchSize?: number) => Promise<ApiResponse>;
  processFeatures: (patientIds?: string[], forceReprocess?: boolean) => Promise<ApiResponse>;
  getETLStatus: () => Promise<ApiResponse>;
  validateDataSource: (dataSource: string, sourceType?: string) => Promise<ApiResponse>;
  createDatabaseBackup: (backupName?: string) => Promise<ApiResponse>;
  listDatabaseBackups: () => Promise<ApiResponse>;
  restoreDatabaseBackup: (backupName: string) => Promise<ApiResponse>;
  getCacheStats: () => Promise<ApiResponse>;
  invalidateAllCache: () => Promise<ApiResponse>;
  invalidatePatientCache: (patientUuid: string) => Promise<ApiResponse>;
  getSecurityAuditLogs: (params?: any) => Promise<ApiResponse>;
  getSecurityEvents: (hours?: number, severity?: string) => Promise<ApiResponse>;
  getSecurityConfig: () => Promise<ApiResponse>;
}

const ApiContext = createContext<ApiContextType | undefined>(undefined);

interface ApiProviderProps {
  children: ReactNode;
}

export const ApiProvider: React.FC<ApiProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastActivity, setLastActivity] = useState(Date.now());

  // Session timeout configuration (30 minutes)
  const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutes in milliseconds

  // Check for existing authentication on mount
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token && !apiClient.isTokenExpired()) {
      // Token exists and is not expired, validate it
      apiClient.getHealth().then(response => {
        if (response.status === 200) {
          // Token is valid, set authenticated state
          setUser({ id: 1, email: '', username: '', is_active: true, is_superuser: false });
        } else {
          // Token invalid, clear it
          apiClient.logout();
        }
      }).catch(() => {
        apiClient.logout();
      });
    } else if (token && apiClient.isTokenExpired()) {
      // Token exists but is expired, try to refresh
      apiClient.refreshToken().then(response => {
        if (response.status === 200) {
          setUser({ id: 1, email: '', username: '', is_active: true, is_superuser: false });
        } else {
          apiClient.logout();
        }
      }).catch(() => {
        apiClient.logout();
      });
    }
    setIsLoading(false);
  }, []);

  // Session timeout handler
  useEffect(() => {
    const checkSessionTimeout = () => {
      if (user && Date.now() - lastActivity > SESSION_TIMEOUT) {
        // Session expired due to inactivity
        logout();
        toast.warning('Session expired due to inactivity. Please log in again.');
      }
    };

    const interval = setInterval(checkSessionTimeout, 60000); // Check every minute
    return () => clearInterval(interval);
  }, [user, lastActivity]);

  // Activity tracker
  useEffect(() => {
    const updateActivity = () => setLastActivity(Date.now());

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    events.forEach(event => {
      document.addEventListener(event, updateActivity, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity, true);
      });
    };
  }, []);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.login(username, password);
      if (response.data?.access_token) {
        // Set mock user data - in real app, get from token or separate endpoint
        setUser({
          id: 1,
          email: username,
          username: username,
          is_active: true,
          is_superuser: username === 'admin' // Simple admin check
        });
      }
      return response;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    apiClient.logout();
    setUser(null);
  };

  const isAuthenticated = user !== null;

  // Health check
  const getHealth = () => apiClient.getHealth();

  // Patient methods
  const getPatients = (skip = 0, limit = 100, search?: string) =>
    apiClient.getPatients(skip, limit, search);

  const getPatient = (uuid: string) => apiClient.getPatient(uuid);

  const createPatient = (patient: Omit<Patient, 'patient_uuid' | 'created_at' | 'updated_at'>) =>
    apiClient.createPatient(patient);

  const updatePatient = (uuid: string, patient: Partial<Patient>) =>
    apiClient.updatePatient(uuid, patient);

  const deletePatient = (uuid: string) => apiClient.deletePatient(uuid);

  // Prediction methods
  const createPrediction = (prediction: any) => apiClient.createPrediction(prediction);

  const getPrediction = (id: number) => apiClient.getPrediction(id);

  const getPredictions = (params: any = {}) => apiClient.getPredictions(
    params.skip,
    params.limit,
    params.patient_uuid,
    params.risk_level,
    params.start_date,
    params.end_date
  );

  const batchPredictions = (request: any) => apiClient.batchPredictions(request);

  const deletePrediction = (id: number) => apiClient.deletePrediction(id);

  const getPredictionAnalytics = (days = 30) => apiClient.getPredictionAnalytics(days);

  // Feature methods
  const getPatientFeatures = (patientUuid: string) => apiClient.getPatientFeatures(patientUuid);

  const updatePatientFeatures = (patientUuid: string, features: Record<string, any>) =>
    apiClient.updatePatientFeatures(patientUuid, features);

  const recalculateFeatures = (patientUuid: string) => apiClient.recalculateFeatures(patientUuid);

  // Analytics methods
  const getAnalyticsOverview = (startDate?: string, endDate?: string) =>
    apiClient.getAnalyticsOverview(startDate, endDate);

  const getRiskDistribution = () => apiClient.getRiskDistribution();

  const getTrendAnalysis = (days = 30) => apiClient.getTrendAnalysis(days);

  // Admin methods
  const runFullETLPipeline = (forceRefresh = false) =>
    apiClient.runFullETLPipeline(forceRefresh);

  const ingestData = (dataSource: string, sourceType = 'json', batchSize = 1000) =>
    apiClient.ingestData(dataSource, sourceType, batchSize);

  const processFeatures = (patientIds?: string[], forceReprocess = false) =>
    apiClient.processFeatures(patientIds, forceReprocess);

  const getETLStatus = () => apiClient.getETLStatus();

  const validateDataSource = (dataSource: string, sourceType = 'json') =>
    apiClient.validateDataSource(dataSource, sourceType);

  const createDatabaseBackup = (backupName?: string) => apiClient.createDatabaseBackup(backupName);

  const listDatabaseBackups = () => apiClient.listDatabaseBackups();

  const restoreDatabaseBackup = (backupName: string) =>
    apiClient.restoreDatabaseBackup(backupName);

  const getCacheStats = () => apiClient.getCacheStats();

  const invalidateAllCache = () => apiClient.invalidateAllCache();

  const invalidatePatientCache = (patientUuid: string) =>
    apiClient.invalidatePatientCache(patientUuid);

  const getSecurityAuditLogs = (params: any = {}) =>
    apiClient.getSecurityAuditLogs(
      params.limit,
      params.offset,
      params.eventType,
      params.userId
    );

  const getSecurityEvents = (hours = 24, severity?: string) =>
    apiClient.getSecurityEvents(hours, severity);

  const getSecurityConfig = () => apiClient.getSecurityConfig();

  const value: ApiContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    getHealth,
    getPatients,
    getPatient,
    createPatient,
    updatePatient,
    deletePatient,
    createPrediction,
    getPrediction,
    getPredictions,
    batchPredictions,
    deletePrediction,
    getPredictionAnalytics,
    getPatientFeatures,
    updatePatientFeatures,
    recalculateFeatures,
    getAnalyticsOverview,
    getRiskDistribution,
    getTrendAnalysis,
    runFullETLPipeline,
    ingestData,
    processFeatures,
    getETLStatus,
    validateDataSource,
    createDatabaseBackup,
    listDatabaseBackups,
    restoreDatabaseBackup,
    getCacheStats,
    invalidateAllCache,
    invalidatePatientCache,
    getSecurityAuditLogs,
    getSecurityEvents,
    getSecurityConfig,
  };

  return (
    <ApiContext.Provider value={value}>
      {children}
    </ApiContext.Provider>
  );
};

export const useApi = (): ApiContextType => {
  const context = useContext(ApiContext);
  if (context === undefined) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
};
