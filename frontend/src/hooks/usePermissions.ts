import { useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export interface UserScopes {
  locales: string[];
  sections: string[];
}

export interface PermissionContext {
  permissions: string[];
  roles: string[];
  scopes: UserScopes;
  isLoading: boolean;
  hasPermission: (permission: string) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
  canAccessLocale: (locale: string) => boolean;
  canAccessSection: (section: string) => boolean;
  canPerformAction: (resource: string, action: string) => boolean;
  isAdmin: () => boolean;
  isManager: () => boolean;
  isSuperuser: () => boolean;
}

export const usePermissions = (): PermissionContext => {
  const { user, isLoading } = useAuth();

  return useMemo(() => {
    // Handle case where user might not have all properties
    const permissions = (user as any)?.permissions || [];
    const roles = (user as any)?.role ? [(user as any).role] : [];
    const scopes = (user as any)?.scopes || { locales: [], sections: [] };

    const hasPermission = (permission: string): boolean => {
      if (!user) return false;
      if ((user as any)?.is_superuser) return true;
      return permissions.includes(permission);
    };

    const hasAnyPermission = (perms: string[]): boolean => {
      if (!user) return false;
      if ((user as any)?.is_superuser) return true;
      return perms.some(p => permissions.includes(p));
    };

    const hasAllPermissions = (perms: string[]): boolean => {
      if (!user) return false;
      if ((user as any)?.is_superuser) return true;
      return perms.every(p => permissions.includes(p));
    };

    const hasRole = (role: string): boolean => {
      if (!user) return false;
      if ((user as any)?.is_superuser) return true;
      return (user as any)?.role === role || roles.includes(role);
    };

    const hasAnyRole = (checkRoles: string[]): boolean => {
      if (!user) return false;
      if ((user as any)?.is_superuser) return true;
      return checkRoles.includes((user as any)?.role) || checkRoles.some(r => roles.includes(r));
    };

    const canAccessLocale = (locale: string): boolean => {
      if (!user) return false;
      if ((user as any)?.is_superuser) return true;
      if (!scopes.locales || scopes.locales.length === 0) return true; // No locale restrictions
      return scopes.locales.includes(locale);
    };

    const canAccessSection = (section: string): boolean => {
      if (!user) return false;
      if ((user as any)?.is_superuser) return true;
      if (!scopes.sections || scopes.sections.length === 0) return true; // No section restrictions
      
      // Check if any allowed section is a prefix of the requested section
      return scopes.sections.some(allowedSection => 
        section.startsWith(allowedSection) || allowedSection === '/'
      );
    };

    const canPerformAction = (resource: string, action: string): boolean => {
      const permission = `${resource}.${action}`;
      return hasPermission(permission);
    };

    const isAdmin = (): boolean => {
      return (user as any)?.is_staff || (user as any)?.role === 'admin' || (user as any)?.is_superuser || false;
    };

    const isManager = (): boolean => {
      return isAdmin() || (user as any)?.role === 'manager' || false;
    };

    const isSuperuser = (): boolean => {
      return (user as any)?.is_superuser || false;
    };

    return {
      permissions,
      roles,
      scopes,
      isLoading,
      hasPermission,
      hasAnyPermission,
      hasAllPermissions,
      hasRole,
      hasAnyRole,
      canAccessLocale,
      canAccessSection,
      canPerformAction,
      isAdmin,
      isManager,
      isSuperuser,
    };
  }, [user, isLoading]);
};

// Convenience hook for checking a single permission
export const useHasPermission = (permission: string): boolean => {
  const { hasPermission } = usePermissions();
  return hasPermission(permission);
};

// Convenience hook for checking multiple permissions
export const useHasAnyPermission = (permissions: string[]): boolean => {
  const { hasAnyPermission } = usePermissions();
  return hasAnyPermission(permissions);
};

// Convenience hook for checking role
export const useHasRole = (role: string): boolean => {
  const { hasRole } = usePermissions();
  return hasRole(role);
};

// Convenience hook for checking locale access
export const useCanAccessLocale = (locale: string): boolean => {
  const { canAccessLocale } = usePermissions();
  return canAccessLocale(locale);
};