import { useRef, useEffect, useCallback, useState } from 'react';

interface UseFormAutoSaveOptions {
  delay?: number;
  enabled?: boolean;
}

interface UseFormAutoSaveReturn {
  isSaving: boolean;
  hasUnsavedChanges: boolean;
  saveNow: () => Promise<void>;
  cancelSave: () => void;
}

/**
 * Robust form auto-save hook with proper debouncing
 * Prevents multiple API calls and database locks
 */
export function useFormAutoSave<T>(
  data: T,
  saveFunction: (data: T) => Promise<void>,
  options: UseFormAutoSaveOptions = {}
): UseFormAutoSaveReturn {
  const { delay = 1000, enabled = true } = options;

  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [lastSavedData, setLastSavedData] = useState<string>('');

  const timeoutRef = useRef<NodeJS.Timeout>();
  const saveFunctionRef = useRef(saveFunction);
  const isInitializedRef = useRef(false);
  const abortControllerRef = useRef<AbortController>();

  // Update save function ref without causing re-renders
  useEffect(() => {
    saveFunctionRef.current = saveFunction;
  }, [saveFunction]);

  // Initialize last saved data on first render
  useEffect(() => {
    if (!isInitializedRef.current) {
      const serializedData = JSON.stringify(data);
      setLastSavedData(serializedData);
      setHasUnsavedChanges(false);
      isInitializedRef.current = true;
    }
  }, [data]);

  // Cancel previous save operation
  const cancelSave = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  // Perform the actual save
  const performSave = useCallback(async (dataToSave: T) => {
    if (isSaving) return;

    const serializedData = JSON.stringify(dataToSave);

    // Don't save if data hasn't actually changed
    if (serializedData === lastSavedData) {
      setHasUnsavedChanges(false);
      return;
    }

    // Cancel any pending save
    cancelSave();

    // Create new abort controller for this request
    abortControllerRef.current = new AbortController();

    setIsSaving(true);
    try {
      await saveFunctionRef.current(dataToSave);

      // Only update if this request wasn't aborted
      if (!abortControllerRef.current.signal.aborted) {
        setLastSavedData(serializedData);
        setHasUnsavedChanges(false);
      }
    } catch (error) {
      // Only handle error if request wasn't aborted
      if (!abortControllerRef.current.signal.aborted) {
        console.error('Auto-save failed:', error);
        throw error;
      }
    } finally {
      if (!abortControllerRef.current.signal.aborted) {
        setIsSaving(false);
      }
    }
  }, [isSaving, lastSavedData, cancelSave]);

  // Debounced save function
  const debouncedSave = useCallback((dataToSave: T) => {
    if (!enabled) return;

    // Cancel any pending save
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      performSave(dataToSave);
    }, delay);
  }, [enabled, delay, performSave]);

  // Manual save function
  const saveNow = useCallback(async () => {
    if (!enabled) return;

    // Cancel debounced save
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    await performSave(data);
  }, [enabled, data, performSave]);

  // Track data changes and trigger debounced save
  useEffect(() => {
    if (!enabled || !isInitializedRef.current) return;

    const serializedData = JSON.stringify(data);
    const hasChanges = serializedData !== lastSavedData;

    setHasUnsavedChanges(hasChanges);

    if (hasChanges) {
      debouncedSave(data);
    }
  }, [data, enabled, lastSavedData, debouncedSave]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelSave();
    };
  }, [cancelSave]);

  return {
    isSaving,
    hasUnsavedChanges,
    saveNow,
    cancelSave
  };
}