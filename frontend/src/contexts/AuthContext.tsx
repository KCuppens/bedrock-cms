import React, { createContext, useContext, memo } from 'react';
import { AuthContextType, useAuthState } from '@/hooks/useAuthSecure';

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Memoize AuthProvider to prevent unnecessary re-renders
export const AuthProvider = memo<{ children: React.ReactNode }>(({ children }) => {
  const authState = useAuthState();

  return (
    <AuthContext.Provider value={authState}>
      {children}
    </AuthContext.Provider>
  );
});