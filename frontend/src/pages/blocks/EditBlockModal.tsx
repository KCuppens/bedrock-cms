import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface BlockType {
  id: number;
  type: string;
  component: string;
  label: string;
  description: string;
  category: string;
  icon: string;
  is_active: boolean;
  preload: boolean;
  editing_mode: string;
  schema: Record<string, any>;
  default_props: Record<string, any>;
}

interface BlockTypeCategory {
  value: string;
  label: string;
}

interface EditBlockModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (formData: any) => Promise<void>;
  blockType: BlockType | null;
  categories: BlockTypeCategory[];
}

const EDITING_MODES = [
  { value: 'inline', label: 'Inline' },
  { value: 'modal', label: 'Modal' },
  { value: 'sidebar', label: 'Sidebar' }
];

export default function EditBlockModal({
  open,
  onOpenChange,
  onSubmit,
  blockType,
  categories
}: EditBlockModalProps) {
  const [formData, setFormData] = useState<Partial<BlockType>>({});

  useEffect(() => {
    if (blockType) {
      setFormData({
        component: blockType.component,
        label: blockType.label,
        description: blockType.description,
        category: blockType.category,
        icon: blockType.icon,
        is_active: blockType.is_active,
        preload: blockType.preload,
        editing_mode: blockType.editing_mode,
        schema: blockType.schema,
        default_props: blockType.default_props
      });
    }
  }, [blockType]);

  const handleSubmit = async () => {
    await onSubmit(formData);
  };

  if (!blockType) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Block Type</DialogTitle>
          <DialogDescription>
            Update the block type configuration. Type cannot be changed after creation.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="edit-component">Component</Label>
            <Input
              id="edit-component"
              value={formData.component || ""}
              onChange={(e) => setFormData(prev => ({ ...prev, component: e.target.value }))}
            />
          </div>

          <div>
            <Label htmlFor="edit-label">Label</Label>
            <Input
              id="edit-label"
              value={formData.label || ""}
              onChange={(e) => setFormData(prev => ({ ...prev, label: e.target.value }))}
            />
          </div>

          <div>
            <Label htmlFor="edit-description">Description</Label>
            <Textarea
              id="edit-description"
              value={formData.description || ""}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="edit-category">Category</Label>
              <Select
                value={formData.category || "content"}
                onValueChange={(value) => setFormData(prev => ({ ...prev, category: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {categories.map(category => (
                    <SelectItem key={category.value} value={category.value}>
                      {category.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="edit-editing_mode">Editing Mode</Label>
              <Select
                value={formData.editing_mode || "inline"}
                onValueChange={(value) => setFormData(prev => ({ ...prev, editing_mode: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EDITING_MODES.map(mode => (
                    <SelectItem key={mode.value} value={mode.value}>
                      {mode.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="edit-icon">Icon</Label>
            <Input
              id="edit-icon"
              value={formData.icon || ""}
              onChange={(e) => setFormData(prev => ({ ...prev, icon: e.target.value }))}
            />
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.is_active || false}
                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, is_active: checked }))}
              />
              <Label>Active</Label>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.preload || false}
                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, preload: checked }))}
              />
              <Label>Preload</Label>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>Update</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}