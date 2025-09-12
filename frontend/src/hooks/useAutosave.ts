import { useEffect, useRef, useCallback, useState } from 'react';
import { useDebounce } from '@/hooks/useDebounce';

export interface AutosaveState {
  lastSaved: Date | null;
  isSaving: boolean;
  hasUnsavedChanges: boolean;
  error: string | null;
  status: 'idle' | 'saving' | 'saved' | 'error';
}

interface UseAutosaveOptions {
  /** Auto-save interval in milliseconds (default: 30000 = 30 seconds) */
  interval?: number;
  /** Debounce delay in milliseconds (default: 2000 = 2 seconds) */
  debounceDelay?: number;
  /** Enable/disable autosave (default: true) */
  enabled?: boolean;
  /** Maximum number of retries on failure (default: 3) */
  maxRetries?: number;
  /** Custom key for localStorage (optional) */
  storageKey?: string;
}

export const useAutosave = <T extends Record<string, any>>(
  data: T,
  saveFunction: (data: T) => Promise<void>,
  options: UseAutosaveOptions = {}
): AutosaveState => {
  const {
    interval = 30000, // 30 seconds
    debounceDelay = 2000, // 2 seconds
    enabled = true,
    maxRetries = 3,
    storageKey
  } = options;

  const [autosaveState, setAutosaveState] = useState<AutosaveState>({
    lastSaved: null,
    isSaving: false,
    hasUnsavedChanges: false,
    error: null,
    status: 'idle'
  });

  const previousDataRef = useRef<T>(data);
  const retryCountRef = useRef(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isComponentMountedRef = useRef(true);

  // Debounced version of the data to avoid excessive saves
  const debouncedData = useDebounce(data, debounceDelay);

  // Save to localStorage for recovery
  const saveToLocalStorage = useCallback((dataToSave: T) => {
    if (storageKey && typeof window !== 'undefined') {
      try {
        localStorage.setItem(storageKey, JSON.stringify({
          data: dataToSave,
          timestamp: new Date().toISOString(),
          version: '1.0'
        }));
      } catch (error) {
        console.warn('Failed to save to localStorage:', error);
      }
    }
  }, [storageKey]);

  // Clear localStorage
  const clearLocalStorage = useCallback(() => {
    if (storageKey && typeof window !== 'undefined') {
      localStorage.removeItem(storageKey);
    }
  }, [storageKey]);

  // Recover from localStorage
  const recoverFromLocalStorage = useCallback((): T | null => {
    if (storageKey && typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(storageKey);
        if (stored) {
          const parsed = JSON.parse(stored);
          return parsed.data as T;
        }
      } catch (error) {
        console.warn('Failed to recover from localStorage:', error);
      }
    }
    return null;
  }, [storageKey]);

  // Perform the actual save
  const performSave = useCallback(async (dataToSave: T): Promise<void> => {
    if (!isComponentMountedRef.current) return;

    setAutosaveState(prev => ({
      ...prev,
      isSaving: true,
      status: 'saving',
      error: null
    }));

    try {
      await saveFunction(dataToSave);

      if (!isComponentMountedRef.current) return;

      setAutosaveState(prev => ({
        ...prev,
        isSaving: false,
        lastSaved: new Date(),
        hasUnsavedChanges: false,
        error: null,
        status: 'saved'
      }));

      // Clear localStorage after successful save
      clearLocalStorage();
      retryCountRef.current = 0;

    } catch (error: any) {
      if (!isComponentMountedRef.current) return;

      const errorMessage = error?.message || 'Auto-save failed';

      setAutosaveState(prev => ({
        ...prev,
        isSaving: false,
        error: errorMessage,
        status: 'error'
      }));

      // Save to localStorage as backup
      saveToLocalStorage(dataToSave);

      // Retry logic
      if (retryCountRef.current < maxRetries) {
        retryCountRef.current++;
        setTimeout(() => {
          if (isComponentMountedRef.current) {
            performSave(dataToSave);
          }
        }, Math.pow(2, retryCountRef.current) * 1000); // Exponential backoff
      }
    }
  }, [saveFunction, maxRetries, saveToLocalStorage, clearLocalStorage]);

  // Check if data has changed
  const hasDataChanged = useCallback((newData: T, oldData: T): boolean => {
    return JSON.stringify(newData) !== JSON.stringify(oldData);
  }, []);

  // Effect to handle data changes
  useEffect(() => {
    if (!enabled) return;

    const currentData = debouncedData;
    const previousData = previousDataRef.current;

    if (hasDataChanged(currentData, previousData)) {
      setAutosaveState(prev => ({
        ...prev,
        hasUnsavedChanges: true,
        status: prev.status === 'saved' ? 'idle' : prev.status
      }));

      // Save to localStorage immediately for recovery
      saveToLocalStorage(currentData);

      // Trigger auto-save
      performSave(currentData);
    }

    previousDataRef.current = currentData;
  }, [debouncedData, enabled, hasDataChanged, saveToLocalStorage, performSave]);

  // Interval-based auto-save (fallback)
  useEffect(() => {
    if (!enabled) return;

    intervalRef.current = setInterval(() => {
      if (autosaveState.hasUnsavedChanges && !autosaveState.isSaving) {
        performSave(data);
      }
    }, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [enabled, interval, data, autosaveState.hasUnsavedChanges, autosaveState.isSaving, performSave]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isComponentMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    ...autosaveState,
    // Helper methods (could be exposed if needed)
    // recoverFromLocalStorage,
    // clearLocalStorage
  };
};

// Hook for debouncing values
const useDebounceHook = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

// Export the debounce hook if it doesn't exist
export const useDebounce = useDebounceHook;
