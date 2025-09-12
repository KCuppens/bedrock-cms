import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { PermissionErrorState } from '@/components/EmptyStates';
import {
  Lock,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Home
} from 'lucide-react';

interface ErrorPageProps {
  onRetry?: () => void;
  onGoHome?: () => void;
  onContactSupport?: () => void;
}

export const PermissionErrorPage: React.FC<ErrorPageProps & {
  action?: string;
  resource?: string;
}> = ({
  action = "access this content",
  resource = "resource",
  onRetry,
  onGoHome = () => window.location.href = '/',
  onContactSupport
}) => (
  <div className="min-h-screen bg-background flex items-center justify-center p-4">
    <PermissionErrorState
      action={action}
      resource={resource}
      onRequestAccess={onContactSupport}
    />
  </div>
);

export const ServerErrorPage: React.FC<ErrorPageProps> = ({
  onRetry,
  onGoHome = () => window.location.href = '/',
  onContactSupport
}) => (
  <div className="min-h-screen bg-background flex items-center justify-center p-4">
    <Card className="max-w-md mx-auto">
      <CardContent className="pt-6">
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="rounded-full bg-destructive/10 p-4">
            <AlertTriangle className="h-12 w-12 text-destructive" />
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-semibold text-foreground">Server Error</h1>
            <p className="text-muted-foreground">
              Something went wrong on our end. We're working to fix it.
            </p>
          </div>

          <div className="space-y-3 w-full">
            {onRetry && (
              <Button onClick={onRetry} className="w-full">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            )}
            <Button variant="outline" onClick={onGoHome} className="w-full">
              <Home className="h-4 w-4 mr-2" />
              Go Home
            </Button>
            {onContactSupport && (
              <Button
                variant="outline"
                onClick={onContactSupport}
                className="w-full"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Contact Support
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
);

export const MaintenanceErrorPage: React.FC<ErrorPageProps> = ({
  onRetry,
  onContactSupport
}) => (
  <div className="min-h-screen bg-background flex items-center justify-center p-4">
    <Card className="max-w-md mx-auto">
      <CardContent className="pt-6">
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="rounded-full bg-blue-100 p-4">
            <RefreshCw className="h-12 w-12 text-blue-600" />
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-semibold text-foreground">Under Maintenance</h1>
            <p className="text-muted-foreground">
              We're performing scheduled maintenance. Please check back shortly.
            </p>
          </div>

          <div className="space-y-3 w-full">
            {onRetry && (
              <Button onClick={onRetry} variant="outline" className="w-full">
                <RefreshCw className="h-4 w-4 mr-2" />
                Check Again
              </Button>
            )}
            {onContactSupport && (
              <Button
                variant="outline"
                onClick={onContactSupport}
                className="w-full"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Status Updates
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
);

// Hook for handling common error states
export const useErrorHandling = () => {
  const handleRetry = () => {
    window.location.reload();
  };

  const handleGoHome = () => {
    window.location.href = '/';
  };

  const handleContactSupport = () => {
    window.open('mailto:support@company.com?subject=Access Request', '_blank');
  };

  return {
    handleRetry,
    handleGoHome,
    handleContactSupport
  };
};
