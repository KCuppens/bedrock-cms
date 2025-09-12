import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import {
  Plus,
  GripVertical,
  Edit,
  Image as ImageIcon,
  Type,
  Layout,
  Trash2,
  ChevronUp,
  ChevronDown
} from "lucide-react";
import { PageData, Block } from "@/pages/PageEditor";
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface PageEditorCanvasProps {
  page: PageData;
  editMode: boolean;
  selectedBlock: string | null;
  onBlockSelect: (blockId: string | null) => void;
  onBlockUpdate: (blockId: string, updates: Partial<Block>) => void;
  onBlockDelete: (blockId: string) => void;
}

export const PageEditorCanvas = ({
  page,
  editMode,
  selectedBlock,
  onBlockSelect,
  onBlockUpdate,
  onBlockDelete
}: PageEditorCanvasProps) => {
  const [editingText, setEditingText] = useState<string | null>(null);

  const SortableBlock = ({ block }: { block: Block }) => {
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
    };

    const isSelected = selectedBlock === block.id;
    const isEditing = editingText === block.id;

    const blockClasses = editMode
      ? `relative group border-2 transition-colors ${
          isSelected ? 'border-blue-500' : 'border-transparent hover:border-blue-300'
        } ${isDragging ? 'opacity-50 z-50' : ''}`
      : '';

    const handleTextEdit = (field: string, value: string) => {
      onBlockUpdate(block.id, {
        content: { ...block.content, [field]: value }
      });
    };

    const renderBlockContent = () => {
      switch (block.type) {
        case 'hero':
          return (
            <div className="relative bg-gradient-to-r from-blue-600 to-purple-600 text-white py-20 px-8 text-center">
              {isEditing ? (
                <div className="space-y-4">
                  <Input
                    value={block.content.title}
                    onChange={(e) => handleTextEdit('title', e.target.value)}
                    className="text-white bg-white/20 border-white/30"
                    onBlur={() => setEditingText(null)}
                    autoFocus
                  />
                  <Textarea
                    value={block.content.subtitle}
                    onChange={(e) => handleTextEdit('subtitle', e.target.value)}
                    className="text-white bg-white/20 border-white/30"
                  />
                </div>
              ) : (
                <div
                  onClick={() => editMode && setEditingText(block.id)}
                  className={editMode ? "cursor-text" : ""}
                >
                  <h1 className="text-4xl font-bold mb-4">{block.content.title}</h1>
                  <p className="text-xl opacity-90">{block.content.subtitle}</p>
                </div>
              )}
            </div>
          );

        case 'richtext':
          return (
            <div className="prose prose-lg max-w-none py-8 px-4">
              {isEditing ? (
                <Textarea
                  value={block.content.html.replace(/<[^>]*>/g, '')}
                  onChange={(e) => handleTextEdit('html', `<p>${e.target.value}</p>`)}
                  className="min-h-32"
                  onBlur={() => setEditingText(null)}
                  autoFocus
                />
              ) : (
                <div
                  onClick={() => editMode && setEditingText(block.id)}
                  className={editMode ? "cursor-text" : ""}
                  dangerouslySetInnerHTML={{ __html: block.content.html }}
                />
              )}
            </div>
          );

        case 'image':
          return (
            <div className="py-8 text-center">
              <div className="bg-muted/50 rounded-lg p-12 border-2 border-dashed border-muted-foreground/20">
                <ImageIcon className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                <p className="text-muted-foreground">Click to add image</p>
                {block.content.alt && (
                  <p className="text-sm mt-2">{block.content.alt}</p>
                )}
              </div>
            </div>
          );

        case 'columns':
          return (
            <div className="grid grid-cols-2 gap-8 py-8 px-4">
              {block.content.columns.map((col: any, idx: number) => (
                <div key={idx} className="space-y-4">
                  <h3 className="font-semibold">Column {idx + 1}</h3>
                  <p>{col.content}</p>
                </div>
              ))}
            </div>
          );

        case 'cta':
          return (
            <div className="bg-primary text-primary-foreground py-12 px-8 text-center">
              <h2 className="text-2xl font-bold mb-4">{block.content.title}</h2>
              <Button variant="secondary" size="lg">
                {block.content.button?.text}
              </Button>
            </div>
          );

        default:
          return (
            <div className="py-8 px-4">
              <p className="text-muted-foreground">Unknown block type: {block.type}</p>
            </div>
          );
      }
    };

    return (
      <div ref={setNodeRef} style={style} className={blockClasses}>
        {editMode && (
          <>
            {/* Add block above button */}
            <Button
              variant="ghost"
              size="sm"
              className="absolute -top-6 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-10"
            >
              <Plus className="w-4 h-4" />
            </Button>

            {/* Drag handle - positioned inside the block */}
            <div
              className="absolute left-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 cursor-grab active:cursor-grabbing bg-white/90 dark:bg-black/90 p-1 rounded border shadow-sm"
              {...attributes}
              {...listeners}
            >
              <GripVertical className="w-4 h-4 text-muted-foreground" />
            </div>

            {/* Control buttons */}
            <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 bg-white/90 dark:bg-black/90 border shadow-sm"
                onClick={() => onBlockSelect(block.id)}
              >
                <Edit className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 bg-white/90 dark:bg-black/90 border shadow-sm hover:bg-destructive hover:text-destructive-foreground"
                onClick={() => onBlockDelete(block.id)}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </>
        )}

        <div onClick={() => editMode && onBlockSelect(block.id)}>
          {renderBlockContent()}
        </div>

        {editMode && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-10"
          >
            <Plus className="w-4 h-4" />
          </Button>
        )}
      </div>
    );
  };

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      <div className="max-w-4xl mx-auto">
        {editMode && (
          <div className="p-4 bg-blue-50 dark:bg-blue-950/20 text-blue-800 dark:text-blue-200 text-sm text-center border-b">
            Edit mode enabled - Drag blocks to reorder, click to edit, trash icon to delete
          </div>
        )}

        <div className="space-y-0">
          {page.blocks
            .sort((a, b) => a.position - b.position)
            .map(block => (
              <SortableBlock key={block.id} block={block} />
            ))}
        </div>

        {page.blocks.length === 0 && (
          <div className="py-20 text-center">
            <Layout className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">Empty page</h3>
            <p className="text-muted-foreground mb-6">Start building by adding blocks from the palette</p>
          </div>
        )}
      </div>
    </div>
  );
};