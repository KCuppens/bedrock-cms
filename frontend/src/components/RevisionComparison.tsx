import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  ArrowRight,
  Copy,
  RotateCcw,
  User,
  Clock,
  FileText,
  Code
} from "lucide-react";
import { PageRevision } from "@/types/api";
import { cn } from "@/lib/utils";

interface RevisionComparisonProps {
  isOpen: boolean;
  onClose: () => void;
  leftRevision: PageRevision;
  rightRevision: PageRevision;
  onRevert: (revisionId: number) => void;
}

interface DiffLine {
  type: 'added' | 'removed' | 'unchanged';
  content: string;
  lineNumber?: number;
}

const generateDiff = (oldText: string, newText: string): DiffLine[] => {
  const oldLines = oldText.split('\n');
  const newLines = newText.split('\n');
  const diff: DiffLine[] = [];
  
  let oldIndex = 0;
  let newIndex = 0;
  
  while (oldIndex < oldLines.length || newIndex < newLines.length) {
    if (oldIndex >= oldLines.length) {
      // Only new lines remain
      diff.push({
        type: 'added',
        content: newLines[newIndex],
        lineNumber: newIndex + 1
      });
      newIndex++;
    } else if (newIndex >= newLines.length) {
      // Only old lines remain
      diff.push({
        type: 'removed',
        content: oldLines[oldIndex],
        lineNumber: oldIndex + 1
      });
      oldIndex++;
    } else if (oldLines[oldIndex] === newLines[newIndex]) {
      // Lines are the same
      diff.push({
        type: 'unchanged',
        content: oldLines[oldIndex],
        lineNumber: newIndex + 1
      });
      oldIndex++;
      newIndex++;
    } else {
      // Lines are different
      diff.push({
        type: 'removed',
        content: oldLines[oldIndex],
        lineNumber: oldIndex + 1
      });
      diff.push({
        type: 'added',
        content: newLines[newIndex],
        lineNumber: newIndex + 1
      });
      oldIndex++;
      newIndex++;
    }
  }
  
  return diff;
};

const DiffView = ({ oldText, newText }: { oldText: string; newText: string }) => {
  const diff = generateDiff(oldText, newText);
  
  return (
    <div className="font-mono text-sm border rounded-lg overflow-hidden">
      <ScrollArea className="h-96">
        {diff.map((line, index) => (
          <div
            key={index}
            className={cn(
              "flex px-4 py-1 border-b last:border-b-0",
              line.type === 'added' && "bg-green-50 border-green-200",
              line.type === 'removed' && "bg-red-50 border-red-200",
              line.type === 'unchanged' && "bg-background"
            )}
          >
            <span className="w-8 text-xs text-muted-foreground flex-shrink-0">
              {line.lineNumber}
            </span>
            <span
              className={cn(
                "ml-2 flex-1",
                line.type === 'added' && "text-green-700",
                line.type === 'removed' && "text-red-700"
              )}
            >
              {line.type === 'added' && '+ '}
              {line.type === 'removed' && '- '}
              {line.content}
            </span>
          </div>
        ))}
      </ScrollArea>
    </div>
  );
};

const SideBySideView = ({ leftText, rightText }: { leftText: string; rightText: string }) => {
  return (
    <div className="grid grid-cols-2 gap-4 h-96">
      <div className="border rounded-lg overflow-hidden">
        <div className="bg-muted px-3 py-2 text-sm font-medium">Original</div>
        <ScrollArea className="h-80">
          <pre className="p-4 text-sm whitespace-pre-wrap">{leftText}</pre>
        </ScrollArea>
      </div>
      <div className="border rounded-lg overflow-hidden">
        <div className="bg-muted px-3 py-2 text-sm font-medium">Updated</div>
        <ScrollArea className="h-80">
          <pre className="p-4 text-sm whitespace-pre-wrap">{rightText}</pre>
        </ScrollArea>
      </div>
    </div>
  );
};

export const RevisionComparison = ({
  isOpen,
  onClose,
  leftRevision,
  rightRevision,
  onRevert
}: RevisionComparisonProps) => {
  const [viewMode, setViewMode] = useState<'diff' | 'side-by-side'>('diff');
  const [selectedField, setSelectedField] = useState<'title' | 'content' | 'meta'>('content');

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFieldContent = (revision: PageRevision, field: string) => {
    switch (field) {
      case 'title':
        return revision.title || '';
      case 'content':
        return JSON.stringify(revision.blocks || [], null, 2);
      case 'meta':
        return JSON.stringify({
          slug: revision.slug,
          status: revision.status,
          seo: revision.seo
        }, null, 2);
      default:
        return '';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Compare Revisions
          </DialogTitle>
        </DialogHeader>

        {/* Revision Info */}
        <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" />
              <span className="font-medium">Revision {leftRevision.id}</span>
              {leftRevision.is_published && (
                <Badge variant="secondary">Published</Badge>
              )}
            </div>
            <div className="text-sm text-muted-foreground space-y-1">
              <div className="flex items-center gap-2">
                <User className="w-3 h-3" />
                {leftRevision.created_by?.first_name} {leftRevision.created_by?.last_name}
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-3 h-3" />
                {formatDate(leftRevision.created_at)}
              </div>
            </div>
            {leftRevision.comment && (
              <p className="text-sm italic">"{leftRevision.comment}"</p>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <ArrowRight className="w-4 h-4" />
              <span className="font-medium">Revision {rightRevision.id}</span>
              {rightRevision.is_published && (
                <Badge variant="secondary">Published</Badge>
              )}
            </div>
            <div className="text-sm text-muted-foreground space-y-1">
              <div className="flex items-center gap-2">
                <User className="w-3 h-3" />
                {rightRevision.created_by?.first_name} {rightRevision.created_by?.last_name}
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-3 h-3" />
                {formatDate(rightRevision.created_at)}
              </div>
            </div>
            {rightRevision.comment && (
              <p className="text-sm italic">"{rightRevision.comment}"</p>
            )}
          </div>
        </div>

        <Separator />

        {/* Field Selection */}
        <Tabs value={selectedField} onValueChange={(value: any) => setSelectedField(value)}>
          <TabsList>
            <TabsTrigger value="title">Title</TabsTrigger>
            <TabsTrigger value="content">Content</TabsTrigger>
            <TabsTrigger value="meta">Metadata</TabsTrigger>
          </TabsList>

          <div className="flex items-center justify-between mt-4">
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'diff' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('diff')}
              >
                <Code className="w-4 h-4 mr-2" />
                Diff View
              </Button>
              <Button
                variant={viewMode === 'side-by-side' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('side-by-side')}
              >
                <Copy className="w-4 h-4 mr-2" />
                Side by Side
              </Button>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onRevert(leftRevision.id)}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Revert to Left
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onRevert(rightRevision.id)}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Revert to Right
              </Button>
            </div>
          </div>

          <TabsContent value={selectedField} className="mt-4">
            {viewMode === 'diff' ? (
              <DiffView
                oldText={getFieldContent(leftRevision, selectedField)}
                newText={getFieldContent(rightRevision, selectedField)}
              />
            ) : (
              <SideBySideView
                leftText={getFieldContent(leftRevision, selectedField)}
                rightText={getFieldContent(rightRevision, selectedField)}
              />
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};