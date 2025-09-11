import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useLocale } from '@/contexts/LocaleContext';

interface LocaleRedirectProps {
  children: React.ReactNode;
}

/**
 * Component that wraps legacy routes and redirects them to language-prefixed URLs
 * based on the current active locale.
 */
export const LocaleRedirect: React.FC<LocaleRedirectProps> = ({ children }) => {
  const location = useLocation();
  const { currentLocale, locales } = useLocale();
  
  // Check if current path already has a locale prefix
  const hasLocalePrefix = /^\/[a-z]{2}(\/|$)/.test(location.pathname);
  
  // If no locale prefix, redirect to prefixed version
  if (!hasLocalePrefix) {
    // Use current locale if available, otherwise use first active locale
    const targetLocale = currentLocale?.code || locales.find(l => l.is_active)?.code || 'en';
    
    // For root path, redirect to /locale
    if (location.pathname === '/') {
      return <Navigate to={`/${targetLocale}${location.search}${location.hash}`} replace />;
    }
    
    // For other paths, prefix with locale
    const newPath = `/${targetLocale}${location.pathname}`;
    return <Navigate to={newPath + location.search + location.hash} replace />;
  }
  
  // Otherwise, render children normally
  return <>{children}</>;
};