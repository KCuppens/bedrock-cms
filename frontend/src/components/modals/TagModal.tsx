import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface Tag {
  id: string;
  name: string;
  count: number;
  trending: boolean;
}

interface TagModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: 'add' | 'edit';
  tag?: Tag;
  onSave: (tag: Partial<Tag>) => void;
}

const TagModal = ({ open, onOpenChange, mode, tag, onSave }: TagModalProps) => {
  const [formData, setFormData] = useState<Partial<Tag>>({
    name: '',
    count: 0,
    trending: false
  });

  useEffect(() => {
    if (mode === 'edit' && tag) {
      setFormData(tag);
    } else {
      setFormData({
        name: '',
        count: 0,
        trending: false
      });
    }
  }, [mode, tag, open]);

  const handleInputChange = (field: keyof Tag, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave(formData);
    onOpenChange(false);
  };

  const isValid = formData.name?.trim();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {mode === 'add' ? 'Create New Tag' : 'Edit Tag'}
          </DialogTitle>
          <DialogDescription>
            {mode === 'add' 
              ? 'Add a new tag to label your content.' 
              : 'Make changes to your tag here.'
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
              placeholder="Tag name..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="count">Post Count</Label>
              <Input
                id="count"
                type="number"
                value={formData.count || 0}
                onChange={(e) => handleInputChange('count', parseInt(e.target.value) || 0)}
                min="0"
              />
            </div>
            <div className="flex items-center space-x-2 pt-6">
              <input
                type="checkbox"
                id="trending"
                checked={formData.trending || false}
                onChange={(e) => handleInputChange('trending', e.target.checked)}
                className="rounded border-border"
              />
              <Label htmlFor="trending">Trending</Label>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!isValid}>
            {mode === 'add' ? 'Create Tag' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default TagModal;