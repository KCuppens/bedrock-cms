import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Plus, Tag, Search, Edit, Trash2, Filter, TrendingUp } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import TagModal from "@/components/modals/TagModal";
import DeleteConfirmModal from "@/components/modals/DeleteConfirmModal";
import React, { useState, useEffect, useCallback, useMemo, memo } from "react";
import { api } from "@/lib/api.ts";
import { useToast } from "@/hooks/use-toast";

// Memoized Tag Card Component
const TagCard = memo<{
  tag: Tag;
  onEdit: (tag: Tag) => void;
  onDelete: (tag: Tag) => void;
}>(({ tag, onEdit, onDelete }) => {
  const handleEdit = useCallback(() => onEdit(tag), [tag, onEdit]);
  const handleDelete = useCallback(() => onDelete(tag), [tag, onDelete]);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: tag.color ? `${tag.color}20` : '#f3f4f6' }}
            >
              <Tag
                className="w-5 h-5"
                style={{ color: tag.color || '#6b7280' }}
              />
            </div>
            <div>
              <CardTitle className="text-lg">{tag.name}</CardTitle>
              <CardDescription>{tag.description || 'No description'}</CardDescription>
            </div>
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" onClick={handleEdit}>
              <Edit className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleDelete}>
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              {tag.post_count} posts
            </Badge>
            {tag.trending && (
              <Badge variant="outline" className="text-orange-600">
                <TrendingUp className="w-3 h-3 mr-1" />
                Trending
              </Badge>
            )}
          </div>
          <code className="text-xs bg-muted px-2 py-1 rounded">
            #{tag.slug}
          </code>
        </div>
      </CardContent>
    </Card>
  );
});

TagCard.displayName = 'TagCard';

interface Tag {
  id: number;
  name: string;
  slug: string;
  description?: string;
  color?: string;
  post_count: number;
  trending?: boolean;
  is_active?: boolean;
  created_at: string;
  updated_at: string;
}

