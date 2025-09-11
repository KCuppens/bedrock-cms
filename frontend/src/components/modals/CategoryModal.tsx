import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Category, CategoryCreateRequest } from "@/types/api";

interface CategoryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: 'add' | 'edit';
  category?: Category;
  onSave: (category: Partial<CategoryCreateRequest>) => void;
}

const CategoryModal = ({ open, onOpenChange, mode, category, onSave }: CategoryModalProps) => {
  const [formData, setFormData] = useState<Partial<CategoryCreateRequest>>({
    name: '',
    slug: '',
    description: '',
    color: '#6366f1',
    is_active: true
  });

  useEffect(() => {
    if (mode === 'edit' && category) {
      setFormData({
        name: category.name,
        slug: category.slug,
        description: category.description || '',
        color: category.color || '#6366f1',
        is_active: category.is_active
      });
    } else {
      setFormData({
        name: '',
        slug: '',
        description: '',
        color: '#6366f1',
        is_active: true
      });
    }
  }, [mode, category, open]);

  const handleInputChange = (field: keyof CategoryCreateRequest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Auto-generate slug from name
    if (field === 'name' && value) {
      const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
      setFormData(prev => ({ ...prev, slug }));
    }
  };

  const handleSave = () => {
    onSave(formData);
    onOpenChange(false);
  };

  const isValid = formData.name?.trim() && formData.slug?.trim();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {mode === 'add' ? 'Create New Category' : 'Edit Category'}
          </DialogTitle>
          <DialogDescription>
            {mode === 'add' 
              ? 'Add a new category to organize your content.' 
              : 'Make changes to your category here.'
            }
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div>
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              value={formData.name || ''}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="Category name..."
            />
          </div>

          <div>
            <Label htmlFor="slug">Slug *</Label>
            <Input
              id="slug"
              value={formData.slug || ''}
              onChange={(e) => handleInputChange('slug', e.target.value)}
              placeholder="category-slug"
            />
            <div className="text-sm text-muted-foreground mt-1">
              URL: /category/{formData.slug || 'category-slug'}
            </div>
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description || ''}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Brief description of this category..."
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="color">Color</Label>
            <div className="flex items-center gap-2">
              <Input
                id="color"
                type="color"
                value={formData.color || '#6366f1'}
                onChange={(e) => handleInputChange('color', e.target.value)}
                className="w-16 h-8 p-1 border rounded cursor-pointer"
              />
              <Input
                value={formData.color || '#6366f1'}
                onChange={(e) => handleInputChange('color', e.target.value)}
                placeholder="#6366f1"
                className="flex-1"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!isValid}>
            {mode === 'add' ? 'Create Category' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CategoryModal;