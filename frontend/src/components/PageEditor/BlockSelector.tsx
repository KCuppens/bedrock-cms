import { memo, useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Type,
  Image,
  Layout,
  Grid,
  Megaphone,
  HelpCircle,
  ListFilter,
  LayoutGrid,
  Columns,
} from "lucide-react";
import { api } from "@/lib/api.ts";

interface BlockSelectorProps {
  onAddBlock: (type: string) => void;
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
};

export const BlockSelector = memo(({ onAddBlock }: BlockSelectorProps) => {
  const [blockTypes, setBlockTypes] = useState<BlockType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadBlockTypes = async () => {
      try {
        setLoading(true);

        // Try to load from API first
        const response = await api.blocks.list();
        if (response && response.block_types) {
          setBlockTypes(response.block_types);
          setError(null);
        } else {
          throw new Error('No block types in response');
        }
      } catch (err) {
        console.error('Failed to load block types:', err);
        setError('Failed to load block types');

        // Fallback to hardcoded blocks if API fails
        setBlockTypes([
          { type: "hero", label: "Hero Section", icon: "layout", description: "Large header with title and CTA", category: "Layout" },
          { type: "rich_text", label: "Rich Text", icon: "type", description: "Formatted text content", category: "Content" },
          { type: "image", label: "Image", icon: "image", description: "Single image with caption", category: "Media" },
          { type: "gallery", label: "Image Gallery", icon: "grid", description: "Multiple images in a grid", category: "Media" },
          { type: "columns", label: "Columns", icon: "columns", description: "Multi-column layout", category: "Layout" },
          { type: "cta_band", label: "Call to Action", icon: "megaphone", description: "Button with compelling text", category: "Marketing" },
          { type: "faq", label: "FAQ", icon: "help-circle", description: "Accordion of questions", category: "Content" },
          { type: "content_detail", label: "Content Detail", icon: "layout-grid", description: "Dynamic content display", category: "Dynamic" },
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
      if (loading) {
        console.warn('Block types API call timed out, using fallback');
        setBlockTypes([
          { type: "hero", label: "Hero Section", icon: "layout", description: "Large header with title and CTA", category: "Layout" },
          { type: "rich_text", label: "Rich Text", icon: "type", description: "Formatted text content", category: "Content" },
          { type: "image", label: "Image", icon: "image", description: "Single image with caption", category: "Media" },
          { type: "gallery", label: "Image Gallery", icon: "grid", description: "Multiple images in a grid", category: "Media" },
          { type: "columns", label: "Columns", icon: "columns", description: "Multi-column layout", category: "Layout" },
          { type: "cta_band", label: "Call to Action", icon: "megaphone", description: "Button with compelling text", category: "Marketing" },
          { type: "faq", label: "FAQ", icon: "help-circle", description: "Accordion of questions", category: "Content" },
          { type: "content_detail", label: "Content Detail", icon: "layout-grid", description: "Dynamic content display", category: "Dynamic" },
        ]);
        setLoading(false);
      }
    }, 3000); // 3 second timeout

    loadBlockTypes();

    return () => clearTimeout(timeoutId);
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="cursor-pointer">
            <CardContent className="p-3">
              <div className="flex items-start gap-3">
                <Skeleton className="h-8 w-8 rounded" />
                <div className="flex-1 space-y-1">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-3 w-full" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      {blockTypes.map(({ type, label, icon, description }) => {
        const Icon = iconMap[icon] || Layout; // Fallback to Layout icon

        return (
          <Card
            key={type}
            className="cursor-pointer hover:border-primary transition-colors"
            onClick={() => onAddBlock(type)}
          >
            <CardContent className="p-3">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-muted rounded">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{label}</div>
                  <div className="text-xs text-muted-foreground">
                    {description}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
});

BlockSelector.displayName = "BlockSelector";