const Tags = memo(() => {
  const { toast } = useToast();

  // Modal states
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [tagModalMode, setTagModalMode] = useState<'add' | 'edit'>('add');
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [tagToDelete, setTagToDelete] = useState<Tag | null>(null);

  // Data states
  const [tags, setTags] = useState<Tag[]>([]);
  const [trendingTags, setTrendingTags] = useState<Tag[]>([]);
  const [unusedTags, setUnusedTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTab, setActiveTab] = useState("all");

  // Fetch all tags data
  const fetchTags = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all tags
      const allTagsResponse = await api.cms.tags.list({ search: searchTerm || undefined });
      const allTags = allTagsResponse.results || [];

      setTags(allTags);
      // Filter trending tags based on the trending field
      setTrendingTags(allTags.filter(tag => tag.trending === true));
      // Filter unused tags (tags with 0 posts)
      setUnusedTags(allTags.filter(tag => tag.post_count === 0));

    } catch (error: any) {
      console.error('Failed to fetch tags:', error);
      setError(error.message || 'Failed to load tags');
      toast({
        title: "Error",
        description: "Failed to load tags. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [searchTerm, toast]);

  // Load data on component mount and when dependencies change
  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  const handleAddTag = useCallback(() => {
    setTagModalMode('add');
    setEditingTag(null);
    setTagModalOpen(true);
  }, []);

  const handleEditTag = useCallback((tag: Tag) => {
    setTagModalMode('edit');
    setEditingTag(tag);
    setTagModalOpen(true);
  }, []);

  const handleDeleteTag = useCallback((tag: Tag) => {
    setTagToDelete(tag);
    setDeleteModalOpen(true);
  }, []);

  const handleSaveTag = useCallback(async (tagData: { name: string; description?: string; color?: string }) => {
    try {
      if (tagModalMode === 'add') {
        await api.cms.tags.create(tagData);
        toast({
          title: "Success",
          description: "Tag created successfully.",
        });
      } else if (editingTag) {
        await api.cms.tags.update(editingTag.slug, tagData);
        toast({
          title: "Success",
          description: "Tag updated successfully.",
        });
      }

      // Refresh tags list
      await fetchTags();
      setTagModalOpen(false);
      setEditingTag(null);

    } catch (error: any) {
      console.error('Failed to save tag:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to save tag. Please try again.",
        variant: "destructive",
      });
    }
  }, [tagModalMode, editingTag, fetchTags, toast]);

  const handleConfirmDelete = useCallback(async () => {
    if (tagToDelete) {
      try {
        await api.cms.tags.delete(tagToDelete.slug);
        toast({
          title: "Success",
          description: "Tag deleted successfully.",
        });

        // Refresh tags list
        await fetchTags();
        setDeleteModalOpen(false);
        setTagToDelete(null);

      } catch (error: any) {
        console.error('Failed to delete tag:', error);
        toast({
          title: "Error",
          description: error.message || "Failed to delete tag. Please try again.",
          variant: "destructive",
        });
      }
    }
  }, [tagToDelete, fetchTags, toast]);

  const popularTags = useMemo(() => tags.filter(tag => tag.post_count >= 10), [tags]);

  const getCurrentTags = useCallback(() => {
    switch (activeTab) {
      case 'trending':
        return trendingTags;
      case 'popular':
        return popularTags;
      case 'unused':
        return unusedTags;
      default:
        return tags;
    }
  }, [activeTab, trendingTags, popularTags, unusedTags, tags]);

  const currentTags = useMemo(() => getCurrentTags(), [getCurrentTags]);

  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />
        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />
          <main className="flex-1 p-8">
            <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Tags</h1>
              <p className="text-muted-foreground">Manage content tags and labels</p>
            </div>
            <Button onClick={handleAddTag}>
              <Plus className="w-4 h-4 mr-2" />
              New Tag
            </Button>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="all">All Tags</TabsTrigger>
                <TabsTrigger value="trending">Trending</TabsTrigger>
                <TabsTrigger value="popular">Popular</TabsTrigger>
                <TabsTrigger value="unused">Unused</TabsTrigger>
              </TabsList>

              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Search tags..."
                    className="pl-10 w-64"
                    value={searchTerm}
                    onChange={useCallback((e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value), [])}
                  />
                </div>
                <Button variant="outline" size="sm">
                  <Filter className="w-4 h-4 mr-2" />
                  Filter
                </Button>
              </div>
            </div>

            <TabsContent value="all" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {loading ? (
                <div className="col-span-full flex items-center justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mr-2" />
                  Loading tags...
                </div>
              ) : error ? (
                <div className="col-span-full text-center py-8 text-destructive">
                  {error}
                </div>
              ) : currentTags.length === 0 ? (
                <div className="col-span-full text-center py-8 text-muted-foreground">
                  No tags found.
                </div>
              ) : (
                currentTags.map((tag) => (
                  <TagCard
                    key={tag.id}
                    tag={tag}
                    onEdit={handleEditTag}
                    onDelete={handleDeleteTag}
                  />
                ))
              )}
            </TabsContent>

            <TabsContent value="trending" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {loading ? (
                <div className="col-span-full flex items-center justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mr-2" />
                  Loading trending tags...
                </div>
              ) : currentTags.length === 0 ? (
                <div className="col-span-full text-center py-8 text-muted-foreground">
                  No trending tags found.
                </div>
              ) : (
                currentTags.map((tag) => (
                  <TagCard
                    key={tag.id}
                    tag={tag}
                    onEdit={handleEditTag}
                    onDelete={handleDeleteTag}
                  />
                ))
              )}
            </TabsContent>

            <TabsContent value="popular" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {loading ? (
                <div className="col-span-full flex items-center justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mr-2" />
                  Loading popular tags...
                </div>
              ) : currentTags.length === 0 ? (
                <div className="col-span-full text-center py-8 text-muted-foreground">
                  No popular tags found.
                </div>
              ) : (
                currentTags.map((tag) => (
                  <TagCard
                    key={tag.id}
                    tag={tag}
                    onEdit={handleEditTag}
                    onDelete={handleDeleteTag}
                  />
                ))
              )}
            </TabsContent>

            <TabsContent value="unused" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {loading ? (
                <div className="col-span-full flex items-center justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mr-2" />
                  Loading unused tags...
                </div>
              ) : currentTags.length === 0 ? (
                <div className="col-span-full text-center py-8 text-muted-foreground">
                  No unused tags found.
                </div>
              ) : (
                currentTags.map((tag) => (
                  <TagCard
                    key={tag.id}
                    tag={tag}
                    onEdit={handleEditTag}
                    onDelete={handleDeleteTag}
                  />
                ))
              )}
            </TabsContent>
          </Tabs>

          {/* Modals */}
          <TagModal
            open={tagModalOpen}
            onOpenChange={setTagModalOpen}
            mode={tagModalMode}
            tag={editingTag}
            onSave={handleSaveTag}
          />

          <DeleteConfirmModal
            open={deleteModalOpen}
            onOpenChange={setDeleteModalOpen}
            title="Delete Tag"
            description="This action cannot be undone. This will permanently delete the tag."
            itemName={tagToDelete?.name || ''}
            onConfirm={handleConfirmDelete}
            warningMessage={tagToDelete?.post_count ? `This tag is used in ${tagToDelete.post_count} posts.` : undefined}
          />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
});

Tags.displayName = 'Tags';
export default Tags;