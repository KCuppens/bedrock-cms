import { useState, useEffect, useCallback, useMemo, createContext, useContext } from 'react';
import { api } from '@/lib/api';

export interface User {
  id: string;
  email: string;
  name?: string;
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
  date_joined?: string;
}

export interface AuthContextType {
  user: User | null;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => void;
  resetPassword: (email: string) => Promise<{ success: boolean; error?: string }>;
  signUp: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const useAuthState = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session on app start
    const checkSession = async () => {
      try {
        const sessionUser = await api.auth.checkSession();
        if (sessionUser) {
          setUser(sessionUser);
        }
      } catch (error) {
        console.error('Session check failed:', error);
      } finally {
        setIsLoading(false);
      }
    };

    checkSession();
  }, []);

  const signIn = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    try {
      const response = await api.auth.login(email, password);

      if (response.user) {
        setUser(response.user);
        setIsLoading(false);
        return { success: true };
      }

      setIsLoading(false);
      return { success: false, error: response.message || 'Login failed' };
    } catch (error: any) {
      setIsLoading(false);
      return {
        success: false,
        error: error.message || 'An error occurred during login'
      };
    }
  };

  const signOut = async () => {
    try {
      await api.auth.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      // Still clear user locally even if API call fails
      setUser(null);
    }
  };

  const resetPassword = async (email: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    try {
      const response = await api.auth.resetPassword(email);
      setIsLoading(false);
      return { success: true };
    } catch (error: any) {
      setIsLoading(false);
      return {
        success: false,
        error: error.message || 'Failed to send password reset email'
      };
    }
  };

  const signUp = async (email: string, password: string, name: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    try {
      // Split name into first and last name
      const nameParts = name.trim().split(' ');
      const first_name = nameParts[0] || '';
      const last_name = nameParts.slice(1).join(' ') || '';

      const response = await api.auth.register({
        email,
        password1: password,
        password2: password,
        first_name,
        last_name,
      });

      if (response.user) {
        // After successful registration, automatically sign in
        const loginResult = await signIn(email, password);
        if (loginResult.success) {
          return { success: true };
        }
      }

      setIsLoading(false);
      return { success: true }; // Registration successful even if auto-login fails
    } catch (error: any) {
      setIsLoading(false);
      return {
        success: false,
        error: error.message || 'Registration failed'
      };
    }
  };

  return {
    user,
    signIn,
    signOut,
    resetPassword,
    signUp,
    isLoading
  };
};