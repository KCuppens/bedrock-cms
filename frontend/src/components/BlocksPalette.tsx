import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Star,
  Type,
  Image,
  Grid,
  Columns,
  Megaphone,
  HelpCircle,
  FileText,
  Sparkles,
  Layout,
  ListFilter,
  LayoutGrid
} from "lucide-react";
import { Block } from "@/pages/PageEditor";
import { api } from "@/lib/api.ts";

interface BlocksPaletteProps {
  onAddBlock: (type: Block['type'], position: number) => void;
  editMode: boolean;
}

interface BlockType {
  type: string;
  label: string;
  description: string;
  category: string;
  icon: string;
}

// Icon mapping for the block types
const iconMap: Record<string, any> = {
  layout: Layout,
  type: Type,
  image: Image,
  grid: Grid,
  columns: Columns,
  megaphone: Megaphone,
  "help-circle": HelpCircle,
  "list-filter": ListFilter,
  "layout-grid": LayoutGrid,
  star: Star,
};

const templates = [
  {
    name: 'About Page',
    description: 'Hero + rich text + team section',
    blocks: ['hero', 'richtext', 'columns']
  },
  {
    name: 'Landing Page',
    description: 'Hero + features + CTA + FAQ',
    blocks: ['hero', 'columns', 'cta', 'faq']
  },
  {
    name: 'Portfolio',
    description: 'Hero + gallery + about',
    blocks: ['hero', 'gallery', 'richtext']
  }
];

export const BlocksPalette = ({ onAddBlock, editMode }: BlocksPaletteProps) => {
  const [blockTypes, setBlockTypes] = useState<BlockType[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadBlockTypes = async () => {
      if (!editMode) {
        setLoading(false);
        return;
      }
      
      try {
        setLoading(true);
        
        // Try to load from API first
        const response = await api.blocks.list();
        if (response && response.block_types) {
          setBlockTypes(response.block_types);
        } else {
          throw new Error('No block types in response');
        }
      } catch (err) {
        console.error('Failed to load block types:', err);
        
        // Fallback to hardcoded blocks if API fails
        setBlockTypes([
          { type: "hero", label: "Hero", icon: "layout", description: "Large banner with title and subtitle", category: "Layout" },
          { type: "rich_text", label: "Rich Text", icon: "type", description: "Formatted text content", category: "Content" },
          { type: "image", label: "Image", icon: "image", description: "Single image with optional caption", category: "Media" },
          { type: "gallery", label: "Gallery", icon: "grid", description: "Collection of images", category: "Media" },
          { type: "columns", label: "Columns", icon: "columns", description: "Multi-column layout", category: "Layout" },
          { type: "cta_band", label: "CTA Band", icon: "megaphone", description: "Call-to-action section", category: "Marketing" },
          { type: "faq", label: "FAQ", icon: "help-circle", description: "Frequently asked questions", category: "Content" },
        ]);
      } finally {
        // Set a timeout to ensure loading state doesn't get stuck
        setTimeout(() => {
          setLoading(false);
        }, 100);
      }
    };

    // Add a maximum timeout to prevent indefinite loading
    const timeoutId = setTimeout(() => {
      if (loading && editMode) {
        console.warn('Block types API call timed out, using fallback');
        setBlockTypes([
          { type: "hero", label: "Hero", icon: "layout", description: "Large banner with title and subtitle", category: "Layout" },
          { type: "rich_text", label: "Rich Text", icon: "type", description: "Formatted text content", category: "Content" },
          { type: "image", label: "Image", icon: "image", description: "Single image with optional caption", category: "Media" },
          { type: "gallery", label: "Gallery", icon: "grid", description: "Collection of images", category: "Media" },
          { type: "columns", label: "Columns", icon: "columns", description: "Multi-column layout", category: "Layout" },
          { type: "cta_band", label: "CTA Band", icon: "megaphone", description: "Call-to-action section", category: "Marketing" },
          { type: "faq", label: "FAQ", icon: "help-circle", description: "Frequently asked questions", category: "Content" },
        ]);
        setLoading(false);
      }
    }, 3000); // 3 second timeout

    loadBlockTypes();

    return () => clearTimeout(timeoutId);
  }, [editMode]);

  if (!editMode) {
    return (
      <div className="w-64 bg-muted/30 border-r border-border p-4">
        <div className="text-center text-muted-foreground">
          <FileText className="w-8 h-8 mx-auto mb-2" />
          <p className="text-sm">Enable edit mode to see blocks palette</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-64 bg-card border-r border-border overflow-y-auto">
      <div className="p-4 space-y-6">
        
        {/* Block Types */}
        <div>
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Grid className="w-4 h-4" />
            Blocks
          </h3>
          <div className="space-y-2">
            {loading ? (
              // Loading skeleton
              Array.from({ length: 4 }).map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-3">
                    <div className="flex items-start gap-3">
                      <Skeleton className="h-8 w-8 rounded-md" />
                      <div className="flex-1 space-y-1">
                        <Skeleton className="h-4 w-16" />
                        <Skeleton className="h-3 w-full" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              blockTypes.map((block) => {
                const Icon = iconMap[block.icon] || Layout; // Fallback to Layout icon
                
                return (
                  <Card 
                    key={block.type}
                    className="cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => onAddBlock(block.type as Block['type'], 999)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary/10 rounded-md">
                          <Icon className="w-4 h-4 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-sm">{block.label}</h4>
                          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                            {block.description}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>
        </div>

        <Separator />

        {/* Templates */}
        <div>
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Templates
          </h3>
          <div className="space-y-3">
            {templates.map((template, idx) => (
              <Card 
                key={idx}
                className="cursor-pointer hover:bg-muted/50 transition-colors"
              >
                <CardContent className="p-3">
                  <h4 className="font-medium text-sm mb-1">{template.name}</h4>
                  <p className="text-xs text-muted-foreground mb-2">
                    {template.description}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {template.blocks.map((blockType, blockIdx) => (
                      <span 
                        key={blockIdx}
                        className="px-2 py-1 bg-muted text-xs rounded"
                      >
                        {blockType}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <Separator />

        {/* Quick Actions */}
        <div>
          <h3 className="font-semibold mb-3">Quick Actions</h3>
          <div className="space-y-2">
            <Button variant="outline" className="w-full justify-start text-sm">
              <FileText className="w-4 h-4 mr-2" />
              Import from URL
            </Button>
            <Button variant="outline" className="w-full justify-start text-sm">
              <Grid className="w-4 h-4 mr-2" />
              Save as Template
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};