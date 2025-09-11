import React from 'react';
import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

const ErrorFallback = React.memo<ErrorFallbackProps>(({ error, resetErrorBoundary }) => {
  const isDev = import.meta.env.DEV;

  return (
    <div className="min-h-screen flex items-center justify-center p-4" role="alert">
      <div className="max-w-2xl w-full space-y-8">
        <Alert variant="destructive" className="border-2">
          <AlertCircle className="h-5 w-5" />
          <AlertTitle className="text-lg font-semibold">
            Something went wrong
          </AlertTitle>
          <AlertDescription className="mt-4 space-y-4">
            <p className="text-sm">
              An unexpected error occurred. The application encountered a problem and couldn't recover.
            </p>
            
            {isDev && error.message && (
              <div className="mt-4 p-4 bg-muted rounded-lg">
                <p className="font-mono text-xs text-muted-foreground mb-2">
                  Error details (development mode):
                </p>
                <pre className="font-mono text-xs overflow-auto whitespace-pre-wrap break-words">
                  {error.message}
                </pre>
                {error.stack && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                      Stack trace
                    </summary>
                    <pre className="mt-2 font-mono text-xs overflow-auto whitespace-pre-wrap break-words text-muted-foreground">
                      {error.stack}
                    </pre>
                  </details>
                )}
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-3 pt-4">
              <Button
                onClick={resetErrorBoundary}
                variant="default"
                className="flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </Button>
              
              <Button
                onClick={() => window.location.href = '/'}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Home className="h-4 w-4" />
                Go to homepage
              </Button>
            </div>
          </AlertDescription>
        </Alert>

        <div className="text-center">
          <p className="text-sm text-muted-foreground">
            If this problem persists, please contact support or try refreshing the page.
          </p>
        </div>
      </div>
    </div>
  );
});

ErrorFallback.displayName = 'ErrorFallback';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: { componentStack: string }) => void;
  onReset?: () => void;
}

export const ErrorBoundary = React.memo<ErrorBoundaryProps>(({ 
  children, 
  fallback = ErrorFallback,
  onError,
  onReset
}) => {
  return (
    <ReactErrorBoundary
      FallbackComponent={fallback}
      onError={(error, errorInfo) => {
        // Log to console in development
        if (import.meta.env.DEV) {
          console.error('Error caught by boundary:', error, errorInfo);
        }
        
        // Call custom error handler if provided
        onError?.(error, errorInfo);
        
        // Send to monitoring service in production
        if (!import.meta.env.DEV && import.meta.env.VITE_ERROR_REPORTING_ENDPOINT) {
          fetch(import.meta.env.VITE_ERROR_REPORTING_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: error.message,
              stack: error.stack,
              componentStack: errorInfo.componentStack,
              url: window.location.href,
              userAgent: navigator.userAgent,
              timestamp: new Date().toISOString(),
            }),
          }).catch(() => {
            // Silently fail error reporting
          });
        }
      }}
      onReset={() => {
        // Clear any error state
        onReset?.();
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
});

ErrorBoundary.displayName = 'ErrorBoundary';

// Route-specific error boundary with simpler UI
export const RouteErrorBoundary = React.memo<{ children: React.ReactNode }>(({ children }) => {
  return (
    <ErrorBoundary
      fallback={({ error, resetErrorBoundary }) => (
        <div className="p-8 text-center">
          <h2 className="text-2xl font-semibold mb-4">Page Error</h2>
          <p className="text-muted-foreground mb-6">
            This page encountered an error and cannot be displayed.
          </p>
          <div className="flex gap-4 justify-center">
            <Button onClick={resetErrorBoundary}>
              Try Again
            </Button>
            <Button variant="outline" onClick={() => window.history.back()}>
              Go Back
            </Button>
          </div>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
});

RouteErrorBoundary.displayName = 'RouteErrorBoundary';