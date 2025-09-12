import { useState, useEffect, useCallback, useMemo } from 'react';

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface AuthContextType {
  user: User | null;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => void;
  resetPassword: (email: string) => Promise<{ success: boolean; error?: string }>;
  signUp: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>;
  isLoading: boolean;
}

// Demo users for localStorage authentication
const DEMO_USERS_KEY = 'demo_users';
const CURRENT_USER_KEY = 'current_user';

export const useAuthState = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Memoized helper functions
  const getDemoUsers = useCallback((): User[] => {
    const stored = localStorage.getItem(DEMO_USERS_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        // Handle invalid JSON
      }
    }
    // Default demo users
    const defaultUsers: User[] = [
      { id: '1', email: 'demo@example.com', name: 'Demo User' },
      { id: '2', email: 'admin@example.com', name: 'Admin User' }
    ];
    localStorage.setItem(DEMO_USERS_KEY, JSON.stringify(defaultUsers));
    return defaultUsers;
  }, []);

  const saveDemoUsers = useCallback((users: User[]) => {
    localStorage.setItem(DEMO_USERS_KEY, JSON.stringify(users));
  }, []);

  useEffect(() => {
    // Check for stored user on app start
    const storedUser = localStorage.getItem(CURRENT_USER_KEY);
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        // Handle invalid JSON
        localStorage.removeItem(CURRENT_USER_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  const signIn = useCallback(async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 800));

    const users = getDemoUsers();
    const foundUser = users.find(u => u.email === email);

    if (!foundUser) {
      setIsLoading(false);
      return { success: false, error: 'User not found' };
    }

    // For demo purposes, any password works
    if (password.length < 1) {
      setIsLoading(false);
      return { success: false, error: 'Password required' };
    }

    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(foundUser));
    setUser(foundUser);
    setIsLoading(false);

    return { success: true };
  }, [getDemoUsers]);

  const signOut = useCallback(() => {
    localStorage.removeItem(CURRENT_USER_KEY);
    setUser(null);
  }, []);

  const resetPassword = useCallback(async (email: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));

    const users = getDemoUsers();
    const foundUser = users.find(u => u.email === email);

    setIsLoading(false);

    if (!foundUser) {
      return { success: false, error: 'No account found with this email' };
    }

    // For demo purposes, always succeed
    return { success: true };
  }, [getDemoUsers]);

  const signUp = useCallback(async (email: string, password: string, name: string): Promise<{ success: boolean; error?: string }> => {
    setIsLoading(true);

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 800));

    const users = getDemoUsers();
    const existingUser = users.find(u => u.email === email);

    if (existingUser) {
      setIsLoading(false);
      return { success: false, error: 'User already exists with this email' };
    }

    const newUser: User = {
      id: Date.now().toString(),
      email,
      name
    };

    users.push(newUser);
    saveDemoUsers(users);

    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(newUser));
    setUser(newUser);
    setIsLoading(false);

    return { success: true };
  }, [getDemoUsers, saveDemoUsers]);

  // Memoize the return value to prevent unnecessary re-renders
  return useMemo(() => ({
    user,
    signIn,
    signOut,
    resetPassword,
    signUp,
    isLoading
  }), [user, signIn, signOut, resetPassword, signUp, isLoading]);
};
