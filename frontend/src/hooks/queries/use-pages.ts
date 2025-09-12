import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';

// Query Keys
export const pageKeys = {
  all: ['pages'] as const,
  lists: () => [...pageKeys.all, 'list'] as const,
  list: (filters?: Record<string, any>) => [...pageKeys.lists(), filters] as const,
  details: () => [...pageKeys.all, 'detail'] as const,
  detail: (id: string | number) => [...pageKeys.details(), id] as const,
};

// Types
export interface Page {
  id: string;
  title: string;
  slug: string;
  path: string;
  parent?: string | null;
  locale: string;
  status: 'draft' | 'published' | 'scheduled' | 'pending_review' | 'approved' | 'rejected';
  blocks?: any[];
  seo?: any;
  in_main_menu: boolean;
  in_footer: boolean;
  is_homepage: boolean;
  published_at?: string;
  updated_at: string;
  created_at: string;
  position?: number;
}

export interface CreatePageDto {
  title: string;
  slug: string;
  parent?: string | null;
  locale: string;
  status?: string;
  blocks?: any[];
  seo?: any;
  in_main_menu?: boolean;
  in_footer?: boolean;
  is_homepage?: boolean;
}

export interface UpdatePageDto extends Partial<CreatePageDto> {
  id: string | number;
}

// Queries
export function usePages(filters?: { locale?: string; status?: string; search?: string }) {
  return useQuery({
    queryKey: pageKeys.list(filters),
    queryFn: async () => {
      const params: any = {};
      if (filters?.locale) params.locale = filters.locale;
      if (filters?.status) params.status = filters.status;
      if (filters?.search) params.search = filters.search;

      const response = await api.cms.pages.list(params);
      return response.results || response.data || [];
    },
  });
}

export function usePage(id: string | number) {
  return useQuery({
    queryKey: pageKeys.detail(id),
    queryFn: () => api.cms.pages.get(id),
    enabled: !!id,
  });
}

// Mutations
export function useCreatePage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreatePageDto) => api.cms.pages.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pageKeys.lists() });
      toast.success('Page created successfully');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.error || 'Failed to create page');
    },
  });
}

export function useUpdatePage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...data }: UpdatePageDto) =>
      api.cms.pages.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: pageKeys.lists() });
      queryClient.invalidateQueries({ queryKey: pageKeys.detail(variables.id) });
      toast.success('Page updated successfully');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.error || 'Failed to update page');
    },
  });
}

export function useDeletePage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string | number) => api.cms.pages.delete(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: pageKeys.lists() });
      queryClient.removeQueries({ queryKey: pageKeys.detail(id) });
      toast.success('Page deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.error || 'Failed to delete page');
    },
  });
}

export function useDuplicatePage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string | number) => api.cms.pages.duplicate(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: pageKeys.lists() });
      const duplicatedPage = data.data || data;
      if (duplicatedPage?.title) {
        toast.success(`Page duplicated as "${duplicatedPage.title}"`);
      } else {
        toast.success('Page duplicated successfully');
      }
      return duplicatedPage;
    },
    onError: (error: any) => {
      toast.error('Failed to duplicate page');
    },
  });
}

export function usePublishPage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string | number) => api.cms.pages.publish(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: pageKeys.lists() });
      queryClient.invalidateQueries({ queryKey: pageKeys.detail(id) });
      toast.success('Page published successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to publish page');
    },
  });
}

export function useUnpublishPage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string | number) => api.cms.pages.unpublish(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: pageKeys.lists() });
      queryClient.invalidateQueries({ queryKey: pageKeys.detail(id) });
      toast.success('Page unpublished successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to unpublish page');
    },
  });
}

export function useReorderPages() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { pageId: string; newParentId?: string; newPosition: number }) =>
      api.cms.pages.reorder(data.pageId, data.newParentId, data.newPosition),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pageKeys.lists() });
      toast.success('Page order updated');
    },
    onError: (error: any) => {
      toast.error('Failed to update page order');
    },
  });
}
