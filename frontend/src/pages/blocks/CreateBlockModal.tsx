import { useState } from "react";
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

interface BlockTypeCategory {
  value: string;
  label: string;
}

interface CreateBlockModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (formData: any) => Promise<void>;
  categories: BlockTypeCategory[];
}

const EDITING_MODES = [
  { value: 'inline', label: 'Inline' },
  { value: 'modal', label: 'Modal' },
  { value: 'sidebar', label: 'Sidebar' }
];

export default function CreateBlockModal({
  open,
  onOpenChange,
  onSubmit,
  categories
}: CreateBlockModalProps) {
  const [formData, setFormData] = useState({
    type: "",
    component: "",
    label: "",
    description: "",
    category: "content",
    icon: "square",
    is_active: true,
    preload: false,
    editing_mode: "inline",
    schema: {},
    default_props: {}
  });

  const handleSubmit = async () => {
    await onSubmit(formData);
    // Reset form after successful submission
    setFormData({
      type: "",
      component: "",
      label: "",
      description: "",
      category: "content",
      icon: "square",
      is_active: true,
      preload: false,
      editing_mode: "inline",
      schema: {},
      default_props: {}
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Block Type</DialogTitle>
          <DialogDescription>
            Add a new block type to your library. Make sure the component exists in your frontend.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="type">Type</Label>
              <Input
                id="type"
                value={formData.type}
                onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
                placeholder="hero, richtext, etc."
              />
            </div>
            <div>
              <Label htmlFor="component">Component</Label>
              <Input
                id="component"
                value={formData.component}
                onChange={(e) => setFormData(prev => ({ ...prev, component: e.target.value }))}
                placeholder="HeroBlock"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="label">Label</Label>
            <Input
              id="label"
              value={formData.label}
              onChange={(e) => setFormData(prev => ({ ...prev, label: e.target.value }))}
              placeholder="Hero Section"
            />
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Large banner section with title and CTA"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="category">Category</Label>
              <Select
                value={formData.category}
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
              <Label htmlFor="editing_mode">Editing Mode</Label>
              <Select
                value={formData.editing_mode}
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
            <Label htmlFor="icon">Icon</Label>
            <Input
              id="icon"
              value={formData.icon}
              onChange={(e) => setFormData(prev => ({ ...prev, icon: e.target.value }))}
              placeholder="layout, type, image, etc."
            />
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, is_active: checked }))}
              />
              <Label>Active</Label>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.preload}
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
          <Button onClick={handleSubmit}>Create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
