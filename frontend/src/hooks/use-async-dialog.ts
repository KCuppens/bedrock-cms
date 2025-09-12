import { useState, useCallback } from 'react';

interface UseAsyncDialogState<T> {
  isOpen: boolean;
  isLoading: boolean;
  data: T | null;
}

interface UseAsyncDialogReturn<T> {
  isOpen: boolean;
  isLoading: boolean;
  data: T | null;
  open: (data?: T) => void;
  close: () => void;
  executeAsync: (asyncFn: () => Promise<void>, options?: ExecuteOptions) => Promise<void>;
  setData: (data: T | null) => void;
}

interface ExecuteOptions {
  closeOnSuccess?: boolean;
  onSuccess?: () => void;
  onError?: (error: any) => void;
  delayClose?: number;
}

/**
 * Custom hook for managing dialog state with async operations
 * Handles the common pattern of opening a dialog, performing an async operation,
 * and closing the dialog without causing React state update issues
 */
export function useAsyncDialog<T = any>(
  initialData: T | null = null
): UseAsyncDialogReturn<T> {
  const [state, setState] = useState<UseAsyncDialogState<T>>({
    isOpen: false,
    isLoading: false,
    data: initialData,
  });

  const open = useCallback((data?: T) => {
    setState({
      isOpen: true,
      isLoading: false,
      data: data ?? null,
    });
  }, []);

  const close = useCallback(() => {
    // Defer the close to avoid React batching issues
    setTimeout(() => {
      setState({
        isOpen: false,
        isLoading: false,
        data: null,
      });
    }, 0);
  }, []);

  const setData = useCallback((data: T | null) => {
    setState(prev => ({ ...prev, data }));
  }, []);

  const executeAsync = useCallback(async (
    asyncFn: () => Promise<void>,
    options: ExecuteOptions = {}
  ) => {
    const {
      closeOnSuccess = true,
      onSuccess,
      onError,
      delayClose = 0
    } = options;

    setState(prev => ({ ...prev, isLoading: true }));

    try {
      await asyncFn();

      if (closeOnSuccess) {
        // Defer state updates to avoid React batching issues
        setTimeout(() => {
          setState({
            isOpen: false,
            isLoading: false,
            data: null,
          });
          onSuccess?.();
        }, delayClose);
      } else {
        setState(prev => ({ ...prev, isLoading: false }));
        onSuccess?.();
      }
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }));
      onError?.(error);
    }
  }, []);

  return {
    isOpen: state.isOpen,
    isLoading: state.isLoading,
    data: state.data,
    open,
    close,
    executeAsync,
    setData,
  };
}

// Example usage:
/*
const MyComponent = () => {
  const editDialog = useAsyncDialog<Item>();
  const deleteDialog = useAsyncDialog<Item>();

  const handleEdit = async () => {
    await editDialog.executeAsync(
      async () => {
        await api.update(editDialog.data.id, formData);
        toast.success('Updated successfully');
      },
      {
        onSuccess: () => loadItems(),
        onError: (error) => toast.error('Update failed'),
        delayClose: 100
      }
    );
  };

  return (
    <>
      <Dialog open={editDialog.isOpen} onOpenChange={(open) => !open && editDialog.close()}>
        <DialogContent>
          <Button onClick={handleEdit} disabled={editDialog.isLoading}>
            {editDialog.isLoading ? 'Updating...' : 'Update'}
          </Button>
        </DialogContent>
      </Dialog>
    </>
  );
};
*/
