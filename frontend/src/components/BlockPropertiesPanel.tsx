import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { 
  X, 
  Settings, 
  Type, 
  Image, 
  Palette,
  Layout,
  Trash2 
} from "lucide-react";
import { Block } from "@/pages/PageEditor";

interface BlockPropertiesPanelProps {
  block: Block | null;
  onBlockUpdate: (blockId: string, updates: Partial<Block>) => void;
  onBlockDelete: (blockId: string) => void;
  onClose: () => void;
}

export const BlockPropertiesPanel = ({ 
  block, 
  onBlockUpdate, 
  onBlockDelete, 
  onClose 
}: BlockPropertiesPanelProps) => {
  if (!block) return null;

  const updateContent = (field: string, value: any) => {
    onBlockUpdate(block.id, {
      content: { ...block.content, [field]: value }
    });
  };

  const renderBlockSettings = () => {
    switch (block.type) {
      case 'hero':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="hero-title">Title</Label>
              <Input
                id="hero-title"
                value={block.content.title || ""}
                onChange={(e) => updateContent('title', e.target.value)}
                placeholder="Enter hero title"
              />
            </div>
            <div>
              <Label htmlFor="hero-subtitle">Subtitle</Label>
              <Textarea
                id="hero-subtitle"
                value={block.content.subtitle || ""}
                onChange={(e) => updateContent('subtitle', e.target.value)}
                placeholder="Enter hero subtitle"
                rows={3}
              />
            </div>
            <div>
              <Label htmlFor="hero-bg">Background Image URL</Label>
              <Input
                id="hero-bg"
                value={block.content.backgroundImage || ""}
                onChange={(e) => {
                  const value = e.target.value;
                  // Prevent CSS gradients or other invalid values from being set
                  if (value && (value.includes('linear-gradient') || value.includes('radial-gradient'))) {
                    return; // Don't update with gradient values
                  }
                  updateContent('backgroundImage', value);
                }}
                placeholder="https://example.com/image.jpg"
              />
            </div>
          </div>
        );

      case 'richtext':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="richtext-content">Content</Label>
              <Textarea
                id="richtext-content"
                value={block.content.html?.replace(/<[^>]*>/g, '') || ""}
                onChange={(e) => updateContent('html', `<p>${e.target.value}</p>`)}
                placeholder="Enter your text content"
                rows={8}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Rich text editing with full toolbar coming soon
              </p>
            </div>
          </div>
        );

      case 'image':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="image-src">Image URL</Label>
              <Input
                id="image-src"
                value={block.content.src || ""}
                onChange={(e) => updateContent('src', e.target.value)}
                placeholder="https://example.com/image.jpg"
              />
            </div>
            <div>
              <Label htmlFor="image-alt">Alt Text</Label>
              <Input
                id="image-alt"
                value={block.content.alt || ""}
                onChange={(e) => updateContent('alt', e.target.value)}
                placeholder="Describe the image"
              />
            </div>
            <div>
              <Label htmlFor="image-caption">Caption</Label>
              <Input
                id="image-caption"
                value={block.content.caption || ""}
                onChange={(e) => updateContent('caption', e.target.value)}
                placeholder="Optional caption"
              />
            </div>
          </div>
        );

      case 'cta':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="cta-title">Title</Label>
              <Input
                id="cta-title"
                value={block.content.title || ""}
                onChange={(e) => updateContent('title', e.target.value)}
                placeholder="Call to action title"
              />
            </div>
            <div>
              <Label htmlFor="cta-button-text">Button Text</Label>
              <Input
                id="cta-button-text"
                value={block.content.button?.text || ""}
                onChange={(e) => updateContent('button', { 
                  ...block.content.button, 
                  text: e.target.value 
                })}
                placeholder="Button text"
              />
            </div>
            <div>
              <Label htmlFor="cta-button-url">Button URL</Label>
              <Input
                id="cta-button-url"
                value={block.content.button?.url || ""}
                onChange={(e) => updateContent('button', { 
                  ...block.content.button, 
                  url: e.target.value 
                })}
                placeholder="https://example.com"
              />
            </div>
          </div>
        );

      case 'columns':
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Column editing interface coming soon. For now, you can edit columns by clicking directly on the content.
            </p>
          </div>
        );

      case 'faq':
        return (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              FAQ editing interface coming soon. Add and edit FAQ items directly in the block.
            </p>
          </div>
        );

      default:
        return (
          <div className="text-center py-8">
            <p className="text-muted-foreground">No settings available for this block type.</p>
          </div>
        );
    }
  };

  const getBlockIcon = () => {
    switch (block.type) {
      case 'hero': return <Layout className="w-4 h-4" />;
      case 'richtext': return <Type className="w-4 h-4" />;
      case 'image': return <Image className="w-4 h-4" />;
      case 'cta': return <Palette className="w-4 h-4" />;
      default: return <Settings className="w-4 h-4" />;
    }
  };

  const getBlockLabel = () => {
    switch (block.type) {
      case 'hero': return 'Hero Section';
      case 'richtext': return 'Rich Text';
      case 'image': return 'Image';
      case 'gallery': return 'Gallery';
      case 'columns': return 'Columns';
      case 'cta': return 'Call to Action';
      case 'faq': return 'FAQ';
      default: return 'Unknown Block';
    }
  };

  return (
    <div className="w-80 bg-card border-l border-border overflow-y-auto">
      <Card className="m-0 border-0 shadow-none">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              {getBlockIcon()}
              {getBlockLabel()}
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {block.type}
            </Badge>
            <Badge variant="outline" className="text-xs">
              ID: {block.id.slice(-6)}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Block Settings */}
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Block Settings
            </h4>
            {renderBlockSettings()}
          </div>

          <Separator />

          {/* Block Actions */}
          <div>
            <h4 className="font-medium mb-3">Actions</h4>
            <div className="space-y-2">
              <Button variant="outline" className="w-full justify-start">
                <Layout className="w-4 h-4 mr-2" />
                Duplicate Block
              </Button>
              <Button 
                variant="destructive" 
                className="w-full justify-start"
                onClick={() => {
                  onBlockDelete(block.id);
                  onClose();
                }}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Block
              </Button>
            </div>
          </div>

          {/* Block Position */}
          <div>
            <h4 className="font-medium mb-3">Position</h4>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="flex-1">
                Move Up
              </Button>
              <Button variant="outline" size="sm" className="flex-1">
                Move Down
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};