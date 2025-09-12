import { ReactNode, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { PermissionGuard } from "@/components/guards/PermissionGuard";
import { usePermissions } from "@/hooks/usePermissions";

interface ActionItem {
  id: string;
  label: string;
  icon?: ReactNode;
  onClick: () => void | Promise<void>;
  permissions?: string[];
  roles?: string[];
  locales?: string[];
  variant?: 'default' | 'destructive';
  disabled?: boolean;
  separatorAfter?: boolean;
  separatorBefore?: boolean;
  customCheck?: (permissions: ReturnType<typeof usePermissions>) => boolean;
}

interface ContentActionsProps {
  /** Array of action items to display */
  actions: ActionItem[];
  /** Content object for context (used for locale checks) */
  content?: {
    locale?: string;
    [key: string]: any;
  };
  /** Trigger button size */
  size?: 'sm' | 'md' | 'lg';
  /** Trigger button variant */
  triggerVariant?: 'ghost' | 'outline' | 'default';
  /** Custom trigger element */
  trigger?: ReactNode;
  /** Show actions as inline buttons instead of dropdown */
  inline?: boolean;
  /** Custom permission error message */
  permissionErrorMessage?: string;
  /** Disable all actions */
  disabled?: boolean;
  /** Loading state for specific actions */
  loading?: string[];
}

export const ContentActions: React.FC<ContentActionsProps> = ({
  actions,
  content,
  size = 'md',
  triggerVariant = 'ghost',
  trigger,
  inline = false,
  permissionErrorMessage,
  disabled = false,
  loading = [],
}) => {
  const permissions = usePermissions();
  const [isLoading, setIsLoading] = useState<string | null>(null);

  // Filter actions based on permissions
  const visibleActions = useMemo(() => {
    return actions.filter(action => {
      // Check custom permission function
      if (action.customCheck && !action.customCheck(permissions)) {
        return false;
      }

      // Check required permissions
      if (action.permissions && action.permissions.length > 0) {
        if (!permissions.hasAnyPermission(action.permissions)) {
          return false;
        }
      }

      // Check required roles
      if (action.roles && action.roles.length > 0) {
        if (!permissions.hasAnyRole(action.roles)) {
          return false;
        }
      }

      // Check locale access
      if (action.locales && action.locales.length > 0) {
        const hasLocaleAccess = action.locales.some(locale =>
          permissions.canAccessLocale(locale)
        );
        if (!hasLocaleAccess) {
          return false;
        }
      }

      // Check content locale if provided
      if (content?.locale && action.locales?.includes(content.locale)) {
        if (!permissions.canAccessLocale(content.locale)) {
          return false;
        }
      }

      return true;
    });
  }, [actions, permissions, content]);

  const handleAction = async (action: ActionItem) => {
    // Check locale access for content
    if (content?.locale && !permissions.canAccessLocale(content.locale)) {
      toast.error(permissionErrorMessage || `You don't have access to this content's locale`);
      return;
    }

    setIsLoading(action.id);
    try {
      await action.onClick();
    } catch (error) {
      console.error('Action failed:', error);
      toast.error('Action failed. Please try again.');
    } finally {
      setIsLoading(null);
    }
  };

  // Don't render if no visible actions
  if (visibleActions.length === 0) {
    return null;
  }

  const isActionLoading = (actionId: string) =>
    isLoading === actionId || loading.includes(actionId);

  const isActionDisabled = (action: ActionItem) =>
    disabled || action.disabled || isActionLoading(action.id);

  if (inline) {
    return (
      <div className="flex items-center gap-2">
        {visibleActions.map((action, index) => (
          <PermissionGuard
            key={action.id}
            permissions={action.permissions}
            roles={action.roles}
            locales={action.locales}
            customCheck={action.customCheck}
            showFallback={false}
          >
            <Button
              variant={action.variant === 'destructive' ? 'destructive' : 'ghost'}
              size={size}
              onClick={() => handleAction(action)}
              disabled={isActionDisabled(action)}
              className={action.variant === 'destructive' ? 'text-destructive' : ''}
            >
              {action.icon}
              {isActionLoading(action.id) ? 'Loading...' : action.label}
            </Button>
          </PermissionGuard>
        ))}
      </div>
    );
  }

  // Dropdown variant
  const defaultTrigger = (
    <Button
      variant={triggerVariant}
      size={size}
      disabled={disabled || isLoading !== null}
      className="h-8 w-8 p-0"
    >
      <span className="sr-only">Open menu</span>
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01" />
      </svg>
    </Button>
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {trigger || defaultTrigger}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {visibleActions.map((action, index) => (
          <PermissionGuard
            key={action.id}
            permissions={action.permissions}
            roles={action.roles}
            locales={action.locales}
            customCheck={action.customCheck}
            showFallback={false}
          >
            <>
              {action.separatorBefore && <DropdownMenuSeparator />}
              <DropdownMenuItem
                onClick={() => handleAction(action)}
                disabled={isActionDisabled(action)}
                className={action.variant === 'destructive' ? 'text-destructive focus:text-destructive' : ''}
              >
                {action.icon && <span className="mr-2">{action.icon}</span>}
                {isActionLoading(action.id) ? 'Loading...' : action.label}
              </DropdownMenuItem>
              {action.separatorAfter && <DropdownMenuSeparator />}
            </>
          </PermissionGuard>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

// Convenience hook for common content actions
export const useContentActions = () => {
  const permissions = usePermissions();

  const createActions = (
    content: any,
    handlers: {
      onEdit?: () => void;
      onDelete?: () => void;
      onDuplicate?: () => void;
      onView?: () => void;
      onPublish?: () => void;
      onUnpublish?: () => void;
      onArchive?: () => void;
      [key: string]: (() => void) | undefined;
    }
  ): ActionItem[] => {
    const actions: ActionItem[] = [];

    if (handlers.onView) {
      actions.push({
        id: 'view',
        label: 'View',
        icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>,
        onClick: handlers.onView,
        permissions: ['view'],
      });
    }

    if (handlers.onEdit) {
      actions.push({
        id: 'edit',
        label: 'Edit',
        icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>,
        onClick: handlers.onEdit,
        permissions: ['change'],
        separatorBefore: true,
      });
    }

    if (handlers.onDuplicate) {
      actions.push({
        id: 'duplicate',
        label: 'Duplicate',
        icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>,
        onClick: handlers.onDuplicate,
        permissions: ['add'],
      });
    }

    if (handlers.onPublish && content.status === 'draft') {
      actions.push({
        id: 'publish',
        label: 'Publish',
        icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>,
        onClick: handlers.onPublish,
        permissions: ['publish'],
        separatorBefore: true,
      });
    }

    if (handlers.onUnpublish && content.status === 'published') {
      actions.push({
        id: 'unpublish',
        label: 'Unpublish',
        icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" /></svg>,
        onClick: handlers.onUnpublish,
        permissions: ['publish'],
        separatorBefore: true,
      });
    }

    if (handlers.onArchive) {
      actions.push({
        id: 'archive',
        label: 'Archive',
        icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8l4 4 4-4" /></svg>,
        onClick: handlers.onArchive,
        permissions: ['change'],
      });
    }

    if (handlers.onDelete) {
      actions.push({
        id: 'delete',
        label: 'Delete',
        icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>,
        onClick: handlers.onDelete,
        permissions: ['delete'],
        variant: 'destructive',
        separatorBefore: true,
      });
    }

    return actions;
  };

  return { createActions, permissions };
};

export default ContentActions;