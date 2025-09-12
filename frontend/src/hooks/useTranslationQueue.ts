import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface LocaleSummary {
  locale: {
    code: string;
    name: string;
    native_name: string;
  };
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  rejected: number;
  assigned: number;
  overdue: number;
  completion_percentage: number;
  priority_breakdown: {
    urgent: number;
    high: number;
    medium: number;
    low: number;
  };
}

interface TranslationQueueSummary {
  overall: {
    total: number;
    pending: number;
    in_progress: number;
    completed: number;
    overdue: number;
    completion_percentage: number;
  };
  locales: LocaleSummary[];
}

export const useTranslationQueueSummary = () => {
  return useQuery<TranslationQueueSummary>({
    queryKey: ['translationQueueSummary'],
    queryFn: () => api.request({ method: 'GET', url: '/api/v1/i18n/translations/queue/summary/' }),
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes instead of every minute
    refetchOnWindowFocus: false,
    staleTime: 2 * 60 * 1000, // Consider data stale after 2 minutes
  });
};
