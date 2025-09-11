import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { api } from '@/lib/api';
import { useLocale } from './LocaleContext';
import type { TranslationBundle, TranslationContextType, TranslationKey, TranslationProviderProps } from '@/types/translations';

const TranslationContext = createContext<TranslationContextType | undefined>(undefined);

// Translation key registry for build-time extraction
export const TRANSLATION_REGISTRY = new Map<string, TranslationKey>();

// Normalize locale codes: en-US -> en, fr-FR -> fr, etc.
const normalizeLocale = (locale: string) => {
  // If locale has a dash, take only the language part
  return locale.split('-')[0].toLowerCase();
};

export const TranslationProvider: React.FC<TranslationProviderProps> = ({
  children,
  locale: overrideLocale,
  fallbackLocale = 'en',
  enableAutoSync = true,
  syncInterval = 30000, // 30 seconds
  reportMissing = true
}) => {
  const { currentLocale } = useLocale();
  
  const rawLocale = overrideLocale || currentLocale?.code || fallbackLocale;
  const activeLocale = normalizeLocale(rawLocale);
  
  const [translations, setTranslations] = useState<TranslationBundle>({});
  const [isLoading, setIsLoading] = useState(false); // Start as false to allow non-blocking render
  const [missingKeys] = useState<Set<string>>(new Set());
  
  const pendingKeys = useRef<Map<string, TranslationKey>>(new Map());
  const syncTimer = useRef<NodeJS.Timeout | null>(null);
  const lastSyncTime = useRef<number>(0);

  // Fetch translation bundle for current locale
  const fetchTranslations = useCallback(async () => {
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 5000); // 5 second timeout
    
    try {
      setIsLoading(true);
      
      // Check localStorage cache first
      const cacheKey = `translations_${activeLocale}`;
      const cached = localStorage.getItem(cacheKey);
      const cacheTimestamp = localStorage.getItem(`${cacheKey}_timestamp`);
      
      // Use cache if less than 1 hour old
      if (cached && cacheTimestamp && (Date.now() - parseInt(cacheTimestamp)) < 3600000) {
        const cachedTranslations = JSON.parse(cached);
        setTranslations(cachedTranslations);
        setIsLoading(false);
        clearTimeout(timeoutId);
        return;
      }
      
      // Load basic fallback translations immediately to avoid blocking UI
      const basicTranslations = {
        'common.loading': 'Loading...',
        'common.error': 'Error',
        'common.save': 'Save',
        'common.cancel': 'Cancel',
        'common.delete': 'Delete',
        'common.edit': 'Edit',
        'navigation.home': 'Home',
        'navigation.blog': 'Blog',
        'navigation.about': 'About',
        'navigation.contact': 'Contact'
      };
      setTranslations(basicTranslations);
      
      const response = await api.request<TranslationBundle>({
        method: 'GET',
        url: `/api/v1/i18n/ui-messages/bundle/${activeLocale}/`,
        signal: abortController.signal
      });
      
      // Check if request was aborted
      if (abortController.signal.aborted) return;
      
      // Cache the response with size management
      try {
        // Manage cache size - keep only last 5 locales to prevent unlimited growth
        const MAX_CACHED_LOCALES = 5;
        const allCacheKeys = Object.keys(localStorage).filter(key => 
          key.startsWith('translations_') && key.endsWith('_timestamp')
        );
        
        if (allCacheKeys.length >= MAX_CACHED_LOCALES) {
          // Sort by timestamp and remove oldest entries
          const sortedKeys = allCacheKeys
            .map(key => ({
              key: key.replace('_timestamp', ''),
              timestamp: parseInt(localStorage.getItem(key) || '0')
            }))
            .sort((a, b) => a.timestamp - b.timestamp);
          
          // Remove oldest cache entries
          const toRemove = sortedKeys.slice(0, sortedKeys.length - MAX_CACHED_LOCALES + 1);
          toRemove.forEach(({ key }) => {
            localStorage.removeItem(key);
            localStorage.removeItem(`${key}_timestamp`);
          });
        }
        
        localStorage.setItem(cacheKey, JSON.stringify(response));
        localStorage.setItem(`${cacheKey}_timestamp`, Date.now().toString());
      } catch (cacheError) {
        // Cache error - continue without caching
      }
      
      // Merge fetched translations with basic ones
      setTranslations(prevTranslations => ({
        ...prevTranslations,
        ...response
      }));
    } catch (error: any) {
      // Don't show error if request was aborted
      if (error.name === 'AbortError' || abortController.signal.aborted) {
        return;
      }
      
      console.error('Failed to fetch translations:', error);
      
      // Try fallback locale if current fails
      const normalizedFallback = normalizeLocale(fallbackLocale);
      if (activeLocale !== normalizedFallback) {
        try {
          const fallbackResponse = await api.request<TranslationBundle>({
            method: 'GET',
            url: `/api/v1/i18n/ui-messages/bundle/${normalizedFallback}/`,
            signal: abortController.signal
          });
          
          if (!abortController.signal.aborted) {
            setTranslations(fallbackResponse);
          }
        } catch (fallbackError) {
          if (fallbackError.name !== 'AbortError' && !abortController.signal.aborted) {
            console.error('Failed to fetch fallback translations:', fallbackError);
          }
        }
      }
    } finally {
      if (!abortController.signal.aborted) {
        setIsLoading(false);
      }
      clearTimeout(timeoutId);
    }
    
    return () => {
      abortController.abort();
      clearTimeout(timeoutId);
    };
  }, [activeLocale, fallbackLocale]);

  // Sync pending keys with backend
  const syncKeys = useCallback(async () => {
    if (pendingKeys.current.size === 0) return;
    
    const now = Date.now();
    if (now - lastSyncTime.current < 5000) return; // Debounce 5 seconds
    
    const keysToSync = Array.from(pendingKeys.current.values());
    pendingKeys.current.clear();
    lastSyncTime.current = now;

    try {
      // Use non-blocking request with timeout
      await api.request({
        method: 'POST',
        url: '/api/v1/i18n/ui-messages/sync-keys/',
        data: { 
          keys: keysToSync,
          source: 'runtime-discovery'
        },
        signal: AbortSignal.timeout(3000) // 3 second timeout
      });
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to sync translation keys:', error);
        // Re-add keys to pending if sync fails
        keysToSync.forEach(key => {
          pendingKeys.current.set(key.key, key);
        });
      }
    }
  }, []);

  // Report missing keys (runtime detection)
  const reportMissingKeys = useCallback(async () => {
    if (missingKeys.size === 0 || !reportMissing) return;
    
    const keys = Array.from(missingKeys);
    missingKeys.clear();

    try {
      // Use non-blocking request with timeout
      await api.request({
        method: 'POST',
        url: '/api/v1/i18n/ui-messages/report-missing/',
        data: {
          keys,
          locale: activeLocale,
          url: window.location.pathname,
          component: 'unknown'
        },
        signal: AbortSignal.timeout(3000) // 3 second timeout
      });
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to report missing keys:', error);
      }
    }
  }, [missingKeys, activeLocale, reportMissing]);

  // Register a translation key
  const registerKey = useCallback((keyData: TranslationKey) => {
    TRANSLATION_REGISTRY.set(keyData.key, keyData);
    
    if (enableAutoSync && !translations[keyData.key]) {
      pendingKeys.current.set(keyData.key, keyData);
      
      // Schedule sync
      if (syncTimer.current) {
        clearTimeout(syncTimer.current);
      }
      syncTimer.current = setTimeout(syncKeys, syncInterval);
    }
  }, [translations, enableAutoSync, syncKeys, syncInterval]);

  // Translation function
  const t = useCallback((key: string, defaultValue?: string): string => {
    const translation = translations[key];
    
    if (!translation) {
      const fallback = defaultValue || key;
      
      // Track missing key with size limit to prevent memory leaks
      if (!missingKeys.has(key)) {
        // Limit missing keys set size to prevent memory issues
        const MAX_MISSING_KEYS = 1000;
        if (missingKeys.size >= MAX_MISSING_KEYS) {
          // Clear oldest half when limit reached
          const keysArray = Array.from(missingKeys);
          const toKeep = keysArray.slice(keysArray.length / 2);
          missingKeys.clear();
          toKeep.forEach(k => missingKeys.add(k));
        }
        
        missingKeys.add(key);
        
        // Missing translation detected in dev mode
        
        // Auto-register if not already registered
        if (enableAutoSync && !TRANSLATION_REGISTRY.has(key)) {
          registerKey({
            key,
            defaultValue: fallback,
            description: `Auto-detected from usage`,
            namespace: key.split('.')[0] || 'general'
          });
        }
      }
      
      return fallback;
    }
    
    return translation;
  }, [translations, missingKeys, enableAutoSync, registerKey]);

  // Load translations on mount and locale change
  useEffect(() => {
    let cleanup: (() => void) | undefined;
    
    const loadTranslations = async () => {
      cleanup = await fetchTranslations();
    };
    
    loadTranslations();
    
    return () => {
      if (cleanup) cleanup();
    };
  }, [fetchTranslations]);

  // Periodic sync of pending keys
  useEffect(() => {
    if (!enableAutoSync) return;
    
    const interval = setInterval(syncKeys, syncInterval);
    return () => clearInterval(interval);
  }, [enableAutoSync, syncKeys, syncInterval]);

  // Report missing keys periodically
  useEffect(() => {
    if (!reportMissing) return;
    
    const interval = setInterval(reportMissingKeys, 60000); // Every minute
    return () => clearInterval(interval);
  }, [reportMissing, reportMissingKeys]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (syncTimer.current) {
        clearTimeout(syncTimer.current);
      }
      // Final sync on unmount
      syncKeys();
      reportMissingKeys();
    };
  }, [syncKeys, reportMissingKeys]);

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo(() => ({
    t,
    locale: activeLocale,
    isLoading,
    missingKeys,
    registerKey
  }), [t, activeLocale, isLoading, missingKeys, registerKey]);

  return (
    <TranslationContext.Provider value={contextValue}>
      {children}
    </TranslationContext.Provider>
  );
};

export const useTranslation = () => {
  const context = useContext(TranslationContext);
  if (!context) {
    throw new Error('useTranslation must be used within TranslationProvider');
  }
  return context;
};