import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Globe,
  RefreshCw,
  Download,
  ExternalLink,
  Settings,
  FileText,
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react';
import { useLocales } from '@/hooks/queries/use-locales';
import { useToast } from '@/hooks/use-toast';

// Mock data for now - will be replaced with real API hooks
interface SitemapData {
  locale: {
    code: string;
    name: string;
    native_name: string;
    is_active: boolean;
  };
  url: string;
  pageCount: number;
  lastModified: Date;
  size: string;
  status: 'ready' | 'generating' | 'error' | 'not_generated';
}

const SitemapTab = () => {
  const { toast } = useToast();
  const { data: locales, isLoading: localesLoading, error: localesError } = useLocales();
  const [regenerating, setRegenerating] = useState<string[]>([]);
  const [sitemapSettings, setSitemapSettings] = useState({
    autoGenerate: false,
    generateFrequency: 'daily',
    includeAlternates: true,
    defaultPriority: '0.5',
    defaultChangefreq: 'weekly'
  });

  // Filter only active locales
  const activeLocales = locales?.filter(locale => locale.is_active) || [];

  // Debug logging
  console.log('🔍 SitemapTab Debug:', {
    locales,
    localesLoading,
    localesError,
    activeLocales,
    activeLocalesLength: activeLocales.length
  });

  // Mock sitemap data - in real implementation, this would come from API
  const sitemapData: SitemapData[] = activeLocales.map(locale => ({
    locale,
    url: `/sitemap-${locale.code}.xml`,
    pageCount: Math.floor(Math.random() * 500) + 100,
    lastModified: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000),
    size: `${Math.floor(Math.random() * 50) + 10}KB`,
    status: Math.random() > 0.1 ? 'ready' : 'not_generated' as any
  }));

  const totalUrls = sitemapData.reduce((sum, s) => sum + (s.status === 'ready' ? s.pageCount : 0), 0);
  const readySitemaps = sitemapData.filter(s => s.status === 'ready').length;

  const handleRegenerate = async (localeCode: string) => {
    setRegenerating(prev => [...prev, localeCode]);

    // Simulate API call
    setTimeout(() => {
      setRegenerating(prev => prev.filter(code => code !== localeCode));
      toast({
        title: "Sitemap Regenerated",
        description: `Sitemap for ${localeCode} has been regenerated successfully.`,
      });
    }, 2000);
  };

  const handleRegenerateAll = async () => {
    const codes = activeLocales.map(l => l.code);
    setRegenerating(codes);

    setTimeout(() => {
      setRegenerating([]);
      toast({
        title: "All Sitemaps Regenerated",
        description: `Successfully regenerated ${codes.length} sitemaps.`,
      });
    }, 3000);
  };

  const handleViewSitemap = (url: string) => {
    window.open(url, '_blank');
  };

  const handleDownloadSitemap = (url: string, localeCode: string) => {
    // In real implementation, this would trigger a download
    const link = document.createElement('a');
    link.href = url;
    link.download = `sitemap-${localeCode}.xml`;
    link.click();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'generating':
        return <Clock className="w-4 h-4 text-yellow-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
      case 'ready':
        return 'default';
      case 'generating':
        return 'secondary';
      case 'error':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  if (localesLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  if (activeLocales.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Globe className="w-12 h-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Active Locales</h3>
          <p className="text-muted-foreground text-center max-w-md">
            No active locales found. Please activate at least one locale to generate sitemaps.
          </p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => window.location.href = '/dashboard/translations/locales'}
          >
            Manage Locales
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Sitemap Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="space-y-1">
              <div className="text-2xl font-bold">{totalUrls.toLocaleString()}</div>
              <div className="text-sm text-muted-foreground">Total URLs</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl font-bold">{activeLocales.length}</div>
              <div className="text-sm text-muted-foreground">Active Locales</div>
            </div>
            <div className="space-y-1">
              <div className="text-2xl font-bold">{readySitemaps}</div>
              <div className="text-sm text-muted-foreground">Generated Sitemaps</div>
            </div>
            <div className="space-y-1">
              <div className="text-sm font-medium">
                {sitemapData[0]?.lastModified
                  ? new Date(sitemapData[0].lastModified).toLocaleDateString()
                  : 'Never'}
              </div>
              <div className="text-sm text-muted-foreground">Last Updated</div>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleRegenerateAll}
              disabled={regenerating.length > 0}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${regenerating.length > 0 ? 'animate-spin' : ''}`} />
              Regenerate All
            </Button>
            <Button
              variant="outline"
              onClick={() => window.open('/robots.txt', '_blank')}
            >
              <FileText className="w-4 h-4 mr-2" />
              View robots.txt
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Locale Sitemaps Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {sitemapData.map((sitemap) => {
          const isRegenerating = regenerating.includes(sitemap.locale.code);

          return (
            <Card key={sitemap.locale.code} className="relative">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Globe className="w-4 h-4" />
                    <span className="truncate">{sitemap.locale.native_name}</span>
                    <span className="text-xs text-muted-foreground">({sitemap.locale.code})</span>
                  </span>
                  <Badge
                    variant={getStatusVariant(isRegenerating ? 'generating' : sitemap.status)}
                    className="flex items-center gap-1"
                  >
                    {getStatusIcon(isRegenerating ? 'generating' : sitemap.status)}
                    {isRegenerating ? 'Generating' : sitemap.status.replace('_', ' ')}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {sitemap.status === 'ready' ? (
                  <>
                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">URLs:</span>
                        <span className="font-medium">{sitemap.pageCount.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Size:</span>
                        <span className="font-medium">{sitemap.size}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Last Modified:</span>
                        <span className="font-medium">
                          {new Date(sitemap.lastModified).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleViewSitemap(sitemap.url)}
                        title="View sitemap"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleRegenerate(sitemap.locale.code)}
                        disabled={isRegenerating}
                        title="Regenerate sitemap"
                      >
                        <RefreshCw className={`w-4 h-4 ${isRegenerating ? 'animate-spin' : ''}`} />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDownloadSitemap(sitemap.url, sitemap.locale.code)}
                        title="Download sitemap"
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="py-4 text-center">
                    <p className="text-sm text-muted-foreground mb-3">
                      Sitemap not generated yet
                    </p>
                    <Button
                      size="sm"
                      onClick={() => handleRegenerate(sitemap.locale.code)}
                      disabled={isRegenerating}
                    >
                      <RefreshCw className={`w-4 h-4 mr-2 ${isRegenerating ? 'animate-spin' : ''}`} />
                      Generate Now
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Settings Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Sitemap Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="auto-generate" className="flex flex-col gap-1">
              <span>Auto-generate sitemaps</span>
              <span className="text-sm text-muted-foreground font-normal">
                Automatically regenerate sitemaps on schedule
              </span>
            </Label>
            <Switch
              id="auto-generate"
              checked={sitemapSettings.autoGenerate}
              onCheckedChange={(checked) =>
                setSitemapSettings(prev => ({ ...prev, autoGenerate: checked }))
              }
            />
          </div>

          {sitemapSettings.autoGenerate && (
            <div className="space-y-2 pl-6 border-l-2 border-muted">
              <Label htmlFor="frequency">Generation Frequency</Label>
              <Select
                value={sitemapSettings.generateFrequency}
                onValueChange={(value) =>
                  setSitemapSettings(prev => ({ ...prev, generateFrequency: value }))
                }
              >
                <SelectTrigger id="frequency" className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hourly">Hourly</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="flex items-center justify-between">
            <Label htmlFor="alternates" className="flex flex-col gap-1">
              <span>Include hreflang alternates</span>
              <span className="text-sm text-muted-foreground font-normal">
                Add alternate language links for multi-locale pages
              </span>
            </Label>
            <Switch
              id="alternates"
              checked={sitemapSettings.includeAlternates}
              onCheckedChange={(checked) =>
                setSitemapSettings(prev => ({ ...prev, includeAlternates: checked }))
              }
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="priority">Default Priority</Label>
              <Select
                value={sitemapSettings.defaultPriority}
                onValueChange={(value) =>
                  setSitemapSettings(prev => ({ ...prev, defaultPriority: value }))
                }
              >
                <SelectTrigger id="priority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1.0">1.0 (Highest)</SelectItem>
                  <SelectItem value="0.9">0.9</SelectItem>
                  <SelectItem value="0.8">0.8</SelectItem>
                  <SelectItem value="0.7">0.7</SelectItem>
                  <SelectItem value="0.6">0.6</SelectItem>
                  <SelectItem value="0.5">0.5 (Default)</SelectItem>
                  <SelectItem value="0.4">0.4</SelectItem>
                  <SelectItem value="0.3">0.3</SelectItem>
                  <SelectItem value="0.2">0.2</SelectItem>
                  <SelectItem value="0.1">0.1</SelectItem>
                  <SelectItem value="0.0">0.0 (Lowest)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="changefreq">Default Change Frequency</Label>
              <Select
                value={sitemapSettings.defaultChangefreq}
                onValueChange={(value) =>
                  setSitemapSettings(prev => ({ ...prev, defaultChangefreq: value }))
                }
              >
                <SelectTrigger id="changefreq">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="always">Always</SelectItem>
                  <SelectItem value="hourly">Hourly</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                  <SelectItem value="yearly">Yearly</SelectItem>
                  <SelectItem value="never">Never</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="pt-4">
            <Button onClick={() => {
              toast({
                title: "Settings Saved",
                description: "Sitemap settings have been updated successfully.",
              });
            }}>
              Save Settings
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SitemapTab;
