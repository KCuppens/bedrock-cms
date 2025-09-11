import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Keyboard, Command } from 'lucide-react';

interface ShortcutGroup {
  title: string;
  shortcuts: Array<{
    keys: string[];
    description: string;
    context?: string;
  }>;
}

const KeyboardShortcutsHelp = () => {
  const [open, setOpen] = useState(false);

  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const modKey = isMac ? '⌘' : 'Ctrl';

  const shortcutGroups: ShortcutGroup[] = [
    {
      title: 'General',
      shortcuts: [
        { keys: [modKey, 'S'], description: 'Save changes' },
        { keys: [modKey, 'P'], description: 'Open publish dialog' },
        { keys: [modKey, 'Z'], description: 'Undo last action' },
        { keys: [modKey, 'Shift', 'Z'], description: 'Redo last action' },
        { keys: ['E'], description: 'Toggle edit mode' },
        { keys: ['?'], description: 'Show this help dialog' },
      ]
    },
    {
      title: 'Page Editor',
      shortcuts: [
        { keys: ['Shift', 'A'], description: 'Focus add block palette', context: 'Page Editor only' },
        { keys: ['['], description: 'Move selected block up', context: 'When block is focused' },
        { keys: [']'], description: 'Move selected block down', context: 'When block is focused' },
        { keys: ['Delete'], description: 'Delete selected block', context: 'When block is focused' },
        { keys: ['Escape'], description: 'Deselect current block', context: 'Page Editor only' },
      ]
    },
    {
      title: 'Navigation',
      shortcuts: [
        { keys: ['G', 'H'], description: 'Go to Home' },
        { keys: ['G', 'P'], description: 'Go to Pages' },
        { keys: ['G', 'M'], description: 'Go to Media' },
        { keys: ['G', 'T'], description: 'Go to Translations' },
        { keys: ['G', 'U'], description: 'Go to Users & Roles' },
        { keys: ['G', 'S'], description: 'Go to SEO & Redirects' },
      ]
    }
  ];

  const renderShortcutKey = (key: string) => (
    <Badge 
      key={key} 
      variant="outline" 
      className="px-2 py-1 text-xs font-mono bg-muted"
    >
      {key}
    </Badge>
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          <Keyboard className="h-4 w-4" />
          <span className="hidden sm:inline">Shortcuts</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Command className="h-5 w-5" />
            Keyboard Shortcuts
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          {shortcutGroups.map((group) => (
            <div key={group.title}>
              <h3 className="text-lg font-semibold mb-3 text-foreground">
                {group.title}
              </h3>
              <div className="space-y-2">
                {group.shortcuts.map((shortcut, index) => (
                  <div 
                    key={index} 
                    className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="text-sm font-medium text-foreground">
                        {shortcut.description}
                      </div>
                      {shortcut.context && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {shortcut.context}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, keyIndex) => (
                        <React.Fragment key={keyIndex}>
                          {keyIndex > 0 && (
                            <span className="text-muted-foreground mx-1">+</span>
                          )}
                          {renderShortcutKey(key)}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          
          <div className="pt-4 border-t border-border">
            <p className="text-sm text-muted-foreground">
              <strong>Tip:</strong> Most shortcuts work globally, but some are specific to certain pages or contexts.
              You can press <Badge variant="outline" className="mx-1 px-1 py-0 text-xs">?</Badge> at any time to see this help.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default KeyboardShortcutsHelp;