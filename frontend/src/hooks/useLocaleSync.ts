import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useLocale } from '@/contexts/LocaleContext';

/**
 * Hook to synchronize URL locale parameter with locale context.
 * This ensures that when users visit URLs with locale prefixes like /en/about or /fr/about,
 * the application's locale context is updated to match the URL.
 */
export const useLocaleSync = () => {
  const { locale: urlLocale } = useParams<{ locale?: string }>();
  const { currentLocale, setCurrentLocale, locales } = useLocale();

  useEffect(() => {
    if (urlLocale && urlLocale !== currentLocale?.code) {
      // Check if the URL locale is valid and active
      const isValidLocale = locales.some(locale => locale.code === urlLocale && locale.is_active);
      if (isValidLocale) {
        const targetLocale = locales.find(locale => locale.code === urlLocale);
        if (targetLocale) {
          setCurrentLocale(targetLocale);
        }
      }
    }
  }, [urlLocale, currentLocale?.code, locales, setCurrentLocale]);

  return { urlLocale, currentLocale };
};