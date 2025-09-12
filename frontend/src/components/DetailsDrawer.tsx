import { useState, useEffect, useRef, useCallback } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Settings,
  Search,
  Calendar,
  History,
  Link,
  Eye,
  Globe,
  Code,
  Clock,
  Save,
  Loader2,
  RotateCcw
} from "lucide-react";
import { PageData } from "@/pages/PageEditor";
import { InlineEditField } from "@/components/InlineEditField";
import { api } from "@/lib/api.ts";
import { useToast } from "@/hooks/use-toast";

interface DetailsDrawerProps {
  page: PageData;
  isOpen: boolean;
  onClose: () => void;
  onPageUpdate: (page: PageData) => void;
}

export const DetailsDrawer = ({ page, isOpen, onClose, onPageUpdate }: DetailsDrawerProps) => {
  const [activeTab, setActiveTab] = useState("page");

  // Local state for form fields
  const [localPageData, setLocalPageData] = useState<PageData>(page);
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const { toast } = useToast();

  // Update local state when page prop changes
  useEffect(() => {
    setLocalPageData(page);
    setHasUnsavedChanges(false);
  }, [page.id]);

  // Update page data - no auto-save
  const updatePage = (updates: Partial<PageData>) => {
    setLocalPageData(prev => ({ ...prev, ...updates }));
    setHasUnsavedChanges(true);
  };

  const updateSeo = (updates: Partial<PageData['seo']>) => {
    setLocalPageData(prev => ({
      ...prev,
      seo: { ...prev.seo, ...updates }
    }));
    setHasUnsavedChanges(true);
  };

  // Manual save
  const saveNow = async () => {
    if (!localPageData.id) return;

    setIsSaving(true);
    try {
      await api.cms.pages.update(parseInt(localPageData.id), {
        title: localPageData.title,
        slug: localPageData.slug,
        seo: localPageData.seo,
      });

      setHasUnsavedChanges(false);
      onPageUpdate(localPageData);

      toast({
        title: "Saved",
        description: "Page details saved successfully",
      });
    } catch (error) {
      console.error('Save failed:', error);
      toast({
        title: "Error",
        description: "Failed to save changes",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const saveChanges = async () => {
    try {
      await saveNow();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save page details",
        variant: "destructive",
      });
    }
  };

  return (
    <>
      <Sheet open={isOpen} onOpenChange={() => onClose()}>
        <SheetContent className="w-[500px] sm:max-w-[500px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center justify-between">
              <span>Page Details</span>
              <div className="flex items-center gap-2">
                {hasUnsavedChanges && (
                  <Badge variant="secondary">
                    Unsaved changes
                  </Badge>
                )}
                {isSaving && (
                  <Badge variant="outline">
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    Saving...
                  </Badge>
                )}
                <Button
                  size="sm"
                  onClick={saveChanges}
                  disabled={isSaving || !hasUnsavedChanges}
                  variant={hasUnsavedChanges ? "default" : "outline"}
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-1" />
                      Save
                    </>
                  )}
                </Button>
              </div>
            </SheetTitle>
          </SheetHeader>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="page">Page</TabsTrigger>
              <TabsTrigger value="seo">SEO</TabsTrigger>
              <TabsTrigger value="advanced">Advanced</TabsTrigger>
            </TabsList>

            <ScrollArea className="h-[calc(100vh-200px)] mt-4">
              <TabsContent value="page" className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title" className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Page Title
                  </Label>
                  <Input
                    id="title"
                    value={localPageData.title}
                    onChange={(e) => updatePage({ title: e.target.value })}
                    placeholder="Enter page title"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="slug" className="flex items-center gap-2">
                    <Link className="h-4 w-4" />
                    URL Slug
                  </Label>
                  <Input
                    id="slug"
                    value={localPageData.slug}
                    onChange={(e) => updatePage({ slug: e.target.value })}
                    placeholder="page-url-slug"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="parent" className="flex items-center gap-2">
                    Parent Page
                  </Label>
                  <Select value={localPageData.parent || "none"} onValueChange={(value) => updatePage({ parent: value === "none" ? undefined : value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select parent page" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No parent (root level)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="visibility" className="flex items-center gap-2">
                      <Eye className="h-4 w-4" />
                      Visibility
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Make this page visible to visitors
                    </p>
                  </div>
                  <Switch
                    id="visibility"
                    checked={localPageData.is_published}
                    onCheckedChange={(checked) => updatePage({ is_published: checked })}
                  />
                </div>
              </TabsContent>

              <TabsContent value="seo" className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="seo-title" className="flex items-center gap-2">
                    <Search className="h-4 w-4" />
                    SEO Title
                  </Label>
                  <Input
                    id="seo-title"
                    value={localPageData.seo.title || ""}
                    onChange={(e) => updateSeo({ title: e.target.value })}
                    placeholder="SEO optimized title"
                  />
                  <p className="text-xs text-muted-foreground">
                    Recommended: 50-60 characters
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="seo-description" className="flex items-center gap-2">
                    Meta Description
                  </Label>
                  <Textarea
                    id="seo-description"
                    value={localPageData.seo.description || ""}
                    onChange={(e) => updateSeo({ description: e.target.value })}
                    placeholder="Brief page description for search engines"
                    className="min-h-[100px]"
                  />
                  <p className="text-xs text-muted-foreground">
                    Recommended: 150-160 characters
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="canonical" className="flex items-center gap-2">
                    <Link className="h-4 w-4" />
                    Canonical URL
                  </Label>
                  <Input
                    id="canonical"
                    value={localPageData.seo.canonical || ""}
                    onChange={(e) => updateSeo({ canonical: e.target.value })}
                    placeholder="https://example.com/page"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="robots" className="flex items-center gap-2">
                    Robots Meta
                  </Label>
                  <Select
                    value={localPageData.seo.robots || "index,follow"}
                    onValueChange={(value) => updateSeo({ robots: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="index,follow">Index, Follow</SelectItem>
                      <SelectItem value="noindex,follow">No Index, Follow</SelectItem>
                      <SelectItem value="index,nofollow">Index, No Follow</SelectItem>
                      <SelectItem value="noindex,nofollow">No Index, No Follow</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label htmlFor="jsonld" className="flex items-center gap-2">
                    <Code className="h-4 w-4" />
                    JSON-LD Schema
                  </Label>
                  <Textarea
                    id="jsonld"
                    value={localPageData.seo.jsonLd || ""}
                    onChange={(e) => updateSeo({ jsonLd: e.target.value })}
                    placeholder='{"@context": "https://schema.org", ...}'
                    className="min-h-[150px] font-mono text-xs"
                  />
                </div>
              </TabsContent>

              <TabsContent value="advanced" className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="template">Page Template</Label>
                  <Select value={localPageData.template || "default"}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">Default</SelectItem>
                      <SelectItem value="landing">Landing Page</SelectItem>
                      <SelectItem value="blog">Blog Post</SelectItem>
                      <SelectItem value="product">Product Page</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Publishing Schedule
                  </Label>

                  <div className="space-y-2">
                    <Label htmlFor="publish-at" className="text-sm">Publish At</Label>
                    <Input
                      id="publish-at"
                      type="datetime-local"
                      value={localPageData.schedule?.publishAt || ""}
                      onChange={(e) => updatePage({
                        schedule: { ...localPageData.schedule, publishAt: e.target.value }
                      })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="unpublish-at" className="text-sm">Unpublish At</Label>
                    <Input
                      id="unpublish-at"
                      type="datetime-local"
                      value={localPageData.schedule?.unpublishAt || ""}
                      onChange={(e) => updatePage({
                        schedule: { ...localPageData.schedule, unpublishAt: e.target.value }
                      })}
                    />
                  </div>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Globe className="h-4 w-4" />
                    Language Settings
                  </Label>
                  <Select value={localPageData.locale || "en"}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="es">Spanish</SelectItem>
                      <SelectItem value="fr">French</SelectItem>
                      <SelectItem value="de">German</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </TabsContent>
            </ScrollArea>
          </Tabs>

          <div className="flex justify-between items-center gap-2 mt-4 pt-4 border-t">
            <div className="flex items-center gap-2">
              {hasUnsavedChanges && (
                <Badge variant="secondary">
                  <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                  Unsaved changes
                </Badge>
              )}
              {isSaving && (
                <Badge variant="outline">
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  Saving...
                </Badge>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={saveChanges}
                disabled={isSaving || !hasUnsavedChanges}
                variant={hasUnsavedChanges ? "default" : "outline"}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
};
