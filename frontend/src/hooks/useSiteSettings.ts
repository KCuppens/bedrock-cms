import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useLocale } from '@/contexts/LocaleContext';

export interface MenuItem {
  id: number;
  title: string;
  slug: string;
  path: string;
  position: number;
  parent?: number | null;
  children?: MenuItem[];
}

export interface SiteSettings {
  homepage: {
    id: number;
    title: string;
    slug: string;
    path: string;
  } | null;
  navigation: MenuItem[];
  footer: MenuItem[];
}

export const useSiteSettings = () => {
  const [siteSettings, setSiteSettings] = useState<SiteSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { currentLocale } = useLocale();

  useEffect(() => {
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 10000); // 10 second timeout

    const fetchSiteSettings = async () => {
      try {
        setLoading(true);
        setError(null);

        // Add locale parameter if available, otherwise use default 'en'
        const localeCode = currentLocale?.code || 'en';
        const params = { locale: localeCode };

        console.log('🔄 [useSiteSettings] Fetching site settings with locale:', localeCode);
        console.log('🔄 [useSiteSettings] Current locale object:', currentLocale);
        console.log('🔄 [useSiteSettings] API Base URL:', import.meta.env.VITE_API_URL);
        console.log('🔄 [useSiteSettings] Full URL will be:', `${import.meta.env.VITE_API_URL || ''}/api/v1/cms/site-settings/`);
        console.log('🔄 [useSiteSettings] Params:', params);

        const response = await api.request({
          method: 'GET',
          url: '/api/v1/cms/site-settings/',
          params,
          signal: abortController.signal
        });

        // Check if request was aborted
        if (abortController.signal.aborted) return;

        console.log('✅ [useSiteSettings] Raw response:', response);
        console.log('✅ [useSiteSettings] Response type:', typeof response);
        console.log('✅ [useSiteSettings] Response keys:', Object.keys(response || {}));
        console.log('✅ [useSiteSettings] Navigation from response:', response?.navigation);
        console.log('✅ [useSiteSettings] Navigation items count:', response?.navigation?.length || 0);

        setSiteSettings(response);
      } catch (err: any) {
        // Don't show error if request was aborted
        if (err.name === 'AbortError' || abortController.signal.aborted) {
          console.log('🚫 [useSiteSettings] Request aborted');
          return;
        }

        console.error('❌ [useSiteSettings] Failed to fetch site settings:', err);
        console.error('❌ [useSiteSettings] Error details:', err.response?.data);
        setError(err.response?.data?.detail || 'Failed to load site settings');
      } finally {
        if (!abortController.signal.aborted) {
          setLoading(false);
        }
        clearTimeout(timeoutId);
      }
    };

    console.log('🎯 [useSiteSettings] useEffect triggered, currentLocale:', currentLocale);
    // Fetch immediately, don't wait for currentLocale
    fetchSiteSettings();

    return () => {
      abortController.abort();
      clearTimeout(timeoutId);
    };
  }, [currentLocale]);

  return { siteSettings, loading, error };
};

export const useNavigation = () => {
  const [navigation, setNavigation] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { currentLocale } = useLocale();

  useEffect(() => {
    const fetchNavigation = async () => {
      try {
        setLoading(true);
        setError(null);

        // Add locale parameter if available, otherwise use default 'en'
        const localeCode = currentLocale?.code || 'en';
        const params = { locale: localeCode };
        const response = await api.request({
          method: 'GET',
          url: '/api/v1/cms/navigation/',
          params
        });
        setNavigation(response.data.menu_items || []);
      } catch (err: any) {
        console.error('Failed to fetch navigation:', err);
        setError(err.response?.data?.detail || 'Failed to load navigation');
      } finally {
        setLoading(false);
      }
    };

    // Fetch immediately, don't wait for currentLocale
    fetchNavigation();
  }, [currentLocale]);

  return { navigation, loading, error };
};

export const useFooterMenu = () => {
  const [footer, setFooter] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { currentLocale } = useLocale();

  useEffect(() => {
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), 10000); // 10 second timeout

    const fetchFooter = async () => {
      try {
        setLoading(true);
        setError(null);

        // Add locale parameter if available, otherwise use default 'en'
        const localeCode = currentLocale?.code || 'en';
        const params = { locale: localeCode };

        console.log('🔄 [useFooterMenu] Fetching footer with locale:', localeCode);

        const response = await api.request({
          method: 'GET',
          url: '/api/v1/cms/footer/',
          params,
          signal: abortController.signal
        });

        // Check if request was aborted
        if (abortController.signal.aborted) return;

        console.log('✅ [useFooterMenu] Footer response:', response.data);
        setFooter(response.data?.footer_items || []);
      } catch (err: any) {
        // Don't show error if request was aborted
        if (err.name === 'AbortError' || abortController.signal.aborted) {
          console.log('🚫 [useFooterMenu] Request aborted');
          return;
        }

        console.error('❌ [useFooterMenu] Failed to fetch footer menu:', err);
        setError(err.response?.data?.detail || 'Failed to load footer menu');
      } finally {
        if (!abortController.signal.aborted) {
          setLoading(false);
        }
        clearTimeout(timeoutId);
      }
    };

    console.log('🎯 [useFooterMenu] useEffect triggered, currentLocale:', currentLocale);
    // Fetch immediately, don't wait for currentLocale
    fetchFooter();

    return () => {
      abortController.abort();
      clearTimeout(timeoutId);
    };
  }, [currentLocale]);

  return { footer, loading, error };
};