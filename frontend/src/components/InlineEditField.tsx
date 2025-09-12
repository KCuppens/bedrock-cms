import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Check, X, Edit2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDebouncedCallback } from "@/hooks/useDebounce";

interface InlineEditFieldProps {
  value: string;
  onSave: (value: string) => void;
  placeholder?: string;
  multiline?: boolean;
  className?: string;
  disabled?: boolean;
  validation?: (value: string) => string | null;
  debounceMs?: number;
  autoSave?: boolean;
}

export const InlineEditField = ({
  value,
  onSave,
  placeholder,
  multiline = false,
  className,
  disabled = false,
  validation,
  debounceMs = 500,
  autoSave = false
}: InlineEditFieldProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  // Debounced save for auto-save mode
  const debouncedSave = useDebouncedCallback(
    async (valueToSave: string) => {
      if (!autoSave || valueToSave === value) return;

      if (validation) {
        const validationError = validation(valueToSave);
        if (validationError) {
          setError(validationError);
          return;
        }
      }

      setIsSaving(true);
      try {
        await onSave(valueToSave);
        setError(null);
      } catch (err) {
        setError('Failed to save changes');
      } finally {
        setIsSaving(false);
      }
    },
    debounceMs
  );

  useEffect(() => {
    setEditValue(value);
  }, [value]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      if (inputRef.current instanceof HTMLInputElement) {
        inputRef.current.select();
      }
    }
  }, [isEditing]);

  // Auto-save effect
  useEffect(() => {
    if (autoSave && isEditing && editValue !== value) {
      debouncedSave(editValue);
    }
  }, [editValue, autoSave, isEditing, debouncedSave, value]);

  const handleSave = () => {
    if (validation) {
      const validationError = validation(editValue);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    setError(null);
    onSave(editValue);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(value);
    setError(null);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !multiline) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    } else if (e.key === 'Enter' && e.ctrlKey && multiline) {
      e.preventDefault();
      handleSave();
    }
  };

  if (disabled) {
    return (
      <div className={cn("text-sm", className)}>
        {value || placeholder}
      </div>
    );
  }

  if (!isEditing) {
    return (
      <div
        className={cn(
          "group flex items-center gap-2 cursor-pointer hover:bg-muted/50 rounded p-1 -m-1",
          className
        )}
        onClick={() => setIsEditing(true)}
      >
        <span className="flex-1 text-sm">
          {value || <span className="text-muted-foreground">{placeholder}</span>}
        </span>
        <div className="flex items-center gap-1">
          {isSaving && (
            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
          )}
          <Edit2 className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>
    );
  }

  const InputComponent = multiline ? Textarea : Input;

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <InputComponent
          ref={inputRef as any}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={cn("flex-1", error && "border-destructive")}
          rows={multiline ? 3 : undefined}
        />
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="outline"
            onClick={handleSave}
            className="h-8 w-8 p-0"
          >
            <Check className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCancel}
            className="h-8 w-8 p-0"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
      {multiline && (
        <p className="text-xs text-muted-foreground">
          Press Ctrl+Enter to save, Escape to cancel
        </p>
      )}
    </div>
  );
};