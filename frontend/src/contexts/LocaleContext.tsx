import { createContext, useContext, useState, useEffect, useMemo, useCallback, ReactNode } from 'react';
import { api } from '@/lib/api';
import {
  getBrowserLanguages,
  matchBrowserToLocale,
  isFirstVisit,
  markAutoDetected
} from '@/utils/browserLanguage';

interface Locale {
  id: number;
  code: string;
  name: string;
  native_name: string;
  is_active: boolean;
  is_default: boolean;
  fallback?: number;
  rtl: boolean;
  flag?: string;
}

interface LocaleContextType {
  locales: Locale[];
  activeLocales: Locale[];
  currentLocale: Locale | null;
  defaultLocale: Locale | null;
  loading: boolean;
  setCurrentLocale: (locale: Locale) => void;
  getLocaleByCode: (code: string) => Locale | undefined;
  refreshLocales: () => Promise<void>;
}

const LocaleContext = createContext<LocaleContextType | undefined>(undefined);

const LOCALE_FLAGS: Record<string, string> = {
  'en': '🇺🇸',
  'en-US': '🇺🇸',
  'en-GB': '🇬🇧',
  'es': '🇪🇸',
  'es-ES': '🇪🇸',
  'es-MX': '🇲🇽',
  'fr': '🇫🇷',
  'fr-FR': '🇫🇷',
  'fr-CA': '🇨🇦',
  'de': '🇩🇪',
  'de-DE': '🇩🇪',
  'de-CH': '🇨🇭',
  'de-AT': '🇦🇹',
  'it': '🇮🇹',
  'it-IT': '🇮🇹',
  'pt': '🇵🇹',
  'pt-PT': '🇵🇹',
  'pt-BR': '🇧🇷',
  'ru': '🇷🇺',
  'ru-RU': '🇷🇺',
  'zh': '🇨🇳',
  'zh-CN': '🇨🇳',
  'zh-TW': '🇹🇼',
  'ja': '🇯🇵',
  'ja-JP': '🇯🇵',
  'ko': '🇰🇷',
  'ko-KR': '🇰🇷',
  'ar': '🇸🇦',
  'ar-SA': '🇸🇦',
  'ar-AE': '🇦🇪',
  'ar-EG': '🇪🇬',
  'he': '🇮🇱',
  'he-IL': '🇮🇱',
  'hi': '🇮🇳',
  'hi-IN': '🇮🇳',
  'pl': '🇵🇱',
  'pl-PL': '🇵🇱',
  'nl': '🇳🇱',
  'nl-NL': '🇳🇱',
  'nl-BE': '🇧🇪',
  'sv': '🇸🇪',
  'sv-SE': '🇸🇪',
  'no': '🇳🇴',
  'nb': '🇳🇴',
  'nb-NO': '🇳🇴',
  'da': '🇩🇰',
  'da-DK': '🇩🇰',
  'fi': '🇫🇮',
  'fi-FI': '🇫🇮',
  'tr': '🇹🇷',
  'tr-TR': '🇹🇷',
  'el': '🇬🇷',
  'el-GR': '🇬🇷',
  'uk': '🇺🇦',
  'uk-UA': '🇺🇦',
  'cs': '🇨🇿',
  'cs-CZ': '🇨🇿',
  'hu': '🇭🇺',
  'hu-HU': '🇭🇺',
  'ro': '🇷🇴',
  'ro-RO': '🇷🇴',
  'bg': '🇧🇬',
  'bg-BG': '🇧🇬',
  'hr': '🇭🇷',
  'hr-HR': '🇭🇷',
  'sr': '🇷🇸',
  'sr-RS': '🇷🇸',
  'sk': '🇸🇰',
  'sk-SK': '🇸🇰',
  'sl': '🇸🇮',
  'sl-SI': '🇸🇮',
  'et': '🇪🇪',
  'et-EE': '🇪🇪',
  'lv': '🇱🇻',
  'lv-LV': '🇱🇻',
  'lt': '🇱🇹',
  'lt-LT': '🇱🇹',
  'th': '🇹🇭',
  'th-TH': '🇹🇭',
  'vi': '🇻🇳',
  'vi-VN': '🇻🇳',
  'id': '🇮🇩',
  'id-ID': '🇮🇩',
  'ms': '🇲🇾',
  'ms-MY': '🇲🇾',
  'tl': '🇵🇭',
  'fil': '🇵🇭',
  'bn': '🇧🇩',
  'bn-BD': '🇧🇩',
  'ur': '🇵🇰',
  'ur-PK': '🇵🇰',
  'fa': '🇮🇷',
  'fa-IR': '🇮🇷',
  'sw': '🇰🇪',
  'sw-KE': '🇰🇪',
  'zu': '🇿🇦',
  'zu-ZA': '🇿🇦',
  'af': '🇿🇦',
  'af-ZA': '🇿🇦',
};

const getLocaleFlag = (code: string): string => {
  // Try exact match first
  if (LOCALE_FLAGS[code]) {
    return LOCALE_FLAGS[code];
  }

  // Try language part only (e.g., 'en' from 'en-US')
  const langPart = code.split('-')[0].toLowerCase();
  if (LOCALE_FLAGS[langPart]) {
    return LOCALE_FLAGS[langPart];
  }

  // Default world flag for unknown locales
  return '🌐';
};

