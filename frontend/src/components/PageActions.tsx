import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { 
  MoreHorizontal, 
  Edit, 
  Eye, 
  Copy, 
  Trash2, 
  Send, 
  Archive,
  ExternalLink,
  Calendar,
  Globe
} from "lucide-react";
import { PermissionGuard } from "@/components/guards/PermissionGuard";
import { usePermissions, useCanAccessLocale } from "@/hooks/usePermissions";
import { Page } from "@/types/api";
import { api } from "@/lib/api.ts";

interface PageActionsProps {
  page: Page;
  onEdit?: (page: Page) => void;
  onDuplicate?: (page: Page) => void;
  onDelete?: (page: Page) => void;
  onPublish?: (page: Page) => void;
  onUnpublish?: (page: Page) => void;
  onSchedule?: (page: Page) => void;
  onViewRevisions?: (page: Page) => void;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'dropdown' | 'inline';
}

export const PageActions: React.FC<PageActionsProps> = ({
  page,
  onEdit,
  onDuplicate,
  onDelete,
  onPublish,
  onUnpublish,
  onSchedule,
  onViewRevisions,
  size = 'md',
  variant = 'dropdown',
}) => {
  const navigate = useNavigate();
  const permissions = usePermissions();
  const canAccessLocale = useCanAccessLocale(page.locale?.code);
  const [isLoading, setIsLoading] = useState<string | null>(null);

  // Check locale access for this specific page
  const hasLocaleAccess = useMemo(() => {
    if (!page.locale?.code) return true; // No locale restriction
    return canAccessLocale;
  }, [page.locale?.code, canAccessLocale]);

  // Permission checks with locale scope
  const canView = useMemo(() => 
    permissions.hasPermission('cms.view_page') && hasLocaleAccess
  , [permissions, hasLocaleAccess]);

  const canEdit = useMemo(() => 
    permissions.hasPermission('cms.change_page') && hasLocaleAccess
  , [permissions, hasLocaleAccess]);

  const canDelete = useMemo(() => 
    permissions.hasPermission('cms.delete_page') && hasLocaleAccess
  , [permissions, hasLocaleAccess]);

  const canPublish = useMemo(() => 
    permissions.hasPermission('cms.publish_page') && hasLocaleAccess
  , [permissions, hasLocaleAccess]);

  const canDuplicate = useMemo(() => 
    permissions.hasPermission('cms.add_page') && hasLocaleAccess
  , [permissions, hasLocaleAccess]);

  const canViewRevisions = useMemo(() => 
    permissions.hasPermission('cms.view_pagerevision') && hasLocaleAccess
  , [permissions, hasLocaleAccess]);

  const canSchedule = useMemo(() => 
    permissions.hasPermission('cms.schedule_page') && hasLocaleAccess
  , [permissions, hasLocaleAccess]);

  // Action handlers with permission checks and loading states
  const handleAction = async (action: string, handler?: (page: Page) => void) => {
    if (!hasLocaleAccess) {
      toast.error(`You don't have access to content in ${page.locale?.name || page.locale?.code} locale`);
      return;
    }

    setIsLoading(action);
    try {
      if (handler) {
        await handler(page);
      }
    } finally {
      setIsLoading(null);
    }
  };

  const handleEdit = () => handleAction('edit', onEdit);
  const handleDuplicate = () => handleAction('duplicate', onDuplicate);
  const handleDelete = () => handleAction('delete', onDelete);
  const handlePublish = () => handleAction('publish', onPublish);
  const handleUnpublish = () => handleAction('unpublish', onUnpublish);
  const handleSchedule = () => handleAction('schedule', onSchedule);
  const handleViewRevisions = () => handleAction('revisions', onViewRevisions);

  const handleNavigate = () => {
    if (canView) {
      navigate(`/pages/${page.slug}`);
    }
  };

  const handleOpenInNewTab = () => {
    if (canView) {
      window.open(`/pages/${page.slug}`, '_blank');
    }
  };

  // Don't render if user can't view the page
  if (!canView) {
    return null;
  }

  if (variant === 'inline') {
    return (
      <div className="flex items-center gap-2">
        <PermissionGuard permissions={['cms.view_page']} locales={page.locale?.code ? [page.locale.code] : undefined}>
          <Button 
            variant="ghost" 
            size={size}
            onClick={handleNavigate}
            disabled={isLoading === 'navigate'}
          >
            <Eye className="w-4 h-4" />
          </Button>
        </PermissionGuard>

        <PermissionGuard permissions={['cms.change_page']} locales={page.locale?.code ? [page.locale.code] : undefined}>
          <Button 
            variant="ghost" 
            size={size}
            onClick={handleEdit}
            disabled={!onEdit || isLoading === 'edit'}
          >
            <Edit className="w-4 h-4" />
          </Button>
        </PermissionGuard>

        {page.status === 'draft' && (
          <PermissionGuard permissions={['cms.publish_page']} locales={page.locale?.code ? [page.locale.code] : undefined}>
            <Button 
              variant="default" 
              size={size}
              onClick={handlePublish}
              disabled={!onPublish || isLoading === 'publish'}
            >
              {isLoading === 'publish' ? 'Publishing...' : 'Publish'}
            </Button>
          </PermissionGuard>
        )}

        {page.status === 'published' && (
          <PermissionGuard permissions={['cms.publish_page']} locales={page.locale?.code ? [page.locale.code] : undefined}>
            <Button 
              variant="outline" 
              size={size}
              onClick={handleUnpublish}
              disabled={!onUnpublish || isLoading === 'unpublish'}
            >
              {isLoading === 'unpublish' ? 'Unpublishing...' : 'Unpublish'}
            </Button>
          </PermissionGuard>
        )}

        <PermissionGuard permissions={['cms.delete_page']} locales={page.locale?.code ? [page.locale.code] : undefined}>
          <Button 
            variant="ghost" 
            size={size}
            onClick={handleDelete}
            disabled={!onDelete || isLoading === 'delete'}
          >
            <Trash2 className="w-4 h-4 text-destructive" />
          </Button>
        </PermissionGuard>
      </div>
    );
  }

  // Dropdown variant
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="h-8 w-8 p-0"
          disabled={isLoading !== null}
        >
          <span className="sr-only">Open menu</span>
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {/* View Actions */}
        <PermissionGuard permissions={['cms.view_page']} locales={page.locale?.code ? [page.locale.code] : undefined} showFallback={false}>
          <DropdownMenuItem onClick={handleNavigate}>
            <Eye className="w-4 h-4 mr-2" />
            View Page
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleOpenInNewTab}>
            <ExternalLink className="w-4 h-4 mr-2" />
            Open in New Tab
          </DropdownMenuItem>
        </PermissionGuard>

        {/* Edit Actions */}
        <PermissionGuard permissions={['cms.change_page']} locales={page.locale?.code ? [page.locale.code] : undefined} showFallback={false}>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleEdit} disabled={!onEdit || isLoading === 'edit'}>
            <Edit className="w-4 h-4 mr-2" />
            {isLoading === 'edit' ? 'Editing...' : 'Edit'}
          </DropdownMenuItem>
        </PermissionGuard>

        <PermissionGuard permissions={['cms.add_page']} locales={page.locale?.code ? [page.locale.code] : undefined} showFallback={false}>
          <DropdownMenuItem onClick={handleDuplicate} disabled={!onDuplicate || isLoading === 'duplicate'}>
            <Copy className="w-4 h-4 mr-2" />
            {isLoading === 'duplicate' ? 'Duplicating...' : 'Duplicate'}
          </DropdownMenuItem>
        </PermissionGuard>

        {/* Publishing Actions */}
        <PermissionGuard permissions={['cms.publish_page']} locales={page.locale?.code ? [page.locale.code] : undefined} showFallback={false}>
          <DropdownMenuSeparator />
          {page.status === 'draft' && (
            <DropdownMenuItem onClick={handlePublish} disabled={!onPublish || isLoading === 'publish'}>
              <Send className="w-4 h-4 mr-2" />
              {isLoading === 'publish' ? 'Publishing...' : 'Publish'}
            </DropdownMenuItem>
          )}
          {page.status === 'published' && (
            <DropdownMenuItem onClick={handleUnpublish} disabled={!onUnpublish || isLoading === 'unpublish'}>
              <Archive className="w-4 h-4 mr-2" />
              {isLoading === 'unpublish' ? 'Unpublishing...' : 'Unpublish'}
            </DropdownMenuItem>
          )}
        </PermissionGuard>

        <PermissionGuard permissions={['cms.schedule_page']} locales={page.locale?.code ? [page.locale.code] : undefined} showFallback={false}>
          <DropdownMenuItem onClick={handleSchedule} disabled={!onSchedule || isLoading === 'schedule'}>
            <Calendar className="w-4 h-4 mr-2" />
            Schedule
          </DropdownMenuItem>
        </PermissionGuard>

        {/* Revision Actions */}
        <PermissionGuard permissions={['cms.view_pagerevision']} locales={page.locale?.code ? [page.locale.code] : undefined} showFallback={false}>
          <DropdownMenuItem onClick={handleViewRevisions} disabled={!onViewRevisions || isLoading === 'revisions'}>
            <Globe className="w-4 h-4 mr-2" />
            View Revisions
          </DropdownMenuItem>
        </PermissionGuard>

        {/* Delete Actions */}
        <PermissionGuard permissions={['cms.delete_page']} locales={page.locale?.code ? [page.locale.code] : undefined} showFallback={false}>
          <DropdownMenuSeparator />
          <DropdownMenuItem 
            onClick={handleDelete} 
            disabled={!onDelete || isLoading === 'delete'}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            {isLoading === 'delete' ? 'Deleting...' : 'Delete'}
          </DropdownMenuItem>
        </PermissionGuard>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default PageActions;