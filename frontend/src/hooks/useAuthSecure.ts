import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '@/lib/api';

export interface User {
  id: string;
  email: string;
  name?: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  is_active?: boolean;
  date_joined?: string;
}

export interface AuthContextType {
  user: User | null;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ success: boolean; error?: string }>;
  signUp: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>;
  isLoading: boolean;
  isAuthenticated: boolean;
}

// Secure session management - no localStorage for sensitive data
const SESSION_CHECK_INTERVAL = 60000; // Check session every minute

export const useAuthState = (): AuthContextType => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check session validity - stable function that doesn't recreate unnecessarily
  const checkSession = useCallback(async () => {
    try {
      const sessionUser = await api.auth.checkSession();
      if (sessionUser) {
        setUser(sessionUser);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
    } catch (error) {
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []); // Empty dependency array is correct here since we only use setters

  // Initialize auth state
  useEffect(() => {
    let mounted = true;
    let interval: NodeJS.Timeout;

    const initializeAuth = async () => {
      if (mounted) {
        await checkSession();

        // Set up periodic session checks only after initial check
        interval = setInterval(() => {
          if (mounted) {
            checkSession();
          }
        }, SESSION_CHECK_INTERVAL);
      }
    };

    initializeAuth();

    // Clean up on unmount
    return () => {
      mounted = false;
      if (interval) {
        clearInterval(interval);
      }
    };
  }, []); // Remove checkSession from dependencies to prevent infinite loop

  // Sign in with secure cookie-based auth
  const signIn = useCallback(async (
    email: string,
    password: string
  ): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    try {
      const response = await api.auth.login(email, password);

      if (response.user) {
        setUser(response.user);
        setIsAuthenticated(true);

        // Store only non-sensitive data in sessionStorage
        sessionStorage.setItem('user_info', JSON.stringify({
          id: response.user.id,
          name: response.user.name || `${response.user.first_name} ${response.user.last_name}`.trim(),
          email: response.user.email,
        }));

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
  }, []);

  // Sign out and clear session
  const signOut = useCallback(async (): Promise<void> => {
    try {
      await api.auth.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear local state
      setUser(null);
      setIsAuthenticated(false);
      sessionStorage.removeItem('user_info');
    }
  }, []);

  // Request password reset
  const resetPassword = useCallback(async (
    email: string
  ): Promise<{ success: boolean; error?: string }> => {
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
  }, []);

  // Sign up new user
  const signUp = useCallback(async (
    email: string,
    password: string,
    name: string
  ): Promise<{ success: boolean; error?: string }> => {
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
  }, [signIn]);

  // Memoize the context value to prevent unnecessary re-renders
  const value = useMemo(
    () => ({
      user,
      signIn,
      signOut,
      resetPassword,
      signUp,
      isLoading,
      isAuthenticated,
    }),
    [user, signIn, signOut, resetPassword, signUp, isLoading, isAuthenticated]
  );

  return value;
};