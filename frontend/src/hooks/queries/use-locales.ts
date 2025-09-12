import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export interface Locale {
  id: number;
  code: string;
  name: string;
  native_name: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// Fetch all locales
export const useLocales = () => {
  return useQuery<Locale[]>({
    queryKey: ['locales'],
    queryFn: async () => {
      try {
        // Use the API client's request method directly
        const response = await (api as any).request({
          method: 'GET',
          url: '/api/v1/i18n/locales/'
        });
        // Handle paginated response - extract results array
        const result = response.results || response;
        return result;
      } catch (error) {
        throw error;
      }
    },
    retry: 1,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Fetch single locale
export const useLocale = (id: number) => {
  return useQuery<Locale>({
    queryKey: ['locales', id],
    queryFn: async () => {
      const response = await api.get(`/api/v1/i18n/locales/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
};

// Create locale
export const useCreateLocale = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: Partial<Locale>) => {
      const response = await api.post('/api/v1/i18n/locales/', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locales'] });
      toast({
        title: 'Success',
        description: 'Locale created successfully',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error?.response?.data?.detail || 'Failed to create locale',
        variant: 'destructive',
      });
    },
  });
};

// Update locale
export const useUpdateLocale = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ id, ...data }: Partial<Locale> & { id: number }) => {
      const response = await api.patch(`/api/v1/i18n/locales/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locales'] });
      toast({
        title: 'Success',
        description: 'Locale updated successfully',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error?.response?.data?.detail || 'Failed to update locale',
        variant: 'destructive',
      });
    },
  });
};

// Delete locale
export const useDeleteLocale = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/v1/i18n/locales/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locales'] });
      toast({
        title: 'Success',
        description: 'Locale deleted successfully',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error?.response?.data?.detail || 'Failed to delete locale',
        variant: 'destructive',
      });
    },
  });
};

// Toggle locale active status
export const useToggleLocaleStatus = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ id, is_active }: { id: number; is_active: boolean }) => {
      const response = await api.patch(`/api/v1/i18n/locales/${id}/`, { is_active });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locales'] });
      toast({
        title: 'Success',
        description: 'Locale status updated successfully',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error?.response?.data?.detail || 'Failed to update locale status',
        variant: 'destructive',
      });
    },
  });
};

// Set default locale
export const useSetDefaultLocale = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post(`/api/v1/i18n/locales/${id}/set-default/`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['locales'] });
      toast({
        title: 'Success',
        description: 'Default locale updated successfully',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error?.response?.data?.detail || 'Failed to set default locale',
        variant: 'destructive',
      });
    },
  });
};
