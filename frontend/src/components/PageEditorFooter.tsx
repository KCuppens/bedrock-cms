import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Undo,
  Redo,
  Save,
  Loader2,
  Edit,
  Eye,
  Keyboard
} from "lucide-react";

interface PageEditorFooterProps {
  saving: boolean;
  lastSaved: Date;
  editMode: boolean;
  onToggleEditMode: () => void;
}

export const PageEditorFooter = ({
  saving,
  lastSaved,
  editMode,
  onToggleEditMode
}: PageEditorFooterProps) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <footer className="border-t border-border bg-card px-6 py-3">
      <div className="flex items-center justify-between">
        {/* Left side - Actions */}
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" disabled>
            <Undo className="w-4 h-4 mr-2" />
            Undo
          </Button>

          <Button variant="ghost" size="sm" disabled>
            <Redo className="w-4 h-4 mr-2" />
            Redo
          </Button>

          <div className="h-6 w-px bg-border" />

          <Button
            variant={editMode ? "default" : "ghost"}
            size="sm"
            onClick={onToggleEditMode}
          >
            {editMode ? <Eye className="w-4 h-4 mr-2" /> : <Edit className="w-4 h-4 mr-2" />}
            {editMode ? "Preview" : "Edit"}
          </Button>
        </div>

        {/* Center - Save Status */}
        <div className="flex items-center gap-3">
          {saving ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Saving...</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Save className="w-4 h-4" />
              <span>Saved at {formatTime(lastSaved)}</span>
            </div>
          )}
        </div>

        {/* Right side - Shortcuts */}
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-xs">
            <Keyboard className="w-3 h-3 mr-1" />
            Ctrl+S to save
          </Badge>

          <Badge variant="outline" className="text-xs">
            Ctrl+Z to undo
          </Badge>
        </div>
      </div>
    </footer>
  );
};