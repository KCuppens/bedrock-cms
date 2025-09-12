import { useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { toast } from '@/hooks/use-toast';

interface KeyboardShortcutsOptions {
  onSave?: () => void;
  onPublish?: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  onToggleEdit?: () => void;
  onAddBlockFocus?: () => void;
  onMoveBlockUp?: () => void;
  onMoveBlockDown?: () => void;
  enableBlockShortcuts?: boolean;
}

export const useKeyboardShortcuts = (options: KeyboardShortcutsOptions = {}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const {
    onSave,
    onPublish,
    onUndo,
    onRedo,
    onToggleEdit,
    onAddBlockFocus,
    onMoveBlockUp,
    onMoveBlockDown,
    enableBlockShortcuts = false
  } = options;

  // Return a function to show available shortcuts
  const showShortcuts = useCallback(() => {
    const shortcuts = [
      'Cmd/Ctrl + S: Save',
      'Cmd/Ctrl + P: Publish',
      'Cmd/Ctrl + Z: Undo',
      'Cmd/Ctrl + Shift + Z: Redo',
      'E: Toggle Edit Mode',
      '?: Show this help'
    ];

    if (enableBlockShortcuts) {
      shortcuts.push(
        'Shift + A: Focus Add Block Palette',
        '[ / ]: Move Block Up/Down'
      );
    }

    toast({
      title: "Keyboard Shortcuts",
      description: shortcuts.join('\n'),
    });
  }, [enableBlockShortcuts]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const { key, ctrlKey, metaKey, shiftKey, target } = event;
    const isInputElement = (target as HTMLElement)?.tagName?.toLowerCase() === 'input' ||
                          (target as HTMLElement)?.tagName?.toLowerCase() === 'textarea' ||
                          (target as HTMLElement)?.contentEditable === 'true';

    // Don't trigger shortcuts when typing in input fields (except for save/publish)
    const isModifierKeyPressed = ctrlKey || metaKey;

    // Cmd/Ctrl + S - Save
    if (isModifierKeyPressed && key === 's') {
      event.preventDefault();
      if (onSave) {
        onSave();
        toast({
          title: "Saved",
          description: "Changes have been saved successfully.",
        });
      } else {
        toast({
          title: "Save",
          description: "No save action available on this page.",
        });
      }
      return;
    }

    // Cmd/Ctrl + P - Publish dialog
    if (isModifierKeyPressed && key === 'p') {
      event.preventDefault();
      if (onPublish) {
        onPublish();
      } else {
        toast({
          title: "Publish",
          description: "No publish action available on this page.",
        });
      }
      return;
    }

    // Cmd/Ctrl + Z - Undo
    if (isModifierKeyPressed && key === 'z' && !shiftKey) {
      event.preventDefault();
      if (onUndo) {
        onUndo();
        toast({
          title: "Undo",
          description: "Last action has been undone.",
        });
      } else {
        toast({
          title: "Undo",
          description: "No undo action available.",
        });
      }
      return;
    }

    // Cmd/Ctrl + Shift + Z - Redo
    if (isModifierKeyPressed && key === 'z' && shiftKey) {
      event.preventDefault();
      if (onRedo) {
        onRedo();
        toast({
          title: "Redo",
          description: "Action has been redone.",
        });
      } else {
        toast({
          title: "Redo",
          description: "No redo action available.",
        });
      }
      return;
    }

    // Skip other shortcuts if user is typing in input fields
    if (isInputElement && !isModifierKeyPressed) {
      return;
    }

    // ? - Show keyboard shortcuts help
    if (key === '?' && !isInputElement) {
      event.preventDefault();
      showShortcuts();
      return;
    }

    // E - Toggle Edit mode
    if (key === 'e' || key === 'E') {
      event.preventDefault();
      if (onToggleEdit) {
        onToggleEdit();
      } else if (location.pathname.includes('/pages/')) {
        // If on a page detail, go to edit mode
        const pageId = location.pathname.split('/')[2];
        if (pageId && !location.pathname.includes('/edit')) {
          navigate(`/pages/${pageId}/edit`);
          toast({
            title: "Edit Mode",
            description: "Switched to edit mode.",
          });
        }
      } else {
        toast({
          title: "Edit Mode",
          description: "Edit mode not available on this page.",
        });
      }
      return;
    }

    // Block-specific shortcuts (only when enabled)
    if (enableBlockShortcuts) {
      // Shift + A - Focus Add block palette
      if (shiftKey && key === 'A') {
        event.preventDefault();
        if (onAddBlockFocus) {
          onAddBlockFocus();
          toast({
            title: "Add Block",
            description: "Block palette focused.",
          });
        }
        return;
      }

      // [ - Move block up
      if (key === '[') {
        event.preventDefault();
        if (onMoveBlockUp) {
          onMoveBlockUp();
          toast({
            title: "Block Moved",
            description: "Block moved up.",
          });
        }
        return;
      }

      // ] - Move block down
      if (key === ']') {
        event.preventDefault();
        if (onMoveBlockDown) {
          onMoveBlockDown();
          toast({
            title: "Block Moved",
            description: "Block moved down.",
          });
        }
        return;
      }
    }
  }, [
    onSave, onPublish, onUndo, onRedo, onToggleEdit,
    onAddBlockFocus, onMoveBlockUp, onMoveBlockDown,
    enableBlockShortcuts, navigate, location, showShortcuts
  ]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return { showShortcuts };
};
