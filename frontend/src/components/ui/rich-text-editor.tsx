import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  List,
  ListOrdered,
  Quote,
  Link,
  Image,
  Code,
  Undo,
  Redo
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  minHeight?: number;
}

export const RichTextEditor = ({
  value,
  onChange,
  placeholder = "Start writing...",
  className,
  minHeight = 200
}: RichTextEditorProps) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const [isEditorFocused, setIsEditorFocused] = useState(false);

  // Update editor content when value prop changes
  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== value) {
      editorRef.current.innerHTML = value;
    }
  }, [value]);

  const executeCommand = (command: string, value?: string) => {
    document.execCommand(command, false, value);
    editorRef.current?.focus();
    handleContentChange();
  };

  const handleContentChange = () => {
    if (editorRef.current) {
      const content = editorRef.current.innerHTML;
      onChange(content);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Handle common keyboard shortcuts
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'b':
          e.preventDefault();
          executeCommand('bold');
          break;
        case 'i':
          e.preventDefault();
          executeCommand('italic');
          break;
        case 'u':
          e.preventDefault();
          executeCommand('underline');
          break;
        case 'z':
          e.preventDefault();
          if (e.shiftKey) {
            executeCommand('redo');
          } else {
            executeCommand('undo');
          }
          break;
      }
    }
  };

  const insertLink = () => {
    const url = prompt('Enter the URL:');
    if (url) {
      executeCommand('createLink', url);
    }
  };

  const insertImage = () => {
    const url = prompt('Enter the image URL:');
    if (url) {
      executeCommand('insertImage', url);
    }
  };

  const toolbarButtons = [
    {
      group: 'format',
      buttons: [
        { icon: Bold, command: 'bold', title: 'Bold (Ctrl+B)' },
        { icon: Italic, command: 'italic', title: 'Italic (Ctrl+I)' },
        { icon: Underline, command: 'underline', title: 'Underline (Ctrl+U)' },
        { icon: Strikethrough, command: 'strikethrough', title: 'Strikethrough' },
      ]
    },
    {
      group: 'align',
      buttons: [
        { icon: AlignLeft, command: 'justifyLeft', title: 'Align Left' },
        { icon: AlignCenter, command: 'justifyCenter', title: 'Align Center' },
        { icon: AlignRight, command: 'justifyRight', title: 'Align Right' },
        { icon: AlignJustify, command: 'justifyFull', title: 'Justify' },
      ]
    },
    {
      group: 'lists',
      buttons: [
        { icon: List, command: 'insertUnorderedList', title: 'Bullet List' },
        { icon: ListOrdered, command: 'insertOrderedList', title: 'Numbered List' },
        { icon: Quote, command: 'formatBlock', value: 'blockquote', title: 'Quote' },
      ]
    },
    {
      group: 'insert',
      buttons: [
        { icon: Link, action: insertLink, title: 'Insert Link' },
        { icon: Image, action: insertImage, title: 'Insert Image' },
        { icon: Code, command: 'formatBlock', value: 'pre', title: 'Code Block' },
      ]
    },
    {
      group: 'history',
      buttons: [
        { icon: Undo, command: 'undo', title: 'Undo (Ctrl+Z)' },
        { icon: Redo, command: 'redo', title: 'Redo (Ctrl+Shift+Z)' },
      ]
    }
  ];

  return (
    <div className={cn("border rounded-lg", className)}>
      {/* Toolbar */}
      <div className="border-b p-2 bg-muted/20">
        <div className="flex items-center gap-1 flex-wrap">
          {toolbarButtons.map((group, groupIndex) => (
            <div key={group.group} className="flex items-center">
              {groupIndex > 0 && <Separator orientation="vertical" className="h-6 mx-1" />}
              {group.buttons.map((button, buttonIndex) => {
                const Icon = button.icon;
                return (
                  <Button
                    key={buttonIndex}
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    title={button.title}
                    onClick={() => {
                      if (button.action) {
                        button.action();
                      } else if (button.command) {
                        executeCommand(button.command, button.value);
                      }
                    }}
                  >
                    <Icon className="h-4 w-4" />
                  </Button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Editor */}
      <div
        ref={editorRef}
        contentEditable
        className={cn(
          "p-4 focus:outline-none prose prose-sm max-w-none",
          !value && "text-muted-foreground before:content-[attr(data-placeholder)]"
        )}
        style={{ minHeight }}
        data-placeholder={placeholder}
        onInput={handleContentChange}
        onKeyDown={handleKeyDown}
        onFocus={() => setIsEditorFocused(true)}
        onBlur={() => setIsEditorFocused(false)}
        suppressContentEditableWarning={true}
      />

      {/* Status Bar */}
      <div className="border-t px-4 py-2 bg-muted/10 text-xs text-muted-foreground flex justify-between">
        <div>
          {value && (
            <span>
              {value.replace(/<[^>]*>/g, '').trim().split(/\s+/).length} words
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className={cn(
            "inline-block w-2 h-2 rounded-full",
            isEditorFocused ? "bg-green-500" : "bg-gray-300"
          )} />
          <span>Rich Text Editor</span>
        </div>
      </div>
    </div>
  );
};

export default RichTextEditor;