import { memo, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Eye,
  Globe,
  Download,
  Settings,
  Save,
  Loader2,
  Undo,
  Redo,
  History,
  Share2,
} from "lucide-react";
import type { PageData } from "@/pages/PageEditor";

interface PageHeaderProps {
  pageData: PageData;
  hasUnsavedChanges: boolean;
  isSaving: boolean;
  canUndo: boolean;
  canRedo: boolean;
  onSave: () => void;
  onPreview: () => void;
  onPublish: () => void;
  onSettings: () => void;
  onVersionHistory: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onExportJSON: () => void;
}

export const PageHeader = memo((props: PageHeaderProps) => {
  const {
    pageData,
    hasUnsavedChanges,
    isSaving,
    canUndo,
    canRedo,
    onSave,
    onPreview,
    onPublish,
    onSettings,
    onVersionHistory,
    onUndo,
    onRedo,
    onExportJSON,
  } = props;

  const handleSave = useCallback(() => {
    if (!isSaving && hasUnsavedChanges) {
      onSave();
    }
  }, [isSaving, hasUnsavedChanges, onSave]);

  const statusColors = {
    draft: "bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400",
    published: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400",
    scheduled: "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400",
  };

  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex items-center justify-between px-6 py-3">
        <div className="flex items-center gap-4">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink href="/pages">Pages</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{pageData.title}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <Badge className={statusColors[pageData.status]}>
            {pageData.status}
          </Badge>
          {pageData.isPresentationPage && (
            <Badge variant="secondary">Presentation Page</Badge>
          )}
          <Badge variant="outline">
            <Globe className="h-3 w-3 mr-1" />
            {pageData.locale}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onUndo}
            disabled={!canUndo}
          >
            <Undo className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRedo}
            disabled={!canRedo}
          >
            <Redo className="h-4 w-4" />
          </Button>
          
          <Button variant="ghost" size="sm" onClick={onVersionHistory}>
            <History className="h-4 w-4 mr-2" />
            Version History
          </Button>

          <Button variant="ghost" size="sm" onClick={onSettings}>
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>

          <Button variant="ghost" size="sm" onClick={onPreview}>
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>

          <Button
            onClick={handleSave}
            disabled={isSaving || !hasUnsavedChanges}
            size="sm"
          >
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save
              </>
            )}
          </Button>

          {pageData.status === "draft" && (
            <Button onClick={onPublish} size="sm">
              <Share2 className="h-4 w-4 mr-2" />
              Publish
            </Button>
          )}

          <Button variant="ghost" size="sm" onClick={onExportJSON}>
            <Download className="h-4 w-4 mr-2" />
            Export JSON
          </Button>
        </div>
      </div>
    </div>
  );
});

PageHeader.displayName = "PageHeader";