import React, { ReactNode, useMemo } from 'react';
import { usePermissions } from '@/hooks/usePermissions';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ShieldX } from 'lucide-react';

interface PermissionGuardProps {
  /** Required permissions (user needs ANY of these) */
  permissions?: string[];
  /** Required permissions (user needs ALL of these) */
  requireAllPermissions?: string[];
  /** Required roles (user needs ANY of these) */
  roles?: string[];
  /** Required locales (user needs access to ANY of these) */
  locales?: string[];
  /** Required sections (user needs access to ANY of these) */
  sections?: string[];
  /** Whether to require ALL permissions instead of ANY */
  requireAll?: boolean;
  /** Custom fallback component */
  fallback?: ReactNode;
  /** Show an error message when access is denied */
  showFallback?: boolean;
  /** Custom error message */
  errorMessage?: string;
  /** Children to render when access is granted */
  children: ReactNode;
  /** Custom access check function */
  customCheck?: (permissions: ReturnType<typeof usePermissions>) => boolean;
}

const PermissionDenied: React.FC<{ message?: string }> = ({
  message = "You don't have permission to access this feature"
}) => (
  <Alert variant="destructive" className="max-w-md">
    <ShieldX className="h-4 w-4" />
    <AlertDescription>{message}</AlertDescription>
  </Alert>
);

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permissions = [],
  requireAllPermissions = [],
  roles = [],
  locales = [],
  sections = [],
  requireAll = false,
  fallback,
  showFallback = true,
  errorMessage,
  children,
  customCheck,
}) => {
  const perms = usePermissions();

  const hasAccess = useMemo(() => {
    // If still loading, assume no access for security
    if (perms.isLoading) {
      return false;
    }

    // Custom check takes precedence
    if (customCheck) {
      return customCheck(perms);
    }

    // Check permissions
    if (permissions.length > 0) {
      const hasPerms = requireAll
        ? perms.hasAllPermissions(permissions)
        : perms.hasAnyPermission(permissions);
      if (!hasPerms) return false;
    }

    // Check "require all" permissions separately
    if (requireAllPermissions.length > 0) {
      if (!perms.hasAllPermissions(requireAllPermissions)) return false;
    }

    // Check roles
    if (roles.length > 0) {
      const hasRoles = perms.hasAnyRole(roles);
      if (!hasRoles) return false;
    }

    // Check locale access
    if (locales.length > 0) {
      const hasLocales = locales.some(locale => perms.canAccessLocale(locale));
      if (!hasLocales) return false;
    }

    // Check section access
    if (sections.length > 0) {
      const hasSections = sections.some(section => perms.canAccessSection(section));
      if (!hasSections) return false;
    }

    return true;
  }, [
    permissions,
    requireAllPermissions,
    roles,
    locales,
    sections,
    requireAll,
    perms,
    customCheck
  ]);

  // Show loading state
  if (perms.isLoading) {
    return <div className="animate-pulse bg-gray-200 h-4 w-full rounded" />;
  }

  // Grant access
  if (hasAccess) {
    return <>{children}</>;
  }

  // Deny access
  if (!showFallback) {
    return null;
  }

  if (fallback !== undefined) {
    return <>{fallback}</>;
  }

  return <PermissionDenied message={errorMessage} />;
};

// Convenience components for common use cases
export const RequirePermission: React.FC<{
  permission: string;
  fallback?: ReactNode;
  children: ReactNode;
}> = ({ permission, fallback, children }) => (
  <PermissionGuard
    permissions={[permission]}
    fallback={fallback}
    children={children}
  />
);

export const RequireRole: React.FC<{
  role: string;
  fallback?: ReactNode;
  children: ReactNode;
}> = ({ role, fallback, children }) => (
  <PermissionGuard
    roles={[role]}
    fallback={fallback}
    children={children}
  />
);

export const RequireAdmin: React.FC<{
  fallback?: ReactNode;
  children: ReactNode;
}> = ({ fallback, children }) => (
  <PermissionGuard
    customCheck={(perms) => perms.isAdmin()}
    fallback={fallback}
    children={children}
  />
);

export const RequireLocaleAccess: React.FC<{
  locale: string;
  fallback?: ReactNode;
  children: ReactNode;
}> = ({ locale, fallback, children }) => (
  <PermissionGuard
    locales={[locale]}
    fallback={fallback}
    children={children}
  />
);
