import React, { useEffect, useState } from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import { api } from '@/lib/api';

interface RedirectHandlerProps {
  children: React.ReactNode;
}

const RedirectHandler: React.FC<RedirectHandlerProps> = ({ children }) => {
  const location = useLocation();
  const [redirect, setRedirect] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkForRedirect = async () => {
      try {
        setLoading(true);

        // Check if there's a redirect for the current path
        const response = await api.redirects.list({
          search: location.pathname
        });

        if (response.results?.length > 0) {
          const redirectRule = response.results[0];

          // Find exact match for source path
          const exactMatch = response.results.find((rule: any) =>
            rule.from_path === location.pathname && rule.is_active
          );

          if (exactMatch && exactMatch.to_path) {
            setRedirect(exactMatch.to_path);
            return;
          }
        }

        setRedirect(null);
      } catch (error) {
        console.error('Failed to check for redirects:', error);
        setRedirect(null);
      } finally {
        setLoading(false);
      }
    };

    // Only check for redirects on public routes (not dashboard)
    if (!location.pathname.startsWith('/dashboard')) {
      checkForRedirect();
    } else {
      setLoading(false);
    }
  }, [location.pathname]);

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (redirect) {
    // Check if it's an external redirect
    if (redirect.startsWith('http://') || redirect.startsWith('https://')) {
      window.location.href = redirect;
      return null;
    }

    // Internal redirect
    return <Navigate to={redirect} replace />;
  }

  return <>{children}</>;
};

export default RedirectHandler;
