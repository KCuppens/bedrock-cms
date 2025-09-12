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
  Settings
} from "lucide-react";
import { PageData } from "@/pages/PageEditor";

interface PageEditorTopBarProps {
  page: PageData;
  onPageUpdate: (page: PageData) => void;
  onDrawerToggle: () => void;
}

export const PageEditorTopBar = ({
  page,
  onPageUpdate,
  onDrawerToggle
}: PageEditorTopBarProps) => {
  const formatLastSaved = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const statusColors = {
    draft: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400",
    published: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400",
    scheduled: "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400"
  };

  return (
    <header className="border-b border-border bg-card px-6 py-3">
      <div className="flex items-center justify-between">
        {/* Left side - Breadcrumb and Status */}
        <div className="flex items-center gap-4">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink href="/">Site</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbLink href="/pages">Pages</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{page.title}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <Badge className={statusColors[page.status]}>
            {page.status.charAt(0).toUpperCase() + page.status.slice(1)}
          </Badge>

          <span className="text-sm text-muted-foreground">
            Last saved: {formatLastSaved(new Date())}
          </span>
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm">
            <Eye className="w-4 h-4 mr-2" />
            Preview
          </Button>

          <Button size="sm">
            <Globe className="w-4 h-4 mr-2" />
            Publish
          </Button>

          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export JSON
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={onDrawerToggle}
          >
            <Settings className="w-4 h-4 mr-2" />
            Details
          </Button>
        </div>
      </div>
    </header>
  );
};