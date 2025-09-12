import { lazy, Suspense, memo, useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, Upload, Users, Calendar, ExternalLink, Activity, Globe, AlertTriangle, CheckCircle, Clock, AlertCircle } from "lucide-react";
import { useTranslationQueueSummary } from "@/hooks/useTranslationQueue";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "@/contexts/TranslationContext";

// Use lightweight chart instead of heavy Recharts
const LightweightChart = lazy(() => import("@/components/LightweightChart"));

const Index = memo(() => {
  const userName = "Mark Bennet";
  const [showTranslations, setShowTranslations] = useState(false);
  const { data: queueSummary, isLoading: queueLoading } = useTranslationQueueSummary();
  const navigate = useNavigate();
  const { t } = useTranslation();

  // Delay loading translation data to reduce initial memory usage
  useEffect(() => {
    const timer = setTimeout(() => setShowTranslations(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />

        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />

          <main className="flex-1 p-8">
            <div className="max-w-7xl mx-auto">
            {/* Header with Welcome and Quick Actions */}
            <div className="mb-8">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
                <h1 className="text-3xl font-bold text-foreground">{t('dashboard.index.welcome', 'Welcome back')}, {userName}</h1>

                <div className="grid grid-cols-2 gap-3">
                  <Button
                    size="sm"
                    onClick={() => navigate('/dashboard/pages?action=new')}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    {t('dashboard.index.new_page', 'New Page')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('/dashboard/media')}
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    {t('dashboard.index.upload_media', 'Upload Media')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('/dashboard/translations/locales?action=add')}
                  >
                    <Globe className="w-4 h-4 mr-2" />
                    {t('dashboard.index.add_locale', 'Add Locale')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('/dashboard/users-roles?action=invite')}
                  >
                    <Users className="w-4 h-4 mr-2" />
                    {t('dashboard.index.invite_user', 'Invite User')}
                  </Button>
                </div>
              </div>
            </div>

            {/* Lightweight Chart - Full Width */}
            <div className="mb-8">
              <Suspense fallback={<div className="h-96 bg-muted animate-pulse rounded-lg" />}>
                <LightweightChart />
              </Suspense>
            </div>

            {/* Dashboard Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              {/* My Work */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5" />
                    {t('dashboard.index.my_work', 'My Work')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="p-3 bg-muted rounded-lg">
                      <div className="font-medium">{t('dashboard.index.reviews_pending', '3 Reviews Pending')}</div>
                      <div className="text-sm text-muted-foreground">{t('dashboard.index.pages_waiting_approval', 'Pages waiting for approval')}</div>
                    </div>
                    <div className="p-3 bg-muted rounded-lg">
                      <div className="font-medium">{t('dashboard.index.draft_pages', '5 Draft Pages')}</div>
                      <div className="text-sm text-muted-foreground">{t('dashboard.index.recently_edited', 'Recently edited by you')}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Recent Activity */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    {t('dashboard.index.recent_activity', 'Recent Activity')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3 p-2">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      <div>
                        <div className="font-medium text-sm">{t('dashboard.index.homepage_published', 'Homepage published')}</div>
                        <div className="text-xs text-muted-foreground">{t('dashboard.index.hours_ago', '2 hours ago')}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-2">
                      <Globe className="w-4 h-4 text-blue-500" />
                      <div>
                        <div className="font-medium text-sm">{t('dashboard.index.translations_approved', 'Spanish translations approved')}</div>
                        <div className="text-xs text-muted-foreground">{t('dashboard.index.hours_ago_5', '5 hours ago')}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-2">
                      <ExternalLink className="w-4 h-4 text-purple-500" />
                      <div>
                        <div className="font-medium text-sm">{t('dashboard.index.redirect_added', 'Redirect added: /old-page → /new-page')}</div>
                        <div className="text-xs text-muted-foreground">{t('dashboard.index.day_ago', '1 day ago')}</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Translations Snapshot */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Globe className="w-5 h-5" />
                    {t('dashboard.index.translation_queue_status', 'Translation Queue Status')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {queueLoading ? (
                    <div className="space-y-3">
                      <div className="animate-pulse">
                        <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                        <div className="h-2 bg-muted rounded"></div>
                      </div>
                      <div className="animate-pulse">
                        <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                        <div className="h-2 bg-muted rounded"></div>
                      </div>
                    </div>
                  ) : queueSummary ? (
                    <div className="space-y-4">
                      {/* Overall Stats */}
                      {queueSummary.overall.total > 0 && (
                        <div className="pb-3 border-b">
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-sm font-medium">{t('dashboard.index.overall_progress', 'Overall Progress')}</span>
                            <span className="text-xs text-muted-foreground">
                              {queueSummary.overall.completed}/{queueSummary.overall.total} {t('dashboard.index.completed', 'completed')}
                            </span>
                          </div>
                          <div className="w-full bg-muted rounded-full h-2">
                            <div
                              className="bg-primary h-2 rounded-full transition-all duration-300"
                              style={{ width: `${queueSummary.overall.completion_percentage}%` }}
                            ></div>
                          </div>
                          {queueSummary.overall.overdue > 0 && (
                            <div className="flex items-center gap-1 mt-2 text-xs text-orange-600">
                              <AlertCircle className="w-3 h-3" />
                              {queueSummary.overall.overdue} {t('dashboard.index.overdue_items', 'overdue items')}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Per-locale breakdown */}
                      <div className="space-y-3">
                        {queueSummary.locales.slice(0, 3).map((locale) => (
                          <div key={locale.locale.code} className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{locale.locale.native_name}</span>
                                <span className="text-muted-foreground text-xs">({locale.locale.code.toUpperCase()})</span>
                              </div>
                              <div className="flex items-center gap-2">
                                {locale.pending > 0 && (
                                  <span className="text-xs text-muted-foreground">{locale.pending} {t('dashboard.index.pending', 'pending')}</span>
                                )}
                                {locale.overdue > 0 && (
                                  <Badge variant="destructive" className="text-xs px-1 py-0">
                                    {locale.overdue} {t('dashboard.index.overdue', 'overdue')}
                                  </Badge>
                                )}
                              </div>
                            </div>
                            <div className="w-full bg-muted rounded-full h-2">
                              <div
                                className={`h-2 rounded-full transition-all duration-300 ${
                                  locale.completion_percentage >= 90 ? 'bg-green-500' :
                                  locale.completion_percentage >= 70 ? 'bg-yellow-500' :
                                  locale.completion_percentage >= 50 ? 'bg-orange-500' :
                                  'bg-red-500'
                                }`}
                                style={{ width: `${locale.completion_percentage}%` }}
                              ></div>
                            </div>
                            <div className="flex justify-between text-xs text-muted-foreground">
                              <span>{locale.completion_percentage}% {t('dashboard.index.complete', 'complete')}</span>
                              {locale.priority_breakdown.urgent > 0 && (
                                <span className="text-red-600 font-medium">
                                  {locale.priority_breakdown.urgent} {t('dashboard.index.urgent', 'urgent')}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Show message if no data */}
                      {queueSummary.locales.length === 0 && (
                        <div className="text-center py-4">
                          <Globe className="w-12 h-12 mx-auto text-muted-foreground mb-2" />
                          <p className="text-sm text-muted-foreground">{t('dashboard.index.no_translations', 'No translations in queue')}</p>
                        </div>
                      )}

                      {/* View Queue button */}
                      {queueSummary.overall.total > 0 && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full"
                          onClick={() => navigate('/dashboard/translations/queue')}
                        >
                          <Activity className="w-4 h-4 mr-2" />
                          {t('dashboard.index.view_translation_queue', 'View Translation Queue')}
                        </Button>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <AlertTriangle className="w-12 h-12 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">{t('dashboard.index.unable_load_data', 'Unable to load translation data')}</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Publishing Schedule */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="w-5 h-5" />
                    {t('dashboard.index.publishing_schedule', 'Publishing Schedule')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-2 bg-muted rounded-lg">
                      <div>
                        <div className="font-medium text-sm">{t('dashboard.index.product_launch', 'Product Launch Page')}</div>
                        <div className="text-xs text-muted-foreground">{t('dashboard.index.tomorrow_9am', 'Tomorrow, 9:00 AM')}</div>
                      </div>
                      <Badge variant="outline">{t('dashboard.index.scheduled', 'Scheduled')}</Badge>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-muted rounded-lg">
                      <div>
                        <div className="font-medium text-sm">{t('dashboard.index.blog_post_q4', 'Blog Post: Q4 Updates')}</div>
                        <div className="text-xs text-muted-foreground">{t('dashboard.index.dec_15', 'Dec 15, 2:00 PM')}</div>
                      </div>
                      <Badge variant="outline">{t('dashboard.index.scheduled', 'Scheduled')}</Badge>
                    </div>
                    <Button variant="outline" size="sm" className="w-full">
                      <Calendar className="w-4 h-4 mr-2" />
                      {t('dashboard.index.view_calendar', 'View Calendar')}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Broken Links */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-orange-500" />
                    {t('dashboard.index.broken_links', 'Broken Links')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center space-y-4">
                    <div className="text-3xl font-bold text-orange-500">7</div>
                    <div className="text-muted-foreground">{t('dashboard.index.broken_links_detected', 'broken links detected')}</div>
                    <Button variant="outline" size="sm" className="w-full">
                      <ExternalLink className="w-4 h-4 mr-2" />
                      {t('dashboard.index.view_report', 'View Report')}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* System Health */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="w-5 h-5" />
                    {t('dashboard.index.system_health', 'System Health')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{t('dashboard.index.queue_status', 'Queue Status')}</span>
                      <Badge variant="secondary" className="bg-green-100 text-green-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        {t('dashboard.index.healthy', 'Healthy')}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{t('dashboard.index.last_index', 'Last Index')}</span>
                      <span className="text-sm text-muted-foreground">{t('dashboard.index.15_min_ago', '15 min ago')}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">{t('dashboard.index.cache_status', 'Cache Status')}</span>
                      <Badge variant="secondary" className="bg-green-100 text-green-800">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        {t('dashboard.index.purged', 'Purged')}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

            </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
});

Index.displayName = 'Index';

export default Index;
