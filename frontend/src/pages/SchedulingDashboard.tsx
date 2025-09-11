import React, { useState, useEffect } from 'react';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, isBefore } from 'date-fns';
import {
  Calendar,
  Clock,
  List,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Eye,
  Edit,
  XCircle,
  AlertCircle
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
  Badge,
  Alert,
  AlertDescription,
  ScrollArea,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui';
import { api } from '@/lib/api.ts';
import { toast } from '@/components/ui/use-toast';

interface ScheduledContent {
  id: number;
  title: string;
  status: string;
  published_at: string;
  updated_at: string;
  locale: {
    code: string;
    name: string;
  };
  path?: string;
}

type ViewMode = 'calendar' | 'timeline';
type FilterType = 'all' | 'page' | 'blogpost';

const SchedulingDashboard: React.FC = () => {
  const [scheduledContent, setScheduledContent] = useState<ScheduledContent[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('calendar');
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  useEffect(() => {
    loadScheduledContent();
  }, []);

  const loadScheduledContent = async () => {
    try {
      setLoading(true);
      
      // Load scheduled pages
      const pagesResponse = await api.request<ScheduledContent[]>({
        method: 'GET',
        url: '/api/v1/cms/pages/scheduled_content/'
      });
      
      let allContent: ScheduledContent[] = pagesResponse || [];
      
      // Try to load scheduled blog posts if available
      try {
        const postsResponse = await api.request<ScheduledContent[]>({
          method: 'GET',
          url: '/api/v1/blog/posts/scheduled_content/'
        });
        allContent = [...allContent, ...(postsResponse || [])];
      } catch (error) {
        // Blog posts might not be available or endpoint doesn't exist
        console.log('Blog posts not available:', error);
      }
      
      setScheduledContent(allContent);
    } catch (error) {
      console.error('Failed to load scheduled content:', error);
      toast({
        title: "Error",
        description: "Failed to load scheduled content",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUnschedule = async (contentId: number, contentType: 'page' | 'blogpost') => {
    try {
      const endpoint = contentType === 'page' 
        ? `/api/v1/cms/pages/${contentId}/unschedule/`
        : `/api/v1/blog/posts/${contentId}/unschedule/`;
      
      await api.request({
        method: 'POST',
        url: endpoint
      });
      
      toast({
        title: "Content Unscheduled",
        description: "Content scheduling has been removed",
      });
      
      // Reload the content list
      loadScheduledContent();
      
    } catch (error: any) {
      console.error('Failed to unschedule content:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to unschedule content",
        variant: "destructive",
      });
    }
  };

  const getContentForDate = (date: Date) => {
    return scheduledContent.filter(content => 
      isSameDay(new Date(content.published_at), date)
    );
  };

  const getFilteredContent = () => {
    let filtered = scheduledContent;
    
    if (filterType !== 'all') {
      // This is a simplified filter - in a real app you'd have content type info
      // For now, we'll assume all content from CMS pages endpoint are pages
      filtered = scheduledContent; // Could implement proper filtering based on API response structure
    }
    
    return filtered.sort((a, b) => new Date(a.published_at).getTime() - new Date(b.published_at).getTime());
  };

  const renderCalendarView = () => {
    const monthStart = startOfMonth(currentMonth);
    const monthEnd = endOfMonth(currentMonth);
    const days = eachDayOfInterval({ start: monthStart, end: monthEnd });
    
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            {format(currentMonth, 'MMMM yyyy')}
          </h3>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentMonth(new Date())}
            >
              Today
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
        
        <div className="grid grid-cols-7 gap-2">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="p-2 text-center text-sm font-medium text-muted-foreground">
              {day}
            </div>
          ))}
          
          {days.map(day => {
            const dayContent = getContentForDate(day);
            const isToday = isSameDay(day, new Date());
            const isPast = isBefore(day, new Date());
            
            return (
              <div
                key={day.toISOString()}
                className={`p-2 min-h-[80px] border rounded-lg cursor-pointer hover:bg-muted/50 ${
                  isToday ? 'bg-primary/10 border-primary' : ''
                } ${
                  isPast ? 'opacity-60' : ''
                }`}
                onClick={() => setSelectedDate(day)}
              >
                <div className={`text-sm font-medium ${
                  isToday ? 'text-primary' : isPast ? 'text-muted-foreground' : ''
                }`}>
                  {format(day, 'd')}
                </div>
                
                {dayContent.length > 0 && (
                  <div className="mt-1 space-y-1">
                    {dayContent.slice(0, 2).map(content => (
                      <div
                        key={content.id}
                        className="text-xs bg-blue-100 text-blue-800 p-1 rounded truncate"
                        title={content.title}
                      >
                        {content.title}
                      </div>
                    ))}
                    {dayContent.length > 2 && (
                      <div className="text-xs text-muted-foreground">
                        +{dayContent.length - 2} more
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        
        {selectedDate && (
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Scheduled for {format(selectedDate, 'MMMM d, yyyy')}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedDate(null)}
                >
                  <XCircle className="w-4 h-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {getContentForDate(selectedDate).length === 0 ? (
                <p className="text-muted-foreground">No content scheduled for this date</p>
              ) : (
                <div className="space-y-2">
                  {getContentForDate(selectedDate).map(content => (
                    <div key={content.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <h4 className="font-medium">{content.title}</h4>
                        <p className="text-sm text-muted-foreground">
                          {format(new Date(content.published_at), 'h:mm a')}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{content.locale.code}</Badge>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUnschedule(content.id, 'page')}
                        >
                          <XCircle className="w-4 h-4" />
                          Unschedule
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  const renderTimelineView = () => {
    const filteredContent = getFilteredContent();
    
    return (
      <div className="space-y-4">
        {filteredContent.length === 0 ? (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              No scheduled content found.
            </AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-3">
            {filteredContent.map(content => {
              const publishDate = new Date(content.published_at);
              const isPast = isBefore(publishDate, new Date());
              
              return (
                <Card key={content.id} className={isPast ? 'opacity-60' : ''}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-medium">{content.title}</h3>
                          <Badge variant="secondary">{content.locale.code}</Badge>
                          {isPast && <Badge variant="outline">Overdue</Badge>}
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            {format(publishDate, 'MMM d, yyyy h:mm a')}
                          </span>
                          
                          {content.path && (
                            <span className="flex items-center gap-1">
                              <Eye className="w-4 h-4" />
                              {content.path}
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => window.open(`/dashboard/pages/${content.id}`, '_blank')}
                        >
                          <Edit className="w-4 h-4" />
                          Edit
                        </Button>
                        
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUnschedule(content.id, 'page')}
                        >
                          <XCircle className="w-4 h-4" />
                          Unschedule
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Scheduling Dashboard</h1>
        <p className="text-muted-foreground">
          Manage all your scheduled content in one place
        </p>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === 'calendar' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('calendar')}
            >
              <Calendar className="w-4 h-4 mr-1" />
              Calendar
            </Button>
            <Button
              variant={viewMode === 'timeline' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('timeline')}
            >
              <List className="w-4 h-4 mr-1" />
              Timeline
            </Button>
          </div>
          
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4" />
            <Select value={filterType} onValueChange={(value: FilterType) => setFilterType(value)}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Content</SelectItem>
                <SelectItem value="page">Pages</SelectItem>
                <SelectItem value="blogpost">Blog Posts</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        
        <Button
          variant="outline"
          onClick={loadScheduledContent}
          disabled={loading}
        >
          <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-8">
            <div className="flex items-center justify-center">
              <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-6">
            {viewMode === 'calendar' ? renderCalendarView() : renderTimelineView()}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SchedulingDashboard;
