export interface TranslationKey {
  key: string;
  defaultValue: string;
  description?: string;
  namespace?: string;
}

export interface TranslationBundle {
  [key: string]: string;
}

export interface TranslationContextType {
  t: (key: string, defaultValue?: string) => string;
  locale: string;
  isLoading: boolean;
  missingKeys: Set<string>;
  registerKey: (key: TranslationKey) => void;
}

export interface TranslationProviderProps {
  children: React.ReactNode;
  locale?: string;
  fallbackLocale?: string;
  enableAutoSync?: boolean;
  syncInterval?: number;
  reportMissing?: boolean;
}
