import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { usePermissions } from "@/hooks/usePermissions";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ShieldX } from "lucide-react";

interface RoutePermissions {
  permissions?: string[];
  roles?: string[];
  locales?: string[];
  customCheck?: (permissions: ReturnType<typeof usePermissions>) => boolean;
}

// Define permission requirements for different routes
const routePermissions: Record<string, RoutePermissions> = {
  '/dashboard/pages': { permissions: ['cms.view_page'] },
  '/dashboard/pages/create': { permissions: ['cms.add_page'] },
  '/dashboard/pages/:id/edit': { permissions: ['cms.change_page'] },
  '/dashboard/blog': { permissions: ['blog.view_blogpost'] },
  '/dashboard/blog/create': { permissions: ['blog.add_blogpost'] },
  '/dashboard/blog/:id/edit': { permissions: ['blog.change_blogpost'] },
  '/dashboard/media': { permissions: ['files.view_fileupload'] },
  '/dashboard/media/upload': { permissions: ['files.add_fileupload'] },
  '/dashboard/users': { roles: ['admin', 'manager'] },
  '/dashboard/users/invite': { roles: ['admin'] },
  '/dashboard/analytics': { permissions: ['analytics.view_analytics'] },
  '/dashboard/settings': { roles: ['admin'] },
  '/dashboard/translations': { permissions: ['i18n.view_translationunit'] },
  '/dashboard/redirects': { permissions: ['cms.view_redirect'] },
};

const AccessDeniedPage = () => (
  <div className="flex items-center justify-center min-h-[50vh]">
    <Alert variant="destructive" className="max-w-md">
      <ShieldX className="h-4 w-4" />
      <AlertDescription>
        You don't have permission to access this page. 
        Please contact your administrator if you believe this is an error.
      </AlertDescription>
    </Alert>
  </div>
);

const checkRouteAccess = (
  pathname: string, 
  permissions: ReturnType<typeof usePermissions>
): boolean => {
  // Find matching route permission config
  const routeConfig = Object.entries(routePermissions).find(([route]) => {
    // Handle dynamic routes with :id parameters
    const routePattern = route.replace(/:[^/]+/g, '[^/]+');
    const regex = new RegExp(`^${routePattern}$`);
    return regex.test(pathname);
  });

  if (!routeConfig) {
    // No specific permissions required for this route
    return true;
  }

  const [, config] = routeConfig;

  // Check custom function first
  if (config.customCheck) {
    return config.customCheck(permissions);
  }

  // Check permissions
  if (config.permissions && config.permissions.length > 0) {
    if (!permissions.hasAnyPermission(config.permissions)) {
      return false;
    }
  }

  // Check roles
  if (config.roles && config.roles.length > 0) {
    if (!permissions.hasAnyRole(config.roles)) {
      return false;
    }
  }

  // Check locales
  if (config.locales && config.locales.length > 0) {
    const hasLocaleAccess = config.locales.some(locale => 
      permissions.canAccessLocale(locale)
    );
    if (!hasLocaleAccess) {
      return false;
    }
  }

  return true;
};

export const ProtectedRoute = () => {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  const permissions = usePermissions();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/sign-in" replace />;
  }

  // Check route-specific permissions
  const hasRouteAccess = checkRouteAccess(location.pathname, permissions);
  if (!hasRouteAccess) {
    return <AccessDeniedPage />;
  }

  return <Outlet />;
};