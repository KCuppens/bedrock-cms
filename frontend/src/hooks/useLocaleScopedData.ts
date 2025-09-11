import { useMemo } from 'react';
import { usePermissions } from './usePermissions';

interface LocaleAware {
  locale?: string;
}

interface SectionAware {
  path?: string;
}

/**
 * Hook to filter data based on user's locale permissions
 */
export const useLocaleScopedData = <T extends LocaleAware>(
  data: T[],
  options: {
    enforceScope?: boolean;
    defaultLocale?: string;
    includeNoLocale?: boolean;
  } = {}
): T[] => {
  const permissions = usePermissions();
  const { 
    enforceScope = true, 
    defaultLocale = 'en',
    includeNoLocale = true 
  } = options;

  return useMemo(() => {
    // If not enforcing scope or user is superuser, return all data
    if (!enforceScope || permissions.isSuperuser()) {
      return data;
    }

    // If no locale scopes defined, return all data
    if (!permissions.scopes.locales || permissions.scopes.locales.length === 0) {
      return data;
    }

    return data.filter(item => {
      // Include items without locale if specified
      if (!item.locale && includeNoLocale) {
        return true;
      }

      // Check if user can access this locale
      if (item.locale) {
        return permissions.canAccessLocale(item.locale);
      }

      return false;
    });
  }, [data, permissions, enforceScope, defaultLocale, includeNoLocale]);
};

/**
 * Hook to filter data based on user's section permissions
 */
export const useSectionScopedData = <T extends SectionAware>(
  data: T[],
  options: {
    enforceScope?: boolean;
    includeNoSection?: boolean;
  } = {}
): T[] => {
  const permissions = usePermissions();
  const { enforceScope = true, includeNoSection = true } = options;

  return useMemo(() => {
    // If not enforcing scope or user is superuser, return all data
    if (!enforceScope || permissions.isSuperuser()) {
      return data;
    }

    // If no section scopes defined, return all data
    if (!permissions.scopes.sections || permissions.scopes.sections.length === 0) {
      return data;
    }

    return data.filter(item => {
      // Include items without path/section if specified
      if (!item.path && includeNoSection) {
        return true;
      }

      // Check if user can access this section
      if (item.path) {
        return permissions.canAccessSection(item.path);
      }

      return false;
    });
  }, [data, permissions, enforceScope, includeNoSection]);
};

/**
 * Hook to filter data based on both locale and section permissions
 */
export const useScopedData = <T extends LocaleAware & SectionAware>(
  data: T[],
  options: {
    enforceLocaleScope?: boolean;
    enforceSectionScope?: boolean;
    includeNoLocale?: boolean;
    includeNoSection?: boolean;
  } = {}
): T[] => {
  const permissions = usePermissions();
  const { 
    enforceLocaleScope = true, 
    enforceSectionScope = true,
    includeNoLocale = true,
    includeNoSection = true 
  } = options;

  return useMemo(() => {
    // If user is superuser, return all data
    if (permissions.isSuperuser()) {
      return data;
    }

    return data.filter(item => {
      // Check locale scope
      if (enforceLocaleScope && permissions.scopes.locales && permissions.scopes.locales.length > 0) {
        if (item.locale) {
          if (!permissions.canAccessLocale(item.locale)) {
            return false;
          }
        } else if (!includeNoLocale) {
          return false;
        }
      }

      // Check section scope
      if (enforceSectionScope && permissions.scopes.sections && permissions.scopes.sections.length > 0) {
        if (item.path) {
          if (!permissions.canAccessSection(item.path)) {
            return false;
          }
        } else if (!includeNoSection) {
          return false;
        }
      }

      return true;
    });
  }, [data, permissions, enforceLocaleScope, enforceSectionScope, includeNoLocale, includeNoSection]);
};

/**
 * Hook to check if current user can access a specific locale
 */
export const useCanAccessLocale = (locale: string | undefined): boolean => {
  const permissions = usePermissions();

  return useMemo(() => {
    if (!locale) return true;
    if (permissions.isSuperuser()) return true;
    return permissions.canAccessLocale(locale);
  }, [locale, permissions]);
};

/**
 * Hook to check if current user can access a specific section
 */
export const useCanAccessSection = (section: string | undefined): boolean => {
  const permissions = usePermissions();

  return useMemo(() => {
    if (!section) return true;
    if (permissions.isSuperuser()) return true;
    return permissions.canAccessSection(section);
  }, [section, permissions]);
};

/**
 * Hook to get available locales for current user
 */
export const useAvailableLocales = (): string[] => {
  const permissions = usePermissions();

  return useMemo(() => {
    if (permissions.isSuperuser()) {
      // Superuser can access all locales - would need to fetch from API
      return permissions.scopes.locales || [];
    }
    
    return permissions.scopes.locales || [];
  }, [permissions]);
};

/**
 * Hook to get available sections for current user
 */
export const useAvailableSections = (): string[] => {
  const permissions = usePermissions();

  return useMemo(() => {
    if (permissions.isSuperuser()) {
      // Superuser can access all sections
      return ['/'];
    }
    
    return permissions.scopes.sections || [];
  }, [permissions]);
};