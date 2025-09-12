import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Debounce hook that delays updating a value until after a delay
 */
export function useDebounce<T>(value: T, delay: number): T {
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
}

/**
 * Debounced callback hook that delays function execution
 * Uses useRef to maintain stable callback reference and avoid recreation
 */
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<NodeJS.Timeout>();
  const callbackRef = useRef(callback);

  // Update callback ref without causing re-renders
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Create stable debounced function that never changes
  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
    },
    [delay] // Only delay in deps, not callback
  ) as T;

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return debouncedCallback;
}

/**
 * Hook for debounced auto-save functionality
 */
export function useDebouncedAutoSave<T>(
  data: T,
  saveFunction: (data: T) => Promise<void>,
  delay: number = 1000,
  enabled: boolean = true
) {
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [lastSavedData, setLastSavedData] = useState<T>(data);
  const saveTimeoutRef = useRef<NodeJS.Timeout>();

  // Track if data has changed
  useEffect(() => {
    const hasChanges = JSON.stringify(data) !== JSON.stringify(lastSavedData);
    setHasUnsavedChanges(hasChanges);
  }, [data, lastSavedData]);

  // Debounced save effect
  useEffect(() => {
    if (!enabled || !hasUnsavedChanges) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      setIsSaving(true);
      try {
        await saveFunction(data);
        setLastSavedData(data);
        setHasUnsavedChanges(false);
      } catch (error) {
        console.error('Auto-save failed:', error);
      } finally {
        setIsSaving(false);
      }
    }, delay);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [data, saveFunction, delay, enabled, hasUnsavedChanges]);

  // Manual save function
  const saveNow = useCallback(async () => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    if (!hasUnsavedChanges) return;

    setIsSaving(true);
    try {
      await saveFunction(data);
      setLastSavedData(data);
      setHasUnsavedChanges(false);
    } catch (error) {
      console.error('Manual save failed:', error);
      throw error;
    } finally {
      setIsSaving(false);
    }
  }, [data, saveFunction, hasUnsavedChanges]);

  // Cancel pending save
  const cancelSave = useCallback(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
  }, []);

  return {
    isSaving,
    hasUnsavedChanges,
    saveNow,
    cancelSave
  };
}
