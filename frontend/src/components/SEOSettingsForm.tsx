import React, { useState, useEffect } from 'react';
import { SEOSettingsResponse, SEOSettingsPayload, SEOSettingsFormState } from '@/types/seo';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MediaPicker } from "@/components/ui/media-picker";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api.ts";
import { 
  Settings, 
  Globe, 
  Twitter, 
  Facebook, 
  Code, 
  Shield,
  Eye,
  Image,
  AlertTriangle,
  Check,
  Loader2,
  X
} from "lucide-react";

interface SEOSettingsFormProps {
  localeCode?: string;
  onSave?: () => void;
}

export const SEOSettingsForm: React.FC<SEOSettingsFormProps> = ({ 
  localeCode = 'en',
  onSave 
}) => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState<SEOSettingsFormState>({
    id: 0,
    locale: 0,
    locale_code: '',
    locale_name: '',
    title_suffix: '',
    default_title: '',
    default_description: '',
    default_keywords: '',
    default_og_asset: null,
    default_og_image_url: null,
    default_og_title: '',
    default_og_description: '',
    default_og_type: 'website',
    default_og_site_name: '',
    default_twitter_asset: null,
    default_twitter_image_url: null,
    default_twitter_card: 'summary_large_image',
    default_twitter_site: '',
    default_twitter_creator: '',
    robots_default: 'index,follow',
    canonical_domain: '',
    google_site_verification: '',
    bing_site_verification: '',
    jsonld_default: [],
    organization_jsonld: {},
    meta_author: '',
    meta_generator: 'Bedrock CMS',
    meta_viewport: 'width=device-width, initial-scale=1.0',
    facebook_app_id: '',
    created_at: '',
    updated_at: '',
    _isModified: false,
    _validationErrors: {}
  });
  const [ogImagePickerOpen, setOgImagePickerOpen] = useState(false);
  const [twitterImagePickerOpen, setTwitterImagePickerOpen] = useState(false);
  const [locales, setLocales] = useState<any[]>([]);
  const [selectedLocale, setSelectedLocale] = useState(localeCode);

  // Load locales
  useEffect(() => {
    const loadLocales = async () => {
      try {
        const response = await api.i18n.locales.list({ active_only: true });
        setLocales(response.results || []);
      } catch (error) {
        console.error('Failed to load locales:', error);
      }
    };
    loadLocales();
  }, []);


  // Load SEO settings for selected locale
  useEffect(() => {
    const loadSettings = async () => {
      try {
        setLoading(true);
        const response = await api.seoSettings.getByLocale(selectedLocale);
        
        if (response?.data || response) {
          const data: SEOSettingsResponse = response.data || response;
          
          setSettings({
            ...data,
            // Ensure nulls are handled
            default_og_asset: data.default_og_asset || null,
            default_og_image_url: data.default_og_image_url || null,
            default_twitter_asset: data.default_twitter_asset || null,
            default_twitter_image_url: data.default_twitter_image_url || null,
            // Internal state
            _isModified: false,
            _validationErrors: {}
          });
        }
      } catch (error) {
        console.log('No existing settings, using defaults');
        
        // Initialize with defaults
        setSettings({
          id: 0,
          locale: 0,
          locale_code: selectedLocale,
          locale_name: '',
          title_suffix: '',
          default_title: '',
          default_description: '',
          default_keywords: '',
          default_og_asset: null,
          default_og_image_url: null,
          default_og_title: '',
          default_og_description: '',
          default_og_type: 'website',
          default_og_site_name: '',
          default_twitter_asset: null,
          default_twitter_image_url: null,
          default_twitter_card: 'summary_large_image',
          default_twitter_site: '',
          default_twitter_creator: '',
          robots_default: 'index,follow',
          canonical_domain: '',
          google_site_verification: '',
          bing_site_verification: '',
          jsonld_default: [],
          organization_jsonld: {},
          meta_author: '',
          meta_generator: 'Bedrock CMS',
          meta_viewport: 'width=device-width, initial-scale=1.0',
          facebook_app_id: '',
          created_at: '',
          updated_at: '',
          _isModified: false,
          _validationErrors: {}
        });
      } finally {
        setLoading(false);
      }
    };
    
    if (selectedLocale) {
      loadSettings();
    }
  }, [selectedLocale]);

  const handleSave = async () => {
    try {
      setSaving(true);
      
      // Find locale ID
      const locale = locales.find(l => l.code === selectedLocale);
      if (!locale) {
        toast({
          title: "Error",
          description: "Selected locale not found",
          variant: "destructive"
        });
        return;
      }

      // Prepare payload with exact field mapping
      const payload: SEOSettingsPayload = {
        locale_id: locale.id,
        
        // Basic SEO
        title_suffix: settings.title_suffix || '',
        default_title: settings.default_title || '',
        default_description: settings.default_description || '',
        default_keywords: settings.default_keywords || '',
        
        // Open Graph - use _id suffix for write
        default_og_asset_id: settings.default_og_asset || null,
        default_og_title: settings.default_og_title || '',
        default_og_description: settings.default_og_description || '',
        default_og_type: settings.default_og_type || 'website',
        default_og_site_name: settings.default_og_site_name || '',
        
        // Twitter Card - use _id suffix for write
        default_twitter_asset_id: settings.default_twitter_asset || null,
        default_twitter_card: settings.default_twitter_card || 'summary_large_image',
        default_twitter_site: settings.default_twitter_site || '',
        default_twitter_creator: settings.default_twitter_creator || '',
        
        // Technical SEO
        robots_default: settings.robots_default || 'index,follow',
        canonical_domain: settings.canonical_domain || '',
        google_site_verification: settings.google_site_verification || '',
        bing_site_verification: settings.bing_site_verification || '',
        
        // JSON-LD
        jsonld_default: settings.jsonld_default || [],
        organization_jsonld: settings.organization_jsonld || {},
        
        // Meta tags
        meta_author: settings.meta_author || '',
        meta_generator: settings.meta_generator || 'Bedrock CMS',
        meta_viewport: settings.meta_viewport || 'width=device-width, initial-scale=1.0',
        
        // Social
        facebook_app_id: settings.facebook_app_id || ''
      };

      let response;
      if (settings.id) {
        // Update existing settings
        response = await api.seoSettings.update(settings.id, payload);
      } else {
        // Create new settings
        response = await api.seoSettings.create(payload);
      }
      
      // Update local state with response
      if (response?.data) {
        setSettings({
          ...response.data,
          _isModified: false,
          _validationErrors: {}
        });
      }
      
      toast({
        title: "Success",
        description: "SEO settings saved successfully"
      });
      
      if (onSave) {
        onSave();
      }
    } catch (error: any) {
      console.error('Failed to save SEO settings:', error);
      
      // Handle specific validation errors
      if (error.response?.data) {
        const errors = error.response.data;
        
        // Check for specific field errors
        if (errors.default_og_asset_id) {
          toast({
            title: "Invalid OG Image",
            description: Array.isArray(errors.default_og_asset_id) 
              ? errors.default_og_asset_id[0] 
              : errors.default_og_asset_id,
            variant: "destructive"
          });
        } else if (errors.default_twitter_asset_id) {
          toast({
            title: "Invalid Twitter Image",
            description: Array.isArray(errors.default_twitter_asset_id)
              ? errors.default_twitter_asset_id[0]
              : errors.default_twitter_asset_id,
            variant: "destructive"
          });
        } else {
          toast({
            title: "Error",
            description: errors.detail || "Failed to save SEO settings",
            variant: "destructive"
          });
        }
        
        // Store validation errors in state
        setSettings(prev => ({
          ...prev,
          _validationErrors: errors
        }));
      } else {
        toast({
          title: "Error",
          description: "Failed to save SEO settings. Please try again.",
          variant: "destructive"
        });
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Locale Selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Label>Language</Label>
          <Select value={selectedLocale} onValueChange={setSelectedLocale}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {locales.map(locale => (
                <SelectItem key={locale.code} value={locale.code}>
                  {locale.native_name} ({locale.code})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Check className="mr-2 h-4 w-4" />
              Save Settings
            </>
          )}
        </Button>
      </div>

      <Tabs defaultValue="basic" className="space-y-6">
        <TabsList className="grid grid-cols-5 w-full max-w-3xl">
          <TabsTrigger value="basic">Basic SEO</TabsTrigger>
          <TabsTrigger value="opengraph">Open Graph</TabsTrigger>
          <TabsTrigger value="twitter">Twitter Card</TabsTrigger>
          <TabsTrigger value="technical">Technical</TabsTrigger>
          <TabsTrigger value="structured">Structured Data</TabsTrigger>
        </TabsList>

        {/* Basic SEO Tab */}
        <TabsContent value="basic" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Basic SEO Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="default_title">Default Title</Label>
                  <Input
                    id="default_title"
                    value={settings.default_title || ''}
                    onChange={(e) => setSettings({...settings, default_title: e.target.value})}
                    placeholder="Default page title"
                  />
                </div>
                <div>
                  <Label htmlFor="title_suffix">Title Suffix</Label>
                  <Input
                    id="title_suffix"
                    value={settings.title_suffix || ''}
                    onChange={(e) => setSettings({...settings, title_suffix: e.target.value})}
                    placeholder=" | Your Site Name"
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="default_description">Default Meta Description</Label>
                <Textarea
                  id="default_description"
                  value={settings.default_description || ''}
                  onChange={(e) => setSettings({...settings, default_description: e.target.value})}
                  placeholder="Default description for pages without one..."
                  rows={3}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  {settings.default_description?.length || 0}/160 characters
                </p>
              </div>
              
              <div>
                <Label htmlFor="default_keywords">Default Keywords</Label>
                <Input
                  id="default_keywords"
                  value={settings.default_keywords || ''}
                  onChange={(e) => setSettings({...settings, default_keywords: e.target.value})}
                  placeholder="keyword1, keyword2, keyword3"
                />
              </div>
              
              <div>
                <Label htmlFor="meta_author">Default Author</Label>
                <Input
                  id="meta_author"
                  value={settings.meta_author || ''}
                  onChange={(e) => setSettings({...settings, meta_author: e.target.value})}
                  placeholder="Author name"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Open Graph Tab */}
        <TabsContent value="opengraph" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Open Graph Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="default_og_title">Default OG Title</Label>
                <Input
                  id="default_og_title"
                  value={settings.default_og_title || ''}
                  onChange={(e) => setSettings({...settings, default_og_title: e.target.value})}
                  placeholder="Open Graph title"
                />
              </div>
              
              <div>
                <Label htmlFor="default_og_description">Default OG Description</Label>
                <Textarea
                  id="default_og_description"
                  value={settings.default_og_description || ''}
                  onChange={(e) => setSettings({...settings, default_og_description: e.target.value})}
                  placeholder="Open Graph description..."
                  rows={3}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="default_og_type">OG Type</Label>
                  <Select 
                    value={settings.default_og_type || 'website'}
                    onValueChange={(value) => setSettings({...settings, default_og_type: value})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="website">Website</SelectItem>
                      <SelectItem value="article">Article</SelectItem>
                      <SelectItem value="blog">Blog</SelectItem>
                      <SelectItem value="product">Product</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label htmlFor="default_og_site_name">Site Name</Label>
                  <Input
                    id="default_og_site_name"
                    value={settings.default_og_site_name || ''}
                    onChange={(e) => setSettings({...settings, default_og_site_name: e.target.value})}
                    placeholder="Your Site Name"
                  />
                </div>
              </div>
              
              <div>
                <Label>Default OG Image</Label>
                <div className="flex gap-2 items-center">
                  {settings.default_og_asset ? (
                    <div className="flex items-center gap-2 p-2 border rounded">
                      <Image className="h-4 w-4" />
                      <span className="text-sm">Image selected</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSettings({...settings, default_og_asset: null})}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={() => setOgImagePickerOpen(true)}
                    >
                      <Image className="mr-2 h-4 w-4" />
                      Select Image
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Twitter Card Tab */}
        <TabsContent value="twitter" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Twitter className="h-5 w-5" />
                Twitter Card Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="default_twitter_card">Card Type</Label>
                <Select
                  value={settings.default_twitter_card || 'summary_large_image'}
                  onValueChange={(value) => setSettings({...settings, default_twitter_card: value})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="summary">Summary</SelectItem>
                    <SelectItem value="summary_large_image">Summary with Large Image</SelectItem>
                    <SelectItem value="app">App</SelectItem>
                    <SelectItem value="player">Player</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="default_twitter_site">Site @username</Label>
                  <Input
                    id="default_twitter_site"
                    value={settings.default_twitter_site || ''}
                    onChange={(e) => setSettings({...settings, default_twitter_site: e.target.value})}
                    placeholder="@yoursite"
                  />
                </div>
                
                <div>
                  <Label htmlFor="default_twitter_creator">Creator @username</Label>
                  <Input
                    id="default_twitter_creator"
                    value={settings.default_twitter_creator || ''}
                    onChange={(e) => setSettings({...settings, default_twitter_creator: e.target.value})}
                    placeholder="@creator"
                  />
                </div>
              </div>
              
              <div>
                <Label>Default Twitter Image</Label>
                <div className="flex gap-2 items-center">
                  {settings.default_twitter_asset ? (
                    <div className="flex items-center gap-2 p-2 border rounded">
                      <Image className="h-4 w-4" />
                      <span className="text-sm">Image selected</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSettings({...settings, default_twitter_asset: null})}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={() => setTwitterImagePickerOpen(true)}
                    >
                      <Image className="mr-2 h-4 w-4" />
                      Select Image
                    </Button>
                  )}
                </div>
              </div>
              
              <div>
                <Label htmlFor="facebook_app_id">Facebook App ID</Label>
                <Input
                  id="facebook_app_id"
                  value={settings.facebook_app_id || ''}
                  onChange={(e) => setSettings({...settings, facebook_app_id: e.target.value})}
                  placeholder="Your Facebook App ID"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Technical SEO Tab */}
        <TabsContent value="technical" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Technical SEO Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="robots_default">Default Robots Directive</Label>
                <Select
                  value={settings.robots_default || 'index,follow'}
                  onValueChange={(value) => setSettings({...settings, robots_default: value})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="index,follow">index, follow</SelectItem>
                    <SelectItem value="noindex,follow">noindex, follow</SelectItem>
                    <SelectItem value="index,nofollow">index, nofollow</SelectItem>
                    <SelectItem value="noindex,nofollow">noindex, nofollow</SelectItem>
                    <SelectItem value="none">none</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label htmlFor="canonical_domain">Canonical Domain</Label>
                <Input
                  id="canonical_domain"
                  value={settings.canonical_domain || ''}
                  onChange={(e) => setSettings({...settings, canonical_domain: e.target.value})}
                  placeholder="https://example.com"
                />
                <p className="text-sm text-muted-foreground mt-1">
                  Used for generating canonical URLs
                </p>
              </div>
              
              <div>
                <Label htmlFor="google_site_verification">Google Site Verification</Label>
                <Input
                  id="google_site_verification"
                  value={settings.google_site_verification || ''}
                  onChange={(e) => setSettings({...settings, google_site_verification: e.target.value})}
                  placeholder="Google verification code"
                />
              </div>
              
              <div>
                <Label htmlFor="bing_site_verification">Bing Site Verification</Label>
                <Input
                  id="bing_site_verification"
                  value={settings.bing_site_verification || ''}
                  onChange={(e) => setSettings({...settings, bing_site_verification: e.target.value})}
                  placeholder="Bing verification code"
                />
              </div>
              
              <div>
                <Label htmlFor="meta_viewport">Viewport Meta Tag</Label>
                <Input
                  id="meta_viewport"
                  value={settings.meta_viewport || 'width=device-width, initial-scale=1.0'}
                  onChange={(e) => setSettings({...settings, meta_viewport: e.target.value})}
                />
              </div>
              
              <div>
                <Label htmlFor="meta_generator">Generator Meta Tag</Label>
                <Input
                  id="meta_generator"
                  value={settings.meta_generator || 'Bedrock CMS'}
                  onChange={(e) => setSettings({...settings, meta_generator: e.target.value})}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Structured Data Tab */}
        <TabsContent value="structured" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                Structured Data (JSON-LD)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="organization_jsonld">Organization Schema</Label>
                <Textarea
                  id="organization_jsonld"
                  value={JSON.stringify(settings.organization_jsonld || {}, null, 2)}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value);
                      setSettings({...settings, organization_jsonld: parsed});
                    } catch (error) {
                      // Invalid JSON, just store as is for now
                    }
                  }}
                  placeholder='{"@type": "Organization", "name": "Your Company"}'
                  rows={10}
                  className="font-mono text-sm"
                />
              </div>
              
              <div>
                <Label htmlFor="jsonld_default">Default JSON-LD Blocks</Label>
                <Textarea
                  id="jsonld_default"
                  value={JSON.stringify(settings.jsonld_default || [], null, 2)}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value);
                      setSettings({...settings, jsonld_default: parsed});
                    } catch (error) {
                      // Invalid JSON, just store as is for now
                    }
                  }}
                  placeholder='[{"@type": "WebSite", "@id": "#website"}]'
                  rows={10}
                  className="font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Media Pickers */}
      <MediaPicker
        open={ogImagePickerOpen}
        onOpenChange={setOgImagePickerOpen}
        onSelect={(asset) => {
          setSettings(prevSettings => ({
            ...prevSettings,
            default_og_asset: asset.id,              // Store UUID string
            default_og_image_url: asset.file,        // Store display URL
            _isModified: true
          }));
          setOgImagePickerOpen(false);
        }}
        selectedAssetId={settings.default_og_asset}
        title="Select Open Graph Image"
        description="Choose an image for Open Graph sharing (Recommended: 1200x630px)"
      />
      
      <MediaPicker
        open={twitterImagePickerOpen}
        onOpenChange={setTwitterImagePickerOpen}
        onSelect={(asset) => {
          setSettings(prevSettings => ({
            ...prevSettings,
            default_twitter_asset: asset.id,         // Store UUID string
            default_twitter_image_url: asset.file,   // Store display URL
            _isModified: true
          }));
          setTwitterImagePickerOpen(false);
        }}
        selectedAssetId={settings.default_twitter_asset}
        title="Select Twitter Card Image"
        description="Choose an image for Twitter Card (Recommended: 1200x600px for large image)"
      />
    </div>
  );
};

export default SEOSettingsForm;