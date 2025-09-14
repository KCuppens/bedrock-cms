// Custom error classes for better error handling
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class PermissionError extends APIError {
  constructor(message: string, data?: any) {
    super(message, 403, data);
    this.name = 'PermissionError';
  }
}

export class AuthenticationError extends APIError {
  constructor(message: string, data?: any) {
    super(message, 401, data);
    this.name = 'AuthenticationError';
  }
}

import type {
  ApiResponse,
  PaginatedResponse,
  Page,
  PageCreateRequest,
  PageUpdateRequest,
  PageFilters,
  PageRevision,
  ScheduledTask,
  MediaAsset,
  MediaUploadRequest,
  MediaFilters,
  TranslationUnit,
  TranslationUpdateRequest,
  TranslationFilters,
  User,
  Redirect,
  RedirectCreateRequest,
  RedirectFilters,
  RedirectTestResult,
  RedirectBulkCreateRequest,
  RedirectImportResult,
  RedirectStats,
  RequestConfig,
  // CMS Types
  Category,
  CategoryCreateRequest,
  CategoryFilters,
  Tag,
  TagCreateRequest,
  TagFilters,
  Collection,
  CollectionCreateRequest,
  CollectionFilters,
  CollectionItem,
  // Blog Types
  BlogPost,
  BlogPostCreateRequest,
  BlogPostFilters,
  BlogPostRevision,
  BlogCategory,
  BlogCategoryCreateRequest,
  BlogTag,
  BlogTagCreateRequest,
  // Analytics Types
  PageView,
  TrafficData,
  AnalyticsFilters,
  Assessment,
  AssessmentCreateRequest,
  AssessmentFilters,
  Risk,
  RiskTimelineEntry,
  Threat,
  ThreatStats,
  AnalyticsSummary,
  // User & Role Management Types
  Role,
  RoleCreateRequest,
  Permission,
  UserInviteRequest,
  UserFilters,
  Scope,
  // Enhanced i18n Types
  TranslationGlossaryEntry,
  TranslationGlossaryCreateRequest,
  TranslationQueueItem,
  UiMessageNamespace,
  UiMessageBulkUpdate
} from '@/types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Comprehensive API client for Bedrock CMS
 *
 * Example usage:
 * ```typescript
 * // CMS operations
 * const categories = await api.cms.categories.list();
 * const blogPosts = await api.blog.posts.list({ status: 'published' });
 *
 * // Analytics
 * const trafficData = await api.analytics.traffic();
 * const assessments = await api.analytics.assessments.list();
 *
 * // User management
 * const users = await api.userManagement.users.list();
 * const roles = await api.userManagement.roles.list();
 *
 * // i18n
 * const glossary = await api.i18n.glossary.list({ locale: 'en' });
 * const translationQueue = await api.i18n.translationQueue.list();
 * ```
 */
class ApiClient {
  private baseURL: string;
  private token: string | null = null;
  private csrfToken: string | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    // Get token from localStorage if available
    this.token = localStorage.getItem('api_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('api_token', token);
    } else {
      localStorage.removeItem('api_token');
    }
  }

  private addPermissionHeaders(headers: HeadersInit): void {
    try {
      // Get current locale from localStorage or context
      const currentLocale = localStorage.getItem('current_locale') || 'en';
      // Ensure ASCII-only characters for HTTP headers
      headers['X-Locale'] = this.encodeHeaderValue(currentLocale);

      // Get user scopes from localStorage (set by auth context)
      const userScopes = localStorage.getItem('user_scopes');
      if (userScopes) {
        headers['X-User-Scopes'] = this.encodeHeaderValue(userScopes);
      }

      // Add user role for quick backend checks
      const userRole = localStorage.getItem('user_role');
      if (userRole) {
        headers['X-User-Role'] = this.encodeHeaderValue(userRole);
      }
    } catch (error) {
      // Fail silently - headers are optional enhancements
      console.debug('Failed to add permission headers:', error);
    }
  }

  private encodeHeaderValue(value: string): string {
    try {
      // Check if the value contains only ASCII characters
      if (/^[\x00-\x7F]*$/.test(value)) {
        return value;
      }

      // If non-ASCII characters are present, base64 encode the value
      // This is a common pattern for handling non-ASCII header values
      const encoded = btoa(unescape(encodeURIComponent(value)));
      return `=?UTF-8?B?${encoded}?=`; // RFC 2047 encoded-word format
    } catch (error) {
      console.warn('Failed to encode header value:', value, error);
      // Fallback: remove non-ASCII characters
      return value.replace(/[^\x00-\x7F]/g, '');
    }
  }

  private handlePermissionError(errorData: any, url: string): void {
    console.warn('Permission denied for:', url, errorData);

    // Show user-friendly toast notification
    if (typeof window !== 'undefined') {
      // Dispatch custom event for error handling
      window.dispatchEvent(new CustomEvent('permission-error', {
        detail: {
          message: errorData.message,
          url,
          data: errorData
        }
      }));
    }
  }

  private handleAuthError(): void {
    console.warn('Authentication error - redirecting to login');

    // Clear stored tokens
    this.setToken(null);
    localStorage.removeItem('user_scopes');
    localStorage.removeItem('user_role');

    // Dispatch auth error event
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('auth-error'));
    }
  }

  private async getCsrfToken(): Promise<string> {
    if (this.csrfToken) {
      return this.csrfToken;
    }

    try {
      // Use the full URL with the backend base URL
      const response = await fetch('http://localhost:8000/auth/csrf/', {
        method: 'GET',
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        this.csrfToken = data.csrfToken;
        return this.csrfToken;
      }
    } catch (error) {
      console.error('Failed to fetch CSRF token:', error);
    }

    // Try to get from cookie as fallback
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];

    if (cookieValue) {
      this.csrfToken = cookieValue;
      return cookieValue;
    }

    return '';
  }

  private async request<T>({ method, url, params, data, headers = {}, signal }: RequestConfig): Promise<T> {
    // If baseURL is empty, use relative URLs which will go through Vite proxy
    const fullUrl = this.baseURL ? new URL(url, this.baseURL) : new URL(url, window.location.origin);

    // Add query parameters
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          fullUrl.searchParams.set(key, String(value));
        }
      });
    }

    const requestHeaders: HeadersInit = {
      'Content-Type': 'application/json',
      ...headers,
    };

    // Add authentication
    if (this.token) {
      requestHeaders['Authorization'] = `Bearer ${this.token}`;
    }

    // Add permission context headers
    this.addPermissionHeaders(requestHeaders);

    // Add CSRF token for state-changing methods
    if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
      const csrfToken = await this.getCsrfToken();
      if (csrfToken) {
        requestHeaders['X-CSRFToken'] = csrfToken;
      }
    }

    // Validate all headers are ASCII-safe before making request
    const safeHeaders: HeadersInit = {};
    Object.entries(requestHeaders).forEach(([key, value]) => {
      if (typeof value === 'string') {
        safeHeaders[key] = this.encodeHeaderValue(value);
      } else {
        safeHeaders[key] = value;
      }
    });

    const config: RequestInit = {
      method,
      headers: safeHeaders,
      credentials: 'include', // Include cookies for session auth
      signal, // Add abort signal support
    };

    if (data && method !== 'GET') {
      if (data instanceof FormData) {
        // Remove content-type for FormData - browser will set it with boundary
        delete requestHeaders['Content-Type'];
        config.body = data;
      } else {
        config.body = JSON.stringify(data);
      }
    }

    try {
      const response = await fetch(fullUrl.toString(), config);

      if (!response.ok) {
        // Handle different error types
        if (response.status === 403) {
          // Try CSRF token refresh for non-GET requests
          if (method !== 'GET') {
            this.csrfToken = null;
            const csrfToken = await this.getCsrfToken();
            if (csrfToken) {
              requestHeaders['X-CSRFToken'] = csrfToken;
              // Re-validate headers for retry request
              const retrySafeHeaders: HeadersInit = {};
              Object.entries(requestHeaders).forEach(([key, value]) => {
                if (typeof value === 'string') {
                  retrySafeHeaders[key] = this.encodeHeaderValue(value);
                } else {
                  retrySafeHeaders[key] = value;
                }
              });
              config.headers = retrySafeHeaders;
              const retryResponse = await fetch(fullUrl.toString(), config);
              if (retryResponse.ok) {
                return retryResponse.status === 204 ? {} as T : await retryResponse.json();
              }
            }
          }

          // Handle permission errors specifically
          const errorData = await response.json().catch(() => ({
            error: 'Permission denied',
            message: 'You do not have permission to perform this action',
            status: 403
          }));

          this.handlePermissionError(errorData, url);
          throw new PermissionError(errorData.message || errorData.error || 'Permission denied');
        }

        if (response.status === 401) {
          // Handle authentication errors
          this.handleAuthError();
          throw new AuthenticationError('Authentication required');
        }

        const errorData = await response.json().catch(() => ({
          error: 'Request failed',
          message: `HTTP ${response.status} ${response.statusText}`,
          status: response.status
        }));

        throw new APIError(errorData.message || errorData.error || 'Request failed', response.status, errorData);
      }

      // Handle empty responses (like 204 No Content)
      if (response.status === 204) {
        return {} as T;
      }

      return await response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }


  // Files/Media API
  files = {
    list: (filters?: { file_type?: string; is_public?: boolean; search?: string; page?: number; limit?: number }): Promise<PaginatedResponse<any>> =>
      this.request({ method: 'GET', url: '/api/v1/files/', params: filters }),

    get: (id: string): Promise<ApiResponse<any>> =>
      this.request({ method: 'GET', url: `/api/v1/files/${id}/` }),

    upload: (data: { file: File; description?: string; tags?: string; is_public?: boolean; expires_at?: string }): Promise<ApiResponse<any>> => {
      const formData = new FormData();
      formData.append('file', data.file);
      if (data.description) formData.append('description', data.description);
      if (data.tags) formData.append('tags', data.tags);
      if (data.is_public !== undefined) formData.append('is_public', data.is_public.toString());
      if (data.expires_at) formData.append('expires_at', data.expires_at);

      return this.request({
        method: 'POST',
        url: '/api/v1/files/',
        data: formData
      });
    },

    update: (id: string, data: { description?: string; tags?: string; is_public?: boolean }): Promise<ApiResponse<any>> =>
      this.request({ method: 'PATCH', url: `/api/v1/files/${id}/`, data }),

    delete: (id: string): Promise<void> =>
      this.request({ method: 'DELETE', url: `/api/v1/files/${id}/` }),

    downloadUrl: (id: string): Promise<ApiResponse<{ download_url: string; expires_in: number; filename: string }>> =>
      this.request({ method: 'GET', url: `/api/v1/files/${id}/download_url/` }),

    download: (id: string): Promise<void> =>
      window.open(`/api/v1/files/${id}/download/`),

    signedUploadUrl: (data: { filename: string; content_type?: string; max_size?: number }): Promise<ApiResponse<{ upload_url: string; fields: any; storage_path: string; expires_in: number }>> =>
      this.request({ method: 'POST', url: '/api/v1/files/signed_upload_url/', data }),

    myFiles: (): Promise<PaginatedResponse<any>> =>
      this.request({ method: 'GET', url: '/api/v1/files/my_files/' }),

    publicFiles: (): Promise<PaginatedResponse<any>> =>
      this.request({ method: 'GET', url: '/api/v1/files/public/' }),
  };


  // Translations API (basic translation units)
  translations = {
    list: (filters?: TranslationFilters): Promise<PaginatedResponse<TranslationUnit>> =>
      this.request({ method: 'GET', url: '/api/v1/i18n/translation-units/', params: filters }),

    get: (id: string): Promise<ApiResponse<TranslationUnit>> =>
      this.request({ method: 'GET', url: `/api/v1/i18n/translation-units/${id}/` }),

    update: (id: string, data: TranslationUpdateRequest): Promise<ApiResponse<TranslationUnit>> =>
      this.request({ method: 'PUT', url: `/api/v1/i18n/translation-units/${id}/`, data }),

    bulkUpdate: (updates: Array<{ id: string; data: TranslationUpdateRequest }>): Promise<ApiResponse<TranslationUnit[]>> =>
      this.request({ method: 'PATCH', url: '/api/v1/i18n/translation-units/bulk/', data: { updates } }),

    suggest: (id: string): Promise<ApiResponse<{ suggestion: string }>> =>
      this.request({ method: 'POST', url: `/api/v1/i18n/translation-units/${id}/suggest/` }),

    approve: (id: string): Promise<ApiResponse<TranslationUnit>> =>
      this.request({ method: 'POST', url: `/api/v1/i18n/translation-units/${id}/approve/` }),
  };

  // Authentication API
  auth = {
    login: (email: string, password: string): Promise<ApiResponse<{ user: User; message: string }>> =>
      this.request({ method: 'POST', url: '/auth/login/', data: { email, password } }),

    logout: (): Promise<ApiResponse<{ message: string }>> =>
      this.request({ method: 'POST', url: '/auth/logout/' }),

    currentUser: (): Promise<User> =>
      this.request({ method: 'GET', url: '/auth/users/me/' }),

    register: (data: { email: string; password1: string; password2: string; first_name?: string; last_name?: string }): Promise<ApiResponse<{ user: User; message: string }>> =>
      this.request({ method: 'POST', url: '/auth/users/register/', data }),

    changePassword: (oldPassword: string, newPassword1: string, newPassword2: string): Promise<ApiResponse<{ message: string }>> =>
      this.request({ method: 'POST', url: '/auth/users/change-password/', data: { old_password: oldPassword, new_password1: newPassword1, new_password2: newPassword2 } }),

    resetPassword: (email: string): Promise<ApiResponse<{ message: string }>> =>
      this.request({ method: 'POST', url: '/auth/password-reset/', data: { email } }),

    resetPasswordConfirm: (uid: string, token: string, newPassword1: string, newPassword2: string): Promise<ApiResponse<{ message: string }>> =>
      this.request({ method: 'POST', url: '/auth/password-reset/confirm/', data: { uid, token, new_password1: newPassword1, new_password2: newPassword2 } }),

    checkSession: (): Promise<User | null> =>
      this.request({ method: 'GET', url: '/auth/session/' }).catch(() => null),
  };

  // Accounts API (user profile management)
  accounts = {
    updateProfile: (data: { first_name?: string; last_name?: string; email?: string; name?: string }): Promise<ApiResponse<User>> =>
      this.request({ method: 'PATCH', url: '/auth/users/me/', data }),

    changePassword: (data: { old_password: string; new_password1: string; new_password2: string }): Promise<ApiResponse<{ message: string }>> =>
      this.request({ method: 'POST', url: '/auth/users/change-password/', data }),

    getProfile: (): Promise<ApiResponse<User>> =>
      this.request({ method: 'GET', url: '/auth/users/me/' }),

    uploadAvatar: (file: File): Promise<ApiResponse<{ avatar_url: string }>> => {
      const formData = new FormData();
      formData.append('avatar', file);
      return this.request({
        method: 'POST',
        url: '/auth/users/avatar/',
        data: formData
      });
    },
  };

  // CMS API
  cms = {
    // Categories
    categories: {
      list: (filters?: CategoryFilters): Promise<PaginatedResponse<Category>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/categories/', params: filters }),

      get: (id: number): Promise<ApiResponse<Category>> =>
        this.request({ method: 'GET', url: `/api/v1/cms/categories/${id}/` }),

      create: (data: CategoryCreateRequest): Promise<ApiResponse<Category>> =>
        this.request({ method: 'POST', url: '/api/v1/cms/categories/', data }),

      update: (id: number, data: Partial<CategoryCreateRequest>): Promise<ApiResponse<Category>> =>
        this.request({ method: 'PATCH', url: `/api/v1/cms/categories/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/cms/categories/${id}/` }),

      tree: (): Promise<ApiResponse<Category[]>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/categories/tree/' }),
    },

    // Tags
    tags: {
      list: (filters?: TagFilters): Promise<PaginatedResponse<Tag>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/tags/', params: filters }),

      get: (id: number | string): Promise<ApiResponse<Tag>> =>
        this.request({ method: 'GET', url: `/api/v1/cms/tags/${id}/` }),

      create: (data: TagCreateRequest): Promise<ApiResponse<Tag>> =>
        this.request({ method: 'POST', url: '/api/v1/cms/tags/', data }),

      update: (id: number | string, data: Partial<TagCreateRequest>): Promise<ApiResponse<Tag>> =>
        this.request({ method: 'PATCH', url: `/api/v1/cms/tags/${id}/`, data }),

      delete: (id: number | string): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/cms/tags/${id}/` }),

      popular: (limit?: number): Promise<ApiResponse<Tag[]>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/tags/popular/', params: { limit } }),

      trending: (limit?: number): Promise<ApiResponse<Tag[]>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/tags/trending/', params: { limit } }),

      unused: (): Promise<ApiResponse<Tag[]>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/tags/unused/' }),
    },

    // Collections
    collections: {
      list: (filters?: CollectionFilters): Promise<PaginatedResponse<Collection>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/collections/', params: filters }),

      get: (id: number): Promise<ApiResponse<Collection>> =>
        this.request({ method: 'GET', url: `/api/v1/cms/collections/${id}/` }),

      create: (data: CollectionCreateRequest): Promise<ApiResponse<Collection>> =>
        this.request({ method: 'POST', url: '/api/v1/cms/collections/', data }),

      update: (id: number, data: Partial<CollectionCreateRequest>): Promise<ApiResponse<Collection>> =>
        this.request({ method: 'PATCH', url: `/api/v1/cms/collections/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/cms/collections/${id}/` }),

      publish: (id: number): Promise<ApiResponse<Collection>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/collections/${id}/publish/` }),

      unpublish: (id: number): Promise<ApiResponse<Collection>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/collections/${id}/unpublish/` }),

      items: (id: number): Promise<ApiResponse<CollectionItem[]>> =>
        this.request({ method: 'GET', url: `/api/v1/cms/collections/${id}/items/` }),

      addItem: (id: number, data: { content_type: string; object_id: number; position?: number }): Promise<ApiResponse<CollectionItem>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/collections/${id}/items/`, data }),

      removeItem: (id: number, itemId: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/cms/collections/${id}/items/${itemId}/` }),
    },

    // Pages (update existing with correct URL)
    pages: {
      list: (filters?: PageFilters): Promise<PaginatedResponse<Page>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/pages/', params: filters }),

      get: (id: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'GET', url: `/api/v1/cms/pages/${id}/` }),

      getByPath: (path: string, locale?: string): Promise<ApiResponse<Page>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/pages/get_by_path/', params: { path, locale } }),

      create: (data: PageCreateRequest): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: '/api/v1/cms/pages/', data }),

      update: (id: number, data: PageUpdateRequest): Promise<ApiResponse<Page>> =>
        this.request({ method: 'PATCH', url: `/api/v1/cms/pages/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/cms/pages/${id}/` }),

      publish: (id: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/publish/` }),

      unpublish: (id: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/unpublish/` }),

      schedule: (id: number, data: { publish_at: string; unpublish_at?: string }): Promise<ApiResponse<any>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/schedule/`, data }),

      scheduleUnpublish: (id: number, data: { unpublish_at: string }): Promise<ApiResponse<any>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/schedule-unpublish/`, data }),

      unschedule: (id: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/unschedule/` }),

      scheduledTasks: (params?: { status?: string; from_date?: string; to_date?: string }): Promise<ApiResponse<{ count: number; results: ScheduledTask[] }>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/pages/scheduled-tasks/', params }),

      duplicate: (id: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/duplicate/` }),

      children: (id: number, locale?: string, depth?: number): Promise<ApiResponse<Page[]>> =>
        this.request({ method: 'GET', url: `/api/v1/cms/pages/${id}/children/`, params: { locale, depth } }),

      tree: (locale?: string, depth?: number, root?: number): Promise<ApiResponse<Page[]>> =>
        this.request({ method: 'GET', url: '/api/v1/cms/pages/tree/', params: { locale, depth, root } }),

      move: (id: number, newParentId?: number, position?: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/move/`, data: { new_parent_id: newParentId, position } }),

      reorder: (parentId: number | null, pageIds: number[]): Promise<ApiResponse<{ success: boolean; reordered_count: number; parent_id: number | null }>> =>
        this.request({ method: 'POST', url: '/api/v1/cms/pages/reorder/', data: { parent_id: parentId, page_ids: pageIds } }),

      insertBlock: (id: number, block: any, at?: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/blocks/insert/`, data: { block, at } }),

      reorderBlocks: (id: number, fromIndex: number, toIndex: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/blocks/reorder/`, data: { from: fromIndex, to: toIndex } }),

      deleteBlock: (id: number, blockIndex: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/cms/pages/${id}/blocks/${blockIndex}/` }),

      duplicateBlock: (id: number, data: { block_index: number }): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/pages/${id}/blocks/duplicate/`, data }),

      updateBlock: (id: number, data: { block_index: number; props: any }): Promise<ApiResponse<Page>> =>
        this.request({ method: 'PATCH', url: `/api/v1/cms/pages/${id}/update-block/`, data }),

      revisions: (id: number): Promise<PaginatedResponse<PageRevision>> =>
        this.request({ method: 'GET', url: `/api/v1/cms/revisions/`, params: { page_id: id } }),

      revision: (id: string): Promise<ApiResponse<PageRevision>> =>
        this.request({ method: 'GET', url: `/api/v1/cms/revisions/${id}/` }),

      revert: (id: number, revisionId: number): Promise<ApiResponse<Page>> =>
        this.request({ method: 'POST', url: `/api/v1/cms/revisions/${revisionId}/revert/` }),
    },

  };

  // Blocks API
  blocks = {
    list: (): Promise<{block_types: any[]}> =>
      this.request({ method: 'GET', url: '/api/v1/cms/blocks/' }),

    getSchema: (blockType: string): Promise<any> =>
      this.request({ method: 'GET', url: `/api/v1/cms/blocks/${blockType}/schema/` }),
  };

  // Block Types API (CMS Management)
  blockTypes = {
    dashboardData: (signal?: AbortSignal): Promise<{block_types: any[], categories: any[], stats: any}> =>
      this.request({ method: 'GET', url: '/api/v1/cms/block-types/dashboard_data/', signal }),

    list: (filters?: {category?: string, is_active?: boolean, search?: string}, signal?: AbortSignal): Promise<{results: any[]}> =>
      this.request({ method: 'GET', url: '/api/v1/cms/block-types/', params: filters, signal }),

    get: (id: number, signal?: AbortSignal): Promise<any> =>
      this.request({ method: 'GET', url: `/api/v1/cms/block-types/${id}/`, signal }),

    create: (data: any, signal?: AbortSignal): Promise<any> =>
      this.request({ method: 'POST', url: '/api/v1/cms/block-types/', data, signal }),

    update: (id: number, data: any, signal?: AbortSignal): Promise<any> =>
      this.request({ method: 'PATCH', url: `/api/v1/cms/block-types/${id}/`, data, signal }),

    delete: (id: number, signal?: AbortSignal): Promise<void> =>
      this.request({ method: 'DELETE', url: `/api/v1/cms/block-types/${id}/`, signal }),

    toggleActive: (id: number, signal?: AbortSignal): Promise<{id: number, is_active: boolean, message: string}> =>
      this.request({ method: 'POST', url: `/api/v1/cms/block-types/${id}/toggle_active/`, signal }),

    duplicate: (id: number, signal?: AbortSignal): Promise<any> =>
      this.request({ method: 'POST', url: `/api/v1/cms/block-types/${id}/duplicate/`, signal }),

    categories: (signal?: AbortSignal): Promise<any[]> =>
      this.request({ method: 'GET', url: '/api/v1/cms/block-types/categories/', signal }),

    stats: (signal?: AbortSignal): Promise<{total: number, active: number, inactive: number, by_category: any, preload_enabled: number}> =>
      this.request({ method: 'GET', url: '/api/v1/cms/block-types/stats/', signal }),
  };

  // Blog API
  blog = {
    // Posts
    posts: {
      list: (filters?: BlogPostFilters): Promise<PaginatedResponse<BlogPost>> =>
        this.request({ method: 'GET', url: '/api/v1/blog/posts/', params: filters }),

      get: (id: number): Promise<ApiResponse<BlogPost>> =>
        this.request({ method: 'GET', url: `/api/v1/blog/posts/${id}/` }),

      create: (data: BlogPostCreateRequest): Promise<ApiResponse<BlogPost>> =>
        this.request({ method: 'POST', url: '/api/v1/blog/posts/', data }),

      update: (id: number, data: Partial<BlogPostCreateRequest>): Promise<ApiResponse<BlogPost>> =>
        this.request({ method: 'PATCH', url: `/api/v1/blog/posts/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/blog/posts/${id}/` }),

      publish: (id: number): Promise<ApiResponse<BlogPost>> =>
        this.request({ method: 'POST', url: `/api/v1/blog/posts/${id}/publish/` }),

      unpublish: (id: number): Promise<ApiResponse<BlogPost>> =>
        this.request({ method: 'POST', url: `/api/v1/blog/posts/${id}/unpublish/` }),

      duplicate: (id: number, data?: any): Promise<ApiResponse<BlogPost>> =>
        this.request({ method: 'POST', url: `/api/v1/blog/posts/${id}/duplicate/`, data }),

      revisions: (id: number): Promise<PaginatedResponse<BlogPostRevision>> =>
        this.request({ method: 'GET', url: `/api/v1/blog/posts/${id}/revisions/` }),

      autosave: (id: number, data: Partial<BlogPostCreateRequest>): Promise<ApiResponse<BlogPost>> =>
        this.request({ method: 'POST', url: `/api/v1/blog/posts/${id}/autosave/`, data }),

      revert: (id: number, revisionId: number): Promise<ApiResponse<BlogPost>> =>
        this.request({ method: 'POST', url: `/api/v1/blog/posts/${id}/revert/${revisionId}/` }),
    },

    // Categories
    categories: {
      list: (): Promise<PaginatedResponse<BlogCategory>> =>
        this.request({ method: 'GET', url: '/api/v1/blog/categories/' }),

      get: (id: number): Promise<ApiResponse<BlogCategory>> =>
        this.request({ method: 'GET', url: `/api/v1/blog/categories/${id}/` }),

      create: (data: BlogCategoryCreateRequest): Promise<ApiResponse<BlogCategory>> =>
        this.request({ method: 'POST', url: '/api/v1/blog/categories/', data }),

      update: (id: number, data: Partial<BlogCategoryCreateRequest>): Promise<ApiResponse<BlogCategory>> =>
        this.request({ method: 'PATCH', url: `/api/v1/blog/categories/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/blog/categories/${id}/` }),
    },

    // Tags
    tags: {
      list: (): Promise<PaginatedResponse<BlogTag>> =>
        this.request({ method: 'GET', url: '/api/v1/blog/tags/' }),

      get: (id: number): Promise<ApiResponse<BlogTag>> =>
        this.request({ method: 'GET', url: `/api/v1/blog/tags/${id}/` }),

      create: (data: BlogTagCreateRequest): Promise<ApiResponse<BlogTag>> =>
        this.request({ method: 'POST', url: '/api/v1/blog/tags/', data }),

      update: (id: number, data: Partial<BlogTagCreateRequest>): Promise<ApiResponse<BlogTag>> =>
        this.request({ method: 'PATCH', url: `/api/v1/blog/tags/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/blog/tags/${id}/` }),
    },

  };

  // SEO Settings API
  seoSettings = {
    list: (params?: { locale?: string; active_only?: boolean; include_defaults?: boolean }): Promise<ApiResponse<any>> =>
      this.request({ method: 'GET', url: '/api/v1/cms/seo-settings/', params }),

    get: (id: number): Promise<ApiResponse<any>> =>
      this.request({ method: 'GET', url: `/api/v1/cms/seo-settings/${id}/` }),

    getByLocale: (localeCode: string): Promise<ApiResponse<any>> =>
      this.request({ method: 'GET', url: `/api/v1/cms/seo-settings/${localeCode}/` }),

    create: (data: any): Promise<ApiResponse<any>> =>
      this.request({ method: 'POST', url: '/api/v1/cms/seo-settings/', data }),

    update: (id: number, data: any): Promise<ApiResponse<any>> =>
      this.request({ method: 'PATCH', url: `/api/v1/cms/seo-settings/${id}/`, data }),

    delete: (id: number): Promise<void> =>
      this.request({ method: 'DELETE', url: `/api/v1/cms/seo-settings/${id}/` }),

    duplicate: (sourceLocale: number, targetLocale: number): Promise<ApiResponse<any>> =>
      this.request({
        method: 'POST',
        url: '/api/v1/cms/seo-settings/duplicate/',
        data: { source_locale: sourceLocale, target_locale: targetLocale }
      }),

    bulkUpdate: (updates: any[]): Promise<ApiResponse<any>> =>
      this.request({ method: 'POST', url: '/api/v1/cms/seo-settings/bulk_update/', data: { updates } }),

    preview: (params: { locale?: string; page_title?: string; page_description?: string }): Promise<ApiResponse<any>> =>
      this.request({ method: 'GET', url: '/api/v1/cms/seo-settings/preview/', params }),

    // Public SEO settings for frontend (no authentication required)
    getPublic: (localeCode: string): Promise<ApiResponse<any>> =>
      this.request({ method: 'GET', url: `/api/v1/cms/public/seo-settings/${localeCode}/` }),
  };

  // Enhanced Redirects API
  redirects = {
    list: (filters?: RedirectFilters): Promise<PaginatedResponse<Redirect>> =>
      this.request({ method: 'GET', url: '/api/v1/redirects/', params: filters }),

    get: (id: number): Promise<ApiResponse<Redirect>> =>
      this.request({ method: 'GET', url: `/api/v1/redirects/${id}/` }),

    create: (data: RedirectCreateRequest): Promise<ApiResponse<Redirect>> =>
      this.request({ method: 'POST', url: '/api/v1/redirects/', data }),

    update: (id: number, data: Partial<RedirectCreateRequest>): Promise<ApiResponse<Redirect>> =>
      this.request({ method: 'PATCH', url: `/api/v1/redirects/${id}/`, data }),

    delete: (id: number): Promise<void> =>
      this.request({ method: 'DELETE', url: `/api/v1/redirects/${id}/` }),

    test: (id: number): Promise<ApiResponse<RedirectTestResult>> =>
      this.request({ method: 'POST', url: `/api/v1/redirects/${id}/test/` }),

    importCSV: (file: File): Promise<ApiResponse<RedirectImportResult>> => {
      const formData = new FormData();
      formData.append('file', file);
      return this.request({ method: 'POST', url: '/api/v1/redirects/import_csv/', data: formData });
    },

    exportCSV: (): Promise<Blob> =>
      fetch(`${this.baseURL}/api/v1/redirects/export_csv/`, {
        headers: this.token ? { 'Authorization': `Bearer ${this.token}` } : {},
        credentials: 'include',
      }).then(r => r.blob()),

    validate: (): Promise<ApiResponse<{ total_redirects: number; issues_found: number; issues: any[] }>> =>
      this.request({ method: 'POST', url: '/api/v1/redirects/validate/' }),
  };

  // Analytics API
  analytics = {
    // Traffic data
    traffic: (filters?: AnalyticsFilters): Promise<ApiResponse<TrafficData>> =>
      this.request({ method: 'GET', url: '/api/v1/analytics/traffic/', params: filters }),

    pageViews: (filters?: AnalyticsFilters): Promise<PaginatedResponse<PageView>> =>
      this.request({ method: 'GET', url: '/api/v1/analytics/page-views/', params: filters }),

    // Assessments
    assessments: {
      list: (filters?: AssessmentFilters): Promise<PaginatedResponse<Assessment>> =>
        this.request({ method: 'GET', url: '/api/v1/analytics/assessments/', params: filters }),

      create: (data: AssessmentCreateRequest): Promise<ApiResponse<Assessment>> =>
        this.request({ method: 'POST', url: '/api/v1/analytics/assessments/', data }),

      update: (id: number, data: Partial<AssessmentCreateRequest>): Promise<ApiResponse<Assessment>> =>
        this.request({ method: 'PATCH', url: `/api/v1/analytics/assessments/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/analytics/assessments/${id}/` }),
    },

    // Risks
    risks: {
      list: (): Promise<PaginatedResponse<Risk>> =>
        this.request({ method: 'GET', url: '/api/v1/analytics/risks/' }),

      timeline: (riskId: number): Promise<ApiResponse<RiskTimelineEntry[]>> =>
        this.request({ method: 'GET', url: `/api/v1/analytics/risks/${riskId}/timeline/` }),
    },

    // Threats
    threats: {
      list: (): Promise<PaginatedResponse<Threat>> =>
        this.request({ method: 'GET', url: '/api/v1/analytics/threats/' }),

      stats: (): Promise<ApiResponse<ThreatStats>> =>
        this.request({ method: 'GET', url: '/api/v1/analytics/threats/stats/' }),
    },

    // Dashboard summary
    summary: (): Promise<ApiResponse<AnalyticsSummary>> =>
      this.request({ method: 'GET', url: '/api/v1/analytics/summary/' }),
  };

  // Enhanced User & Role Management API
  userManagement = {
    // Users
    users: {
      list: (filters?: UserFilters): Promise<PaginatedResponse<User>> =>
        this.request({ method: 'GET', url: '/auth/users-management/', params: filters }),

      get: (id: number): Promise<ApiResponse<User>> =>
        this.request({ method: 'GET', url: `/auth/users-management/${id}/` }),

      update: (id: number, data: { first_name?: string; last_name?: string; email?: string }): Promise<ApiResponse<User>> =>
        this.request({ method: 'PUT', url: `/auth/users-management/${id}/`, data }),

      invite: (data: { email: string; roles?: number[]; role?: string; message?: string; resend?: boolean }): Promise<ApiResponse<{ message: string; user_id: number }>> =>
        this.request({ method: 'POST', url: '/auth/users-management/invite/', data }),

      updateRoles: (id: number, roleIds: number[]): Promise<ApiResponse<{ message: string; roles: string[] }>> =>
        this.request({ method: 'PUT', url: `/auth/users-management/${id}/roles/`, data: { role_ids: roleIds } }),

      deactivate: (id: number): Promise<ApiResponse<User>> =>
        this.request({ method: 'POST', url: `/auth/users-management/${id}/deactivate/` }),

      reactivate: (id: number): Promise<ApiResponse<User>> =>
        this.request({ method: 'POST', url: `/auth/users-management/${id}/reactivate/` }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/auth/users-management/${id}/` }),
    },

    // Roles
    roles: {
      list: (): Promise<PaginatedResponse<Role>> =>
        this.request({ method: 'GET', url: '/auth/roles/' }),

      get: (id: number): Promise<ApiResponse<Role>> =>
        this.request({ method: 'GET', url: `/auth/roles/${id}/` }),

      create: (data: RoleCreateRequest): Promise<ApiResponse<Role>> =>
        this.request({ method: 'POST', url: '/auth/roles/', data }),

      update: (id: number, data: Partial<RoleCreateRequest>): Promise<ApiResponse<Role>> =>
        this.request({ method: 'PATCH', url: `/auth/roles/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/auth/roles/${id}/` }),

      updatePermissions: (id: number, permissionIds: number[]): Promise<ApiResponse<Role>> =>
        this.request({ method: 'POST', url: `/auth/roles/${id}/permissions/`, data: { permission_ids: permissionIds } }),
    },

    // Permissions
    permissions: {
      list: (): Promise<PaginatedResponse<Permission>> =>
        this.request({ method: 'GET', url: '/auth/permissions/' }),

      get: (id: number): Promise<ApiResponse<Permission>> =>
        this.request({ method: 'GET', url: `/auth/permissions/${id}/` }),
    },

    // Scopes
    scopes: (): Promise<ApiResponse<Scope[]>> =>
      this.request({ method: 'GET', url: '/auth/scopes/' }),
  };

  // Enhanced i18n API
  i18n = {
    // Locales
    locales: {
      list: (filters?: { is_active?: boolean; active_only?: boolean; page?: number; limit?: number }): Promise<PaginatedResponse<any>> =>
        this.request({ method: 'GET', url: '/api/v1/i18n/locales/', params: filters }),

      get: (id: number): Promise<ApiResponse<any>> =>
        this.request({ method: 'GET', url: `/api/v1/i18n/locales/${id}/` }),

      create: (data: any): Promise<ApiResponse<any>> =>
        this.request({ method: 'POST', url: '/api/v1/i18n/locales/', data }),

      update: (id: number, data: any): Promise<ApiResponse<any>> =>
        this.request({ method: 'PUT', url: `/api/v1/i18n/locales/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/i18n/locales/${id}/` }),

      toggleActive: (id: number): Promise<ApiResponse<{ message: string; locale: any }>> =>
        this.request({ method: 'POST', url: `/api/v1/i18n/locales/${id}/toggle_active/` }),

      setDefault: (id: number): Promise<ApiResponse<{ message: string; locale: any }>> =>
        this.request({ method: 'POST', url: `/api/v1/i18n/locales/${id}/set_default/` }),
    },

    // Glossary
    glossary: {
      list: (filters?: { locale?: string; q?: string; page?: number; limit?: number }): Promise<PaginatedResponse<TranslationGlossaryEntry>> =>
        this.request({ method: 'GET', url: '/api/v1/i18n/glossary/', params: filters }),

      create: (data: TranslationGlossaryCreateRequest): Promise<ApiResponse<TranslationGlossaryEntry>> =>
        this.request({ method: 'POST', url: '/api/v1/i18n/glossary/', data }),

      update: (id: number, data: Partial<TranslationGlossaryCreateRequest>): Promise<ApiResponse<TranslationGlossaryEntry>> =>
        this.request({ method: 'PATCH', url: `/api/v1/i18n/glossary/${id}/`, data }),

      delete: (id: number): Promise<void> =>
        this.request({ method: 'DELETE', url: `/api/v1/i18n/glossary/${id}/` }),

      search: (term: string, locale?: string): Promise<ApiResponse<TranslationGlossaryEntry[]>> =>
        this.request({ method: 'GET', url: '/api/v1/i18n/glossary/search/', params: { term, locale } }),
    },

    // Translation Queue
    translationQueue: {
      list: (filters?: { status?: string; assignee_id?: number; priority?: string; page?: number; limit?: number }): Promise<PaginatedResponse<TranslationQueueItem>> =>
        this.request({ method: 'GET', url: '/api/v1/i18n/translations/', params: filters }),
    },

    // Translation Actions
    translations: {
      approve: (id: string): Promise<ApiResponse<TranslationUnit>> =>
        this.request({ method: 'POST', url: `/api/v1/i18n/translation-units/${id}/approve/` }),

      reject: (id: string, reason?: string): Promise<ApiResponse<TranslationUnit>> =>
        this.request({ method: 'POST', url: `/api/v1/i18n/translation-units/${id}/reject/`, data: { reason } }),

      markAsDraft: (id: string, comment?: string): Promise<ApiResponse<TranslationUnit>> =>
        this.request({ method: 'POST', url: `/api/v1/i18n/translation-units/${id}/mark_as_draft/`, data: { comment } }),

      markNeedsReview: (id: string, comment?: string): Promise<ApiResponse<TranslationUnit>> =>
        this.request({ method: 'POST', url: `/api/v1/i18n/translation-units/${id}/mark_needs_review/`, data: { comment } }),

      mtSuggest: (id: string, text: string, sourceLocale: string, targetLocale: string, service?: string): Promise<ApiResponse<{ suggestion: string }>> =>
        this.request({
          method: 'POST',
          url: `/api/v1/i18n/translation-units/${id}/mt_suggest/`,
          data: {
            text,
            source_locale: sourceLocale,
            target_locale: targetLocale,
            service: service || 'auto'
          }
        }),

      complete: (id: string): Promise<ApiResponse<TranslationUnit>> =>
        this.request({ method: 'POST', url: `/api/v1/i18n/translation-units/${id}/complete/` }),

      history: (id: string): Promise<ApiResponse<any[]>> =>
        this.request({ method: 'GET', url: `/api/v1/i18n/translation-units/${id}/history/` }),

      assign: (id: string, assignedToId?: number, comment?: string): Promise<ApiResponse<TranslationUnit>> =>
        this.request({
          method: 'POST',
          url: `/api/v1/i18n/translation-units/${id}/assign/`,
          data: { assigned_to: assignedToId, comment }
        }),

      bulkAssign: (translationUnitIds: number[], assignedToId?: number, comment?: string): Promise<ApiResponse<{
        assigned: any[],
        errors: any[],
        total_requested: number,
        total_assigned: number,
        assignee: { id: number | null, email: string | null } | null
      }>> =>
        this.request({
          method: 'POST',
          url: `/api/v1/i18n/translation-units/bulk_assign/`,
          data: {
            translation_unit_ids: translationUnitIds,
            assigned_to: assignedToId,
            comment
          }
        }),
    },

    // UI Messages
    uiMessages: {
      bulkUpdate: (data: UiMessageBulkUpdate): Promise<ApiResponse<{ updated: number }>> =>
        this.request({ method: 'POST', url: '/api/v1/i18n/ui-messages/bulk-update/', data }),

      namespaces: (): Promise<ApiResponse<UiMessageNamespace[]>> =>
        this.request({ method: 'GET', url: '/api/v1/i18n/ui-messages/namespaces/' }),

      bundle: (locale: string): Promise<Record<string, any>> =>
        this.request({ method: 'GET', url: `/api/v1/i18n/ui/messages/${locale}.json` }),
    },
  };

  // Schema & Documentation
  schema = {
    openapi: (): Promise<any> =>
      this.request({ method: 'GET', url: '/api/schema' }),

    openApiYaml: (): Promise<string> =>
      fetch(`${this.baseURL}/api/schema.yaml`).then(r => r.text()),
  };

  // Convenience aliases for backward compatibility
  get pages() {
    return this.cms.pages;
  }

  get users() {
    return {
      list: this.userManagement.users.list,
      get: this.userManagement.users.get,
      me: (): Promise<ApiResponse<User>> =>
        this.request({ method: 'GET', url: '/auth/users/me/' }),
    };
  }
}

// Create and export a singleton instance
export const api = new ApiClient(API_BASE_URL);

// Export types for convenience
export type * from '@/types/api';

// Utility functions
export const isApiError = (error: any): error is { message: string } => {
  return error && typeof error.message === 'string';
};

export const handleApiError = (error: unknown): string => {
  if (isApiError(error)) {
    return error.message;
  }
  return 'An unexpected error occurred';
};
