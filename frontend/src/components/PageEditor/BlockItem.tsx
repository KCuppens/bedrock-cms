import { memo } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import {
  GripVertical,
  Edit,
  Copy,
  Trash2,
  MoreVertical,
  Type,
  Image,
  Layout,
  Grid,
  Megaphone,
  HelpCircle,
  ListFilter,
  LayoutGrid,
} from "lucide-react";
import type { Block } from "@/pages/PageEditor";

interface BlockItemProps {
  block: Block;
  onEdit: (block: Block) => void;
  onDuplicate: (blockId: string) => void;
  onDelete: (blockId: string) => void;
}

const blockIcons: Record<string, React.ReactNode> = {
  hero: <Layout className="h-4 w-4" />,
  richtext: <Type className="h-4 w-4" />,
  image: <Image className="h-4 w-4" />,
  gallery: <Grid className="h-4 w-4" />,
  columns: <LayoutGrid className="h-4 w-4" />,
  cta: <Megaphone className="h-4 w-4" />,
  faq: <HelpCircle className="h-4 w-4" />,
  collection_list: <ListFilter className="h-4 w-4" />,
  content_detail: <LayoutGrid className="h-4 w-4" />,
};

const blockTitles: Record<string, string> = {
  hero: "Hero Section",
  richtext: "Rich Text",
  image: "Image",
  gallery: "Image Gallery",
  columns: "Columns",
  cta: "Call to Action",
  faq: "FAQ",
  collection_list: "Collection List",
  content_detail: "Content Detail",
};

export const BlockItem = memo(({ block, onEdit, onDuplicate, onDelete }: BlockItemProps) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: block.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const getBlockDescription = (block: Block) => {
    switch (block.type) {
      case "hero":
        return block.content.title || "No title set";
      case "richtext":
        return block.content.text?.substring(0, 100) || "No content";
      case "image":
        return block.content.alt || "No alt text";
      case "gallery":
        return `${block.content.images?.length || 0} images`;
      case "columns":
        return `${block.content.columns?.length || 0} columns`;
      case "cta":
        return block.content.buttonText || "No button text";
      case "faq":
        return `${block.content.items?.length || 0} questions`;
      case "collection_list":
        return `Collection: ${block.content.collectionName || "Not set"}`;
      case "content_detail":
        return `${block.content.showTitle ? "Title, " : ""}${
          block.content.showContent ? "Content" : ""
        }`;
      default:
        return "Configure block";
    }
  };

  return (
    <div ref={setNodeRef} style={style}>
      <Card className="mb-2">
        <CardContent className="p-3">
          <div className="flex items-center gap-2">
            <div
              {...attributes}
              {...listeners}
              className="cursor-move text-muted-foreground hover:text-foreground"
            >
              <GripVertical className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-2 flex-1">
              {blockIcons[block.type]}
              <div className="flex-1">
                <div className="font-medium text-sm">
                  {blockTitles[block.type]}
                </div>
                <div className="text-xs text-muted-foreground truncate max-w-md">
                  {getBlockDescription(block)}
                </div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(block)}
            >
              <Edit className="h-4 w-4" />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => onDuplicate(block.id)}>
                  <Copy className="h-4 w-4 mr-2" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={() => onDelete(block.id)}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
      </Card>
    </div>
  );
});

BlockItem.displayName = "BlockItem";
