import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient, UserProfile } from '../services/api';
import { toast } from 'react-toastify';

// Use UserProfile from api.ts for consistency
type User = UserProfile;

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  /**
   * Fetch current user profile from backend
   * This replaces mock data with real user information
   */
  const fetchUserProfile = async (): Promise<User | null> => {
    try {
      const response = await apiClient.getCurrentUser();
      if (response.status === 200 && response.data) {
        return response.data as User;
      }
      return null;
    } catch (error) {
      console.error('Failed to fetch user profile:', error);
      return null;
    }
  };

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      const response = await apiClient.login(username, password);
      
      if (response.status === 200 && response.data?.access_token) {
        // User profile is included in login response
        if (response.data.user) {
          setUser(response.data.user);
          toast.success(`Welcome back, ${response.data.user.username}!`);
          return true;
        }
        
        // Fallback: Fetch user profile separately
        const userProfile = await fetchUserProfile();
        
        if (userProfile) {
          setUser(userProfile);
          toast.success(`Welcome back, ${userProfile.username}!`);
          return true;
        }
        
        // Should not reach here with proper backend
        toast.error('Failed to retrieve user profile');
        return false;
      } else {
        toast.error(response.error || 'Login failed');
        return false;
      }
    } catch (error) {
      console.error('Login error:', error);
      toast.error('Login failed. Please try again.');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await apiClient.logout();
      setUser(null);
      toast.info('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      // Clear local state even if backend call fails
      setUser(null);
    }
  };

  const checkAuth = async () => {
    try {
      setIsLoading(true);
      
      // Check if we have a valid token (in localStorage or cookie)
      const token = localStorage.getItem('auth_token');
      
      if (token && !apiClient.isTokenExpired()) {
        // Token exists and is not expired, validate it with API
        const userProfile = await fetchUserProfile();
        
        if (userProfile) {
          setUser(userProfile);
        } else {
          // Token invalid, clear it
          await logout();
        }
      } else if (token && apiClient.isTokenExpired()) {
        // Token exists but is expired, try to refresh
        const refreshResponse = await apiClient.refreshToken();
        
        if (refreshResponse.status === 200) {
          const userProfile = await fetchUserProfile();
          if (userProfile) {
            setUser(userProfile);
          } else {
            await logout();
          }
        } else {
          await logout();
        }
      }
    } catch (error) {
      console.error('Auth check error:', error);
      await logout();
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUser = async () => {
    const userProfile = await fetchUserProfile();
    if (userProfile) {
      setUser(userProfile);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    checkAuth,
    refreshUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
