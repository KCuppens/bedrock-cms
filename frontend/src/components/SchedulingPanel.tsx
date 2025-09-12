import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import {
  Calendar,
  Clock,
  AlertCircle,
  CheckCircle,
  XCircle,
  Loader2
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Button,
  Input,
  Label,
  Alert,
  AlertDescription,
  Badge
} from '@/components/ui';
import { api } from '@/lib/api';
import { toast } from '@/components/ui/use-toast';

interface SchedulingPanelProps {
  contentType: 'page' | 'blogpost';
  contentId: number;
  currentStatus: string;
  currentPublishedAt?: string | null;
  onStatusChange?: (status: string, publishedAt?: string | null) => void;
  className?: string;
}

const SchedulingPanel: React.FC<SchedulingPanelProps> = ({
  contentType,
  contentId,
  currentStatus,
  currentPublishedAt,
  onStatusChange,
  className
}) => {
  const [scheduledDateTime, setScheduledDateTime] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conflicts, setConflicts] = useState<any[]>([]);

  useEffect(() => {
    if (currentPublishedAt && currentStatus === 'scheduled') {
      // Format the existing scheduled time for the input
      const date = new Date(currentPublishedAt);
      const localDateTime = new Date(date.getTime() - (date.getTimezoneOffset() * 60000))
        .toISOString()
        .slice(0, 16);
      setScheduledDateTime(localDateTime);
    } else {
      // Default to 1 hour from now
      const defaultTime = new Date();
      defaultTime.setHours(defaultTime.getHours() + 1);
      defaultTime.setMinutes(0, 0, 0);
      const localDateTime = new Date(defaultTime.getTime() - (defaultTime.getTimezoneOffset() * 60000))
        .toISOString()
        .slice(0, 16);
      setScheduledDateTime(localDateTime);
    }
  }, [currentPublishedAt, currentStatus]);

  const handleSchedule = async () => {
    if (!scheduledDateTime) {
      toast({
        title: "Error",
        description: "Please select a date and time",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);

    try {
      const publishAt = new Date(scheduledDateTime).toISOString();

      const endpoint = contentType === 'page'
        ? `/api/v1/cms/pages/${contentId}/schedule/`
        : `/api/v1/blog/posts/${contentId}/schedule/`;

      const response = await api.request({
        method: 'POST',
        url: endpoint,
        data: {
          publish_at: publishAt
        }
      });

      toast({
        title: "Content Scheduled",
        description: `Content will be published on ${format(new Date(publishAt), 'MMM d, yyyy h:mm a')}`,
      });

      onStatusChange?.('scheduled', publishAt);

    } catch (error: any) {
      console.error('Failed to schedule content:', error);
      toast({
        title: "Scheduling Failed",
        description: error.message || "Failed to schedule content",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUnschedule = async () => {
    setIsLoading(true);

    try {
      const endpoint = contentType === 'page'
        ? `/api/v1/cms/pages/${contentId}/unschedule/`
        : `/api/v1/blog/posts/${contentId}/unschedule/`;

      await api.request({
        method: 'POST',
        url: endpoint
      });

      toast({
        title: "Scheduling Removed",
        description: "Content is no longer scheduled for publishing",
      });

      onStatusChange?.('draft', null);

    } catch (error: any) {
      console.error('Failed to unschedule content:', error);
      toast({
        title: "Unscheduling Failed",
        description: error.message || "Failed to remove scheduling",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePublishNow = async () => {
    setIsLoading(true);

    try {
      const endpoint = contentType === 'page'
        ? `/api/v1/cms/pages/${contentId}/publish/`
        : `/api/v1/blog/posts/${contentId}/publish/`;

      const response = await api.request({
        method: 'POST',
        url: endpoint
      });

      toast({
        title: "Content Published",
        description: "Content is now live",
      });

      onStatusChange?.('published', response.published_at);

    } catch (error: any) {
      console.error('Failed to publish content:', error);
      toast({
        title: "Publishing Failed",
        description: error.message || "Failed to publish content",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = () => {
    switch (currentStatus) {
      case 'published':
        return (
          <Badge variant="default" className="flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Published
          </Badge>
        );
      case 'scheduled':
        return (
          <Badge variant="secondary" className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Scheduled
          </Badge>
        );
      case 'draft':
      default:
        return (
          <Badge variant="outline" className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Draft
          </Badge>
        );
    }
  };

  const isInPast = scheduledDateTime && new Date(scheduledDateTime) <= new Date();
  const isValidDateTime = scheduledDateTime && !isInPast;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            Publishing Schedule
          </span>
          {getStatusBadge()}
        </CardTitle>
        <CardDescription>
          Manage when this content will be published
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {currentStatus === 'scheduled' && currentPublishedAt && (
          <Alert>
            <Clock className="h-4 w-4" />
            <AlertDescription>
              Currently scheduled to publish on{' '}
              <strong>{format(new Date(currentPublishedAt), 'MMMM d, yyyy h:mm a')}</strong>
            </AlertDescription>
          </Alert>
        )}

        {currentStatus === 'published' && currentPublishedAt && (
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              Published on{' '}
              <strong>{format(new Date(currentPublishedAt), 'MMMM d, yyyy h:mm a')}</strong>
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <Label htmlFor="schedule-datetime">Schedule Date & Time</Label>
          <Input
            id="schedule-datetime"
            type="datetime-local"
            value={scheduledDateTime}
            onChange={(e) => setScheduledDateTime(e.target.value)}
            disabled={isLoading}
            className={isInPast ? 'border-red-500' : ''}
          />
          {isInPast && (
            <p className="text-sm text-red-600">
              Selected time is in the past. Please choose a future date and time.
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {currentStatus !== 'published' && (
            <Button
              onClick={handleSchedule}
              disabled={isLoading || !isValidDateTime}
              className="flex items-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              <Clock className="w-4 h-4" />
              {currentStatus === 'scheduled' ? 'Reschedule' : 'Schedule'}
            </Button>
          )}

          {currentStatus === 'scheduled' && (
            <Button
              variant="outline"
              onClick={handleUnschedule}
              disabled={isLoading}
              className="flex items-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              <XCircle className="w-4 h-4" />
              Unschedule
            </Button>
          )}

          {currentStatus !== 'published' && (
            <Button
              variant="default"
              onClick={handlePublishNow}
              disabled={isLoading}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              <CheckCircle className="w-4 h-4" />
              Publish Now
            </Button>
          )}
        </div>

        {conflicts.length > 0 && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Scheduling conflicts detected:</strong>
              <ul className="mt-2 space-y-1">
                {conflicts.map((conflict, index) => (
                  <li key={index} className="text-sm">
                    • {conflict.title} is scheduled at the same time
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default SchedulingPanel;
