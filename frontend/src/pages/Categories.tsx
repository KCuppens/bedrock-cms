import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Plus, Folder, Edit, Trash2 } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import CategoryModal from "@/components/modals/CategoryModal";
import DeleteConfirmModal from "@/components/modals/DeleteConfirmModal";
import React, { useState, useEffect, useCallback, useMemo, memo } from "react";
import { api } from "@/lib/api.ts";
import { Category, CategoryCreateRequest } from "@/types/api";
import { toast } from "sonner";

// Memoized Category Card Component
const CategoryCard = memo<{
  category: Category;
  onEdit: (category: Category) => void;
  onDelete: (category: Category) => void;
}>(({ category, onEdit, onDelete }) => {
  const handleEdit = useCallback(() => onEdit(category), [category, onEdit]);
  const handleDelete = useCallback(() => onDelete(category), [category, onDelete]);

  return (
    <Card key={category.id} className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
              <Folder className="w-5 h-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-lg">{category.name}</CardTitle>
              <CardDescription>{category.description}</CardDescription>
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
          <Badge variant="secondary">
            {category.post_count || 0} posts
          </Badge>
          <code className="text-xs bg-muted px-2 py-1 rounded">
            /{category.slug}
          </code>
        </div>
      </CardContent>
    </Card>
  );
});

CategoryCard.displayName = 'CategoryCard';

const Categories = memo(() => {
  // Modal states
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [categoryModalMode, setCategoryModalMode] = useState<'add' | 'edit'>('add');
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [categoryToDelete, setCategoryToDelete] = useState<Category | null>(null);
  
  // Data states
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const loadCategories = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.cms.categories.list();
      setCategories(response.results || []);
    } catch (error) {
      toast.error('Failed to load categories');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load categories
  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  const handleAddCategory = useCallback(() => {
    setCategoryModalMode('add');
    setEditingCategory(null);
    setCategoryModalOpen(true);
  }, []);

  const handleEditCategory = useCallback((category: Category) => {
    setCategoryModalMode('edit');
    setEditingCategory(category);
    setCategoryModalOpen(true);
  }, []);

  const handleDeleteCategory = useCallback((category: Category) => {
    setCategoryToDelete(category);
    setDeleteModalOpen(true);
  }, []);

  const handleSaveCategory = useCallback(async (categoryData: Partial<CategoryCreateRequest>) => {
    try {
      if (categoryModalMode === 'add') {
        await api.cms.categories.create(categoryData as CategoryCreateRequest);
        toast.success('Category created successfully');
      } else if (editingCategory) {
        await api.cms.categories.update(editingCategory.id, categoryData);
        toast.success('Category updated successfully');
      }
      setCategoryModalOpen(false);
      loadCategories();
    } catch (error) {
      toast.error(`Failed to ${categoryModalMode === 'add' ? 'create' : 'update'} category`);
      console.error(error);
    }
  }, [categoryModalMode, editingCategory, loadCategories]);

  const handleConfirmDelete = useCallback(async () => {
    if (categoryToDelete) {
      try {
        await api.cms.categories.delete(categoryToDelete.id);
        toast.success('Category deleted successfully');
        setDeleteModalOpen(false);
        setCategoryToDelete(null);
        loadCategories();
      } catch (error) {
        toast.error('Failed to delete category');
        console.error(error);
      }
    }
  }, [categoryToDelete, loadCategories]);

  // Memoize category cards to avoid re-renders
  const categoryCards = useMemo(() => 
    categories.map((category) => (
      <CategoryCard
        key={category.id}
        category={category}
        onEdit={handleEditCategory}
        onDelete={handleDeleteCategory}
      />
    )), [categories, handleEditCategory, handleDeleteCategory]
  );

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
              <h1 className="text-3xl font-bold text-foreground">Categories</h1>
              <p className="text-muted-foreground">Organize your content with categories</p>
            </div>
            <Button onClick={handleAddCategory}>
              <Plus className="w-4 h-4 mr-2" />
              New Category
            </Button>
          </div>

          <div className="space-y-4">

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {loading ? (
                <div className="col-span-2 text-center py-8 text-muted-foreground">
                  Loading categories...
                </div>
              ) : categories.length === 0 ? (
                <div className="col-span-2 text-center py-8 text-muted-foreground">
                  No categories found
                </div>
              ) : (
                categoryCards
              )}
            </div>

          </div>

          {/* Modals */}
          <CategoryModal
            open={categoryModalOpen}
            onOpenChange={setCategoryModalOpen}
            mode={categoryModalMode}
            category={editingCategory}
            onSave={handleSaveCategory}
          />

          <DeleteConfirmModal
            open={deleteModalOpen}
            onOpenChange={setDeleteModalOpen}
            title="Delete Category"
            description="This action cannot be undone. This will permanently delete the category."
            itemName={categoryToDelete?.name || ''}
            onConfirm={handleConfirmDelete}
            warningMessage={categoryToDelete?.post_count ? `This category has ${categoryToDelete.post_count} posts. They will be uncategorized.` : undefined}
          />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
});

Categories.displayName = 'Categories';
export default Categories;