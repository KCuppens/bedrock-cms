import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

// Query Keys
export const redirectKeys = {
  all: ['redirects'] as const,
  lists: () => [...redirectKeys.all, 'list'] as const,
  list: (filters?: Record<string, any>) => [...redirectKeys.lists(), filters] as const,
  details: () => [...redirectKeys.all, 'detail'] as const,
  detail: (id: number) => [...redirectKeys.details(), id] as const,
};

// Types
export interface Redirect {
  id: number;
  from_path: string;
  to_path: string;
  status: number;
  is_active: boolean;
  notes?: string;
  hits: number;
  locale?: string | null;
  created_at: string;
}

export interface CreateRedirectDto {
  from_path: string;
  to_path: string;
  status: number;
  is_active?: boolean;
  notes?: string;
}

export interface UpdateRedirectDto extends CreateRedirectDto {
  id: number;
}

// Queries
export function useRedirects(filters?: { search?: string }) {
  return useQuery({
    queryKey: redirectKeys.list(filters),
    queryFn: async () => {
      const params: any = {};
      if (filters?.search) params.search = filters.search;
      
      const response = await api.redirects.list(params);
      return response.results || response.data || [];
    },
  });
}

export function useRedirect(id: number) {
  return useQuery({
    queryKey: redirectKeys.detail(id),
    queryFn: () => api.redirects.get(id),
    enabled: !!id,
  });
}

// Mutations
export function useCreateRedirect() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: CreateRedirectDto) => api.redirects.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: redirectKeys.lists() });
      toast({
        title: "Success",
        description: "Redirect created successfully.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error?.response?.data?.error || "Failed to create redirect.",
        variant: "destructive",
      });
    },
  });
}

export function useUpdateRedirect() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, ...data }: UpdateRedirectDto) => 
      api.redirects.update(id, data),
    onSuccess: (_, variables) => {
      // Defer query invalidation to avoid race conditions
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: redirectKeys.lists() });
        queryClient.invalidateQueries({ queryKey: redirectKeys.detail(variables.id) });
      }, 100);
    },
    onError: (error: any) => {
      // Error handled by UI feedback
    },
  });
}

export function useDeleteRedirect() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: number) => api.redirects.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: redirectKeys.lists() });
      toast({
        title: "Success",
        description: "Redirect deleted successfully.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error?.response?.data?.error || "Failed to delete redirect.",
        variant: "destructive",
      });
    },
  });
}

export function useTestRedirect() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: number) => api.redirects.test(id),
    onSuccess: (result) => {
      toast({
        title: result.success ? "Success" : "Test Failed",
        description: result.success 
          ? `Redirect working correctly (${result.status})` 
          : `Test failed: ${result.error || 'Unknown error'}`,
        variant: result.success ? "default" : "destructive",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: "Failed to test redirect.",
        variant: "destructive",
      });
    },
  });
}

export function useImportRedirectsCSV() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (file: File) => api.redirects.importCSV(file),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: redirectKeys.lists() });
      toast({
        title: "Import Completed",
        description: `${result.successful_imports} redirects imported successfully. ${result.failed_imports} failed.`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Import Failed",
        description: "Failed to import redirects. Please check the CSV format.",
        variant: "destructive",
      });
    },
  });
}

export function useExportRedirectsCSV() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: () => api.redirects.exportCSV(),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'redirects.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    onError: () => {
      toast({
        title: "Export Failed",
        description: "Failed to export redirects.",
        variant: "destructive",
      });
    },
  });
}