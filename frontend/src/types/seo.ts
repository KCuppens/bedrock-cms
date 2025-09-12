// UUID string type for clarity
type UUIDString = string;

// Asset reference used in SEO settings
export interface SEOAssetReference {
  id: UUIDString;           // The UUID of the FileUpload
  url: string;              // The download URL for display
  filename: string;         // Original filename
  width?: number;           // Image width in pixels
  height?: number;          // Image height in pixels
}

// SEO Settings as received from API (READ)
export interface SEOSettingsResponse {
  id: number;
  locale: number;
  locale_code: string;
  locale_name: string;

  // Basic SEO
  title_suffix: string;
  default_title: string;
  default_description: string;
  default_keywords: string;

  // Open Graph - READ format
  default_og_asset: UUIDString | null;        // UUID of the asset
  default_og_image_url: string | null;        // Full URL for display
  default_og_title: string;
  default_og_description: string;
  default_og_type: string;
  default_og_site_name: string;

  // Twitter Card - READ format
  default_twitter_asset: UUIDString | null;   // UUID of the asset
  default_twitter_image_url: string | null;   // Full URL for display
  default_twitter_card: string;
  default_twitter_site: string;
  default_twitter_creator: string;

  // Technical SEO
  robots_default: string;
  canonical_domain: string;
  google_site_verification: string;
  bing_site_verification: string;

  // JSON-LD
  jsonld_default: any[];
  organization_jsonld: Record<string, any>;

  // Meta tags
  meta_author: string;
  meta_generator: string;
  meta_viewport: string;

  // Social
  facebook_app_id: string;

  // Timestamps
  created_at: string;
  updated_at: string;
}

// SEO Settings for API submission (WRITE)
export interface SEOSettingsPayload {
  locale_id: number;

  // Basic SEO
  title_suffix?: string;
  default_title?: string;
  default_description?: string;
  default_keywords?: string;

  // Open Graph - WRITE format
  default_og_asset_id?: UUIDString | null;    // UUID to send to backend
  default_og_title?: string;
  default_og_description?: string;
  default_og_type?: string;
  default_og_site_name?: string;

  // Twitter Card - WRITE format
  default_twitter_asset_id?: UUIDString | null; // UUID to send to backend
  default_twitter_card?: string;
  default_twitter_site?: string;
  default_twitter_creator?: string;

  // Technical SEO
  robots_default?: string;
  canonical_domain?: string;
  google_site_verification?: string;
  bing_site_verification?: string;

  // JSON-LD
  jsonld_default?: any[];
  organization_jsonld?: Record<string, any>;

  // Meta tags
  meta_author?: string;
  meta_generator?: string;
  meta_viewport?: string;

  // Social
  facebook_app_id?: string;
}

// Internal state for the form component
export interface SEOSettingsFormState extends SEOSettingsResponse {
  // Additional fields for UI state
  _isModified: boolean;
  _validationErrors: Record<string, string>;
}