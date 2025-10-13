import React, { useEffect, useState, useRef } from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import { api } from '@/lib/api';

interface RedirectHandlerProps {
  children: React.ReactNode;
}

// Cache for redirect lookups to prevent repeated API calls
const redirectCache = new Map<string, { redirect: string | null; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Pending requests map to prevent duplicate concurrent requests
const pendingRequests = new Map<string, Promise<any>>();

const RedirectHandler: React.FC<RedirectHandlerProps> = ({ children }) => {
  const location = useLocation();
  const [redirect, setRedirect] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const checkForRedirect = async () => {
      // Skip dashboard routes entirely
      if (location.pathname.startsWith('/dashboard')) {
        return;
      }

      // Check cache first
      const cached = redirectCache.get(location.pathname);
      if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        setRedirect(cached.redirect);
        return;
      }

      // Check if there's already a pending request for this path
      const pendingRequest = pendingRequests.get(location.pathname);
      if (pendingRequest) {
        try {
          const response = await pendingRequest;
          if (isMountedRef.current) {
            processRedirectResponse(response);
          }
        } catch (error) {
          // Error already handled by original request
        }
        return;
      }

      try {
        setLoading(true);

        // Create the request promise and store it - use the new public lookup endpoint
        const requestPromise = api.redirects.lookup(location.pathname);
        pendingRequests.set(location.pathname, requestPromise);

        const response = await requestPromise;

        if (isMountedRef.current) {
          processRedirectResponse(response);
        }
      } catch (error) {
        // Silently fail - redirects are not critical
        if (isMountedRef.current) {
          setRedirect(null);
          // Cache the null result to prevent repeated failed requests
          redirectCache.set(location.pathname, { redirect: null, timestamp: Date.now() });
        }
      } finally {
        // Clean up pending request
        pendingRequests.delete(location.pathname);
        if (isMountedRef.current) {
          setLoading(false);
        }
      }
    };

    const processRedirectResponse = (response: { from_path: string; to_path: string; status: number } | null) => {
      let foundRedirect: string | null = null;

      // New lookup endpoint returns null if no redirect found, or the redirect object
      if (response && response.to_path) {
        foundRedirect = response.to_path;
      }

      setRedirect(foundRedirect);
      // Cache the result
      redirectCache.set(location.pathname, { redirect: foundRedirect, timestamp: Date.now() });
    };

    checkForRedirect();
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