export const LocaleProvider = ({ children }: { children: ReactNode }) => {
  const [locales, setLocales] = useState<Locale[]>([]);
  const [currentLocale, setCurrentLocale] = useState<Locale | null>(null);
  const [loading, setLoading] = useState(true);

  const loadLocales = async () => {
    setLoading(true);
    try {
      const response = await api.i18n.locales.list({ active_only: false });
      // Ensure we have a valid array and filter out any undefined/null values
      const validResults = (response.results || []).filter((locale: any) => locale !== null && locale !== undefined);
      const localesWithFlags = validResults.map((locale: Locale) => ({
        ...locale,
        flag: getLocaleFlag(locale.code)
      }));
      setLocales(localesWithFlags);

      // Only set current locale on initial load
      if (!currentLocale) {
        // Try to restore from localStorage first
        const storedLocale = localStorage.getItem('current_locale');
        if (storedLocale) {
          try {
            const parsed = JSON.parse(storedLocale);
            const matchingLocale = localesWithFlags.find((l: Locale) => l.code === parsed.code);
            if (matchingLocale && matchingLocale.is_active) {
              setCurrentLocale(matchingLocale);
              return;
            }
          } catch {
            // Invalid stored locale, continue to auto-detect
          }
        }

        // Auto-detect browser language on first visit
        if (isFirstVisit() && localesWithFlags.length > 1) {
          const browserLanguages = getBrowserLanguages();
          const matchedLocaleCode = matchBrowserToLocale(browserLanguages, localesWithFlags);

          if (matchedLocaleCode) {
            const matchedLocale = localesWithFlags.find((l: Locale) => l.code === matchedLocaleCode);
            if (matchedLocale) {
              setCurrentLocale(matchedLocale);
              localStorage.setItem('current_locale', JSON.stringify(matchedLocale));
              markAutoDetected();

              // Optional: Show a notification that we auto-detected their language
              console.log(`Auto-detected language: ${matchedLocale.name}`);
              return;
            }
          }
        }

        // Fall back to default locale
        const defaultLocale = localesWithFlags.find((l: Locale) => l.is_default);
        if (defaultLocale) {
          setCurrentLocale(defaultLocale);
          localStorage.setItem('current_locale', JSON.stringify(defaultLocale));
        }
      } else {
        // On refresh, update current locale if it still exists and is active
        const updatedCurrentLocale = localesWithFlags.find((l: Locale) => l.id === currentLocale.id);
        if (updatedCurrentLocale && updatedCurrentLocale.is_active) {
          setCurrentLocale(updatedCurrentLocale);
        } else {
          // Current locale was deleted or deactivated, switch to default
          const defaultLocale = localesWithFlags.find((l: Locale) => l.is_default);
          if (defaultLocale) {
            setCurrentLocale(defaultLocale);
            localStorage.setItem('current_locale', JSON.stringify(defaultLocale));
          }
        }
      }
    } catch (error) {
      console.error('Failed to load locales:', error);
      // Set a default fallback locale if API fails
      const fallbackLocale: Locale = {
        id: 1,
        code: 'en',
        name: 'English',
        native_name: 'English',
        is_active: true,
        is_default: true,
        rtl: false,
        flag: '🇺🇸'
      };
      setLocales([fallbackLocale]);
      if (!currentLocale) {
        setCurrentLocale(fallbackLocale);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLocales();
  }, []); // Remove currentLocale from dependencies to prevent infinite loop

  // Memoize expensive computations to prevent unnecessary re-renders
  const activeLocales = useMemo(() =>
    locales.filter(l => l.is_active),
    [locales]
  );

  const defaultLocale = useMemo(() =>
    locales.find(l => l.is_default) || null,
    [locales]
  );

  const handleSetCurrentLocale = useCallback((locale: Locale) => {
    setCurrentLocale(locale);
    // Persist to localStorage
    localStorage.setItem('current_locale', JSON.stringify(locale));

    // Set document direction based on RTL
    document.documentElement.dir = locale.rtl ? 'rtl' : 'ltr';

    // Set lang attribute
    document.documentElement.lang = locale.code;
  }, []);

  const getLocaleByCode = useCallback((code: string) => {
    return locales.find(l => l.code === code);
  }, [locales]);

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo(() => ({
    locales,
    activeLocales,
    currentLocale,
    defaultLocale,
    loading,
    setCurrentLocale: handleSetCurrentLocale,
    getLocaleByCode,
    refreshLocales: loadLocales,
  }), [
    locales,
    activeLocales,
    currentLocale,
    defaultLocale,
    loading,
    handleSetCurrentLocale,
    getLocaleByCode,
    loadLocales,
  ]);

  return (
    <LocaleContext.Provider value={contextValue}>
      {children}
    </LocaleContext.Provider>
  );
};

export const useLocale = () => {
  const context = useContext(LocaleContext);
  if (context === undefined) {
    throw new Error('useLocale must be used within a LocaleProvider');
  }
  return context;
};
