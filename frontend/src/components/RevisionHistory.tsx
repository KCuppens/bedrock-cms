import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { 
  Clock, 
  User, 
  RotateCcw, 
  Eye, 
  GitBranch, 
  Save,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  FileText
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Badge,
  Button,
  Separator,
  ScrollArea,
  Alert,
  AlertDescription,
} from '@/components/ui';
import { api } from '@/lib/api.ts';
import { toast } from '@/components/ui/use-toast';

interface Revision {
  id: number;
  version: number;
  title: string;
  content: Record<string, any>;
  revision_type: 'manual' | 'autosave' | 'published';
  created_by: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
  };
  created_at: string;
  is_published: boolean;
  comment?: string;
}

interface RevisionHistoryProps {
  contentType: 'page' | 'blogpost';
  contentId: number;
  currentTitle: string;
  onRevert?: (revisionId: number) => void;
  className?: string;
}

const RevisionHistory: React.FC<RevisionHistoryProps> = ({
  contentType,
  contentId,
  currentTitle,
  onRevert,
  className
}) => {
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRevision, setSelectedRevision] = useState<Revision | null>(null);
  const [showRevertDialog, setShowRevertDialog] = useState(false);
  const [reverting, setReverting] = useState(false);

  // Load revisions on mount
  useEffect(() => {
    loadRevisions();
  }, [contentType, contentId]);

  const loadRevisions = async () => {
    try {
      setLoading(true);
      const endpoint = contentType === 'page' 
        ? `/api/v1/cms/pages/${contentId}/revisions/`
        : `/api/v1/blog/posts/${contentId}/revisions/`;
      
      const response = await api.request<{ results: Revision[] }>({
        method: 'GET',
        url: endpoint
      });
      
      setRevisions(response.results || []);
    } catch (error) {
      console.error('Failed to load revisions:', error);
      toast({
        title: "Error",
        description: "Failed to load revision history",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRevert = async (revision: Revision) => {
    if (!onRevert) return;
    
    try {
      setReverting(true);
      
      // Call the API to revert
      const response = await api.request({
        method: 'POST',
        url: `/api/v1/cms/revisions/${revision.id}/revert/`
      });
      
      toast({
        title: "Content Reverted",
        description: `Successfully reverted to version ${revision.version} from ${format(new Date(revision.created_at), 'MMM d, yyyy h:mm a')}`,
      });
      
      // Notify parent component
      onRevert(revision.id);
      
      // Reload revisions to show the new revert revision
      await loadRevisions();
      
    } catch (error: any) {
      console.error('Failed to revert:', error);
      toast({
        title: "Revert Failed",
        description: error.message || "Failed to revert to this version",
        variant: "destructive",
      });
    } finally {
      setReverting(false);
      setShowRevertDialog(false);
      setSelectedRevision(null);
    }
  };

  const getRevisionTypeIcon = (type: string) => {
    switch (type) {
      case 'published':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'autosave':
        return <Save className="w-4 h-4 text-blue-600" />;
      default:
        return <FileText className="w-4 h-4 text-gray-600" />;
    }
  };

  const getRevisionTypeBadge = (type: string) => {
    const variants = {
      published: 'default',
      autosave: 'secondary',
      manual: 'outline'
    };
    
    const labels = {
      published: 'Published',
      autosave: 'Auto-save',
      manual: 'Manual'
    };
    
    return (
      <Badge variant={variants[type as keyof typeof variants] || 'outline'} className="text-xs">
        {labels[type as keyof typeof labels] || type}
      </Badge>
    );
  };

  const formatUserName = (user: Revision['created_by']) => {
    if (user.first_name || user.last_name) {
      return `${user.first_name} ${user.last_name}`.trim();
    }
    return user.email;
  };

  const getContentPreview = (content: Record<string, any>): string => {
    if (content.blocks && Array.isArray(content.blocks)) {
      const textBlocks = content.blocks
        .filter(block => block.type === 'richtext' || block.type === 'text')
        .map(block => block.content?.text || block.content?.value || '')
        .join(' ');
      
      return textBlocks.slice(0, 150) + (textBlocks.length > 150 ? '...' : '');
    }
    
    if (content.content) {
      const text = typeof content.content === 'string' 
        ? content.content 
        : JSON.stringify(content.content);
      return text.slice(0, 150) + (text.length > 150 ? '...' : '');
    }
    
    return 'No content preview available';
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Revision History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center p-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Revision History
          </CardTitle>
          <CardDescription>
            {revisions.length} version{revisions.length !== 1 ? 's' : ''} of "{currentTitle}"
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {revisions.length === 0 ? (
            <div className="p-6">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  No revision history available for this content.
                </AlertDescription>
              </Alert>
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <div className="space-y-2 p-4">
                {revisions.map((revision, index) => (
                  <div key={revision.id} className="group">
                    <div className="flex items-start gap-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                      {/* Timeline indicator */}
                      <div className="flex flex-col items-center">
                        <div className="w-8 h-8 rounded-full bg-background border-2 border-muted flex items-center justify-center">
                          {getRevisionTypeIcon(revision.revision_type)}
                        </div>
                        {index < revisions.length - 1 && (
                          <div className="w-px h-6 bg-border mt-2"></div>
                        )}
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-medium text-sm">
                            Version {revision.version}
                          </span>
                          {getRevisionTypeBadge(revision.revision_type)}
                          {revision.is_published && (
                            <Badge variant="default" className="text-xs">
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Published
                            </Badge>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                          <User className="w-3 h-3" />
                          <span>{formatUserName(revision.created_by)}</span>
                          <span>•</span>
                          <span>{format(new Date(revision.created_at), 'MMM d, yyyy h:mm a')}</span>
                        </div>
                        
                        {revision.comment && (
                          <div className="text-sm text-muted-foreground mb-2 italic">
                            "{revision.comment}"
                          </div>
                        )}
                        
                        {revision.title !== currentTitle && (
                          <div className="text-sm text-muted-foreground mb-2">
                            <span className="font-medium">Title:</span> {revision.title}
                          </div>
                        )}
                        
                        <div className="text-xs text-muted-foreground">
                          {getContentPreview(revision.content)}
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedRevision(revision);
                            setShowRevertDialog(true);
                          }}
                          disabled={!onRevert}
                          className="h-8 px-2"
                        >
                          <RotateCcw className="w-3 h-3 mr-1" />
                          Revert
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Revert Confirmation Dialog */}
      <Dialog open={showRevertDialog} onOpenChange={setShowRevertDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Revert</DialogTitle>
            <DialogDescription>
              Are you sure you want to revert to this version? This will create a new revision 
              with the content from version {selectedRevision?.version}.
            </DialogDescription>
          </DialogHeader>
          
          {selectedRevision && (
            <div className="space-y-4">
              <div className="border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-medium">Version {selectedRevision.version}</span>
                  {getRevisionTypeBadge(selectedRevision.revision_type)}
                </div>
                
                <div className="text-sm text-muted-foreground mb-2">
                  Created by {formatUserName(selectedRevision.created_by)} on{' '}
                  {format(new Date(selectedRevision.created_at), 'MMMM d, yyyy h:mm a')}
                </div>
                
                {selectedRevision.title !== currentTitle && (
                  <div className="text-sm">
                    <span className="font-medium">Title:</span> {selectedRevision.title}
                  </div>
                )}
              </div>
              
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  This action will create a new revision and update the current content. 
                  Your current unsaved changes will be lost.
                </AlertDescription>
              </Alert>
            </div>
          )}
          
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRevertDialog(false)}
              disabled={reverting}
            >
              Cancel
            </Button>
            <Button
              onClick={() => selectedRevision && handleRevert(selectedRevision)}
              disabled={reverting}
              className="bg-orange-600 hover:bg-orange-700"
            >
              {reverting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Reverting...
                </>
              ) : (
                <>
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Revert to Version {selectedRevision?.version}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default RevisionHistory;