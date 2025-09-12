import React, { memo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  FileText,
  Plus,
  Globe,
  Upload,
  Image,
  BookOpen,
  Lock,
  AlertTriangle,
  ExternalLink,
  Lightbulb,
  ArrowRight
} from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: "default" | "outline";
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
    icon?: React.ComponentType<{ className?: string }>;
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = memo(({
  icon: Icon = FileText,
  title,
  description,
  action,
  secondaryAction,
  className = ""
}) => {
  return (
    <div className={`flex flex-col items-center justify-center py-16 px-4 text-center ${className}`}>
      <div className="rounded-full bg-muted/30 p-6 mb-6">
        <Icon className="h-12 w-12 text-muted-foreground" />
      </div>
      <h3 className="text-xl font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-muted-foreground mb-6 max-w-md leading-relaxed">{description}</p>

      <div className="flex flex-col sm:flex-row gap-3">
        {action && (
          <Button onClick={action.onClick} variant={action.variant || "default"}>
            {action.label}
          </Button>
        )}
        {secondaryAction && (
          <Button variant="outline" onClick={secondaryAction.onClick} className="gap-2">
            {secondaryAction.icon && <secondaryAction.icon className="h-4 w-4" />}
            {secondaryAction.label}
          </Button>
        )}
      </div>
    </div>
  );
});

EmptyState.displayName = 'EmptyState';

export const PagesEmptyState: React.FC<{ onCreatePage: () => void }> = memo(({ onCreatePage }) => {
  return (
    <EmptyState
      icon={FileText}
      title="No pages yet"
      description="Get started by creating your first page. You can add content, customize the design, and publish when you're ready."
      action={{
        label: "Create First Page",
        onClick: onCreatePage
      }}
    />
  );
});

PagesEmptyState.displayName = 'PagesEmptyState';

export const TranslationsEmptyState: React.FC<{
  locale?: string;
  onAddLocale: () => void;
  onSeedTranslations?: () => void;
}> = memo(({ locale, onAddLocale, onSeedTranslations }) => (
  <div className="py-16 px-4">
    <div className="max-w-2xl mx-auto">
      <EmptyState
        icon={Globe}
        title={locale ? `No translations for ${locale}` : "No locales configured"}
        description={
          locale
            ? "This locale doesn't have any translations yet. You can seed initial translations from your default locale or start adding them manually."
            : "Set up your first locale to start managing translations across different languages."
        }
        action={{
          label: locale ? "Seed Translations" : "Add First Locale",
          onClick: locale && onSeedTranslations ? onSeedTranslations : onAddLocale
        }}
      />

      {locale && (
        <Card className="mt-8 bg-blue-50/50 border-blue-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-blue-600" />
              How to add translations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-start gap-3">
              <Badge variant="outline" className="shrink-0 text-xs">1</Badge>
              <div>
                <p className="font-medium">Set up locales</p>
                <p className="text-muted-foreground">Configure all languages you want to support in Locale Management</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge variant="outline" className="shrink-0 text-xs">2</Badge>
              <div>
                <p className="font-medium">Seed initial content</p>
                <p className="text-muted-foreground">Copy existing translations from your default locale as a starting point</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Badge variant="outline" className="shrink-0 text-xs">3</Badge>
              <div>
                <p className="font-medium">Translate manually</p>
                <p className="text-muted-foreground">Edit translations directly or assign them to translators</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  </div>
));

TranslationsEmptyState.displayName = 'TranslationsEmptyState';

export const MediaEmptyState: React.FC<{
  onUpload: () => void;
  isDragActive?: boolean;
}> = memo(({ onUpload, isDragActive = false }) => (
  <div className={`border-2 border-dashed rounded-lg transition-colors ${
    isDragActive
      ? 'border-primary bg-primary/5'
      : 'border-muted-foreground/25 hover:border-muted-foreground/40'
  }`}>
    <EmptyState
      icon={Image}
      title={isDragActive ? "Drop files here" : "No media files"}
      description={
        isDragActive
          ? "Release to upload your files"
          : "Upload images, videos, and documents to use across your content. Drag and drop files here or click to browse."
      }
      action={{
        label: "Upload Files",
        onClick: onUpload,
        variant: "outline"
      }}
      className="py-20"
    />

    <div className="px-8 pb-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-muted-foreground">
        <div>
          <h4 className="font-medium text-foreground mb-2">Supported formats</h4>
          <ul className="space-y-1">
            <li>• Images: JPG, PNG, GIF, WebP</li>
            <li>• Videos: MP4, WebM, MOV</li>
            <li>• Documents: PDF, DOC, TXT</li>
          </ul>
        </div>
        <div>
          <h4 className="font-medium text-foreground mb-2">Tips</h4>
          <ul className="space-y-1">
            <li>• Max file size: 50MB</li>
            <li>• Use descriptive filenames</li>
            <li>• Optimize images for web</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
));

MediaEmptyState.displayName = 'MediaEmptyState';

export const PermissionErrorState: React.FC<{
  action?: string;
  resource?: string;
  onRequestAccess?: () => void;
}> = memo(({
  action = "access this content",
  resource = "resource",
  onRequestAccess
}) => {
  const handleContactAdmin = useCallback(() => {
    window.open('mailto:admin@company.com?subject=Access Request', '_blank');
  }, []);

  return (
  <div className="py-16 px-4">
    <Card className="max-w-md mx-auto border-destructive/20 bg-destructive/5">
      <CardContent className="pt-6">
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="rounded-full bg-destructive/10 p-3">
            <Lock className="h-8 w-8 text-destructive" />
          </div>

          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-foreground">Access Denied</h3>
            <p className="text-sm text-muted-foreground">
              You don't have permission to {action}. Your current role doesn't include access to this {resource}.
            </p>
          </div>

          <div className="space-y-3 w-full">
            {onRequestAccess && (
              <Button onClick={onRequestAccess} className="w-full">
                Request Access
              </Button>
            )}
            <Button
              variant="outline"
              onClick={handleContactAdmin}
              className="w-full gap-2"
            >
              <ExternalLink className="h-4 w-4" />
              Contact Administrator
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card className="max-w-md mx-auto mt-6 bg-blue-50/50 border-blue-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-blue-600" />
          Need different permissions?
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm space-y-2">
        <p className="text-muted-foreground">
          Contact your administrator to request the necessary permissions or role changes.
        </p>
        <div className="flex items-center gap-2 text-blue-700">
          <ArrowRight className="h-3 w-3" />
          <span className="font-medium">Include what you're trying to access</span>
        </div>
      </CardContent>
    </Card>
  </div>
  );
});

PermissionErrorState.displayName = 'PermissionErrorState';

export const NotFoundState: React.FC<{
  title?: string;
  description?: string;
  onGoBack: () => void;
}> = memo(({
  title = "Page not found",
  description = "The page you're looking for doesn't exist or has been moved.",
  onGoBack
}) => {
  const handleGoHome = useCallback(() => {
    window.location.href = '/';
  }, []);

  return (
    <EmptyState
      icon={AlertTriangle}
      title={title}
      description={description}
      action={{
        label: "Go Back",
        onClick: onGoBack,
        variant: "outline"
      }}
      secondaryAction={{
        label: "Go to Home",
        onClick: handleGoHome,
        icon: ArrowRight
      }}
    />
  );
});

NotFoundState.displayName = 'NotFoundState';

export const LoadingState: React.FC<{ message?: string }> = memo(({
  message = "Loading..."
}) => (
  <div className="flex flex-col items-center justify-center py-16 px-4">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
    <p className="text-muted-foreground">{message}</p>
  </div>
));

LoadingState.displayName = 'LoadingState';
