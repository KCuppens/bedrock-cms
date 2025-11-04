# Bedrock CMS Architecture Analysis

## Overview
The Bedrock CMS is a Django REST Framework-based headless CMS with a sophisticated block-based content system, comprehensive versioning, audit trails, and role-based access control (RBAC).

---

## 1. REST API ENDPOINTS

### Base API Router (DRF DefaultRouter at `/api/cms/`)

#### 1.1 Pages Management
- **Endpoint:** `/pages/`
- **Class:** `PagesViewSet` (inherits VersioningMixin)
- **Methods:**
  - `GET /pages/` - List pages (paginated)
  - `POST /pages/` - Create new page
  - `GET /pages/{id}/` - Retrieve single page
  - `PUT /pages/{id}/` - Full update
  - `PATCH /pages/{id}/` - Partial update
  - `DELETE /pages/{id}` - Delete page (with cascade option)

**Custom Actions:**
  - `GET /pages/get_by_path/?path=/foo&locale=en&preview={token}` - Get page by URL path (optimized for public consumption)
  - `GET /pages/{id}/children/?locale=en&depth=1` - Get page children
  - `GET /pages/tree/?locale=en&root={id}&depth=2` - Get full page tree structure
  - `POST /pages/reorder/` - Reorder pages (bulk position update)
  - `POST /pages/{id}/move/` - Move page to new parent and position
  - `POST /pages/{id}/duplicate/` - Duplicate page with content
  - `POST /pages/{id}/schedule/` - Schedule publishing at future date
  - `POST /pages/{id}/unschedule/` - Cancel scheduled publishing
  - `GET /pages/scheduled_content/` - List scheduled pages

**Block Management Actions:**
  - `PATCH /pages/{id}/update-block/` - Update specific block
  - `POST /pages/{id}/blocks/insert/` - Insert new block
  - `POST /pages/{id}/blocks/reorder/` - Reorder blocks
  - `POST /pages/{id}/blocks/duplicate/` - Duplicate a block
  - `DELETE /pages/{id}/blocks/{block_index}/` - Delete block
  - `PATCH /pages/{id}/blocks/{block_index}/` - Update block

#### 1.2 Publishing & Versioning (VersioningMixin)
- `POST /pages/{id}/publish/` - Publish page (requires "publish_page" permission)
- `POST /pages/{id}/unpublish/` - Unpublish page
- `GET /pages/{id}/audit/` - Get audit trail for page

#### 1.3 Page Revisions
- **Endpoint:** `/revisions/`
- **Class:** `PageRevisionViewSet`
- **Methods:**
  - `GET /revisions/` - List revisions (filtered by page, user, type)
  - `GET /revisions/{id}/` - Get revision details
- **Custom Actions:**
  - `GET /revisions/{id}/diff/?against={revision_id}` - Compare two revisions
  - `GET /revisions/{id}/diff_current/` - Compare with current page state
  - `POST /revisions/{id}/revert/?comment=...` - Restore page to revision

#### 1.4 Categories & Tags
- **Endpoint:** `/categories/`
  - `GET /categories/` - List categories
  - `POST /categories/` - Create category
  - `GET /categories/{id}/` - Retrieve category
  - `PUT /categories/{id}/` - Update category
  - `PATCH /categories/{id}/` - Partial update
  - `DELETE /categories/{id}/` - Delete category
  - `GET /categories/tree/` - Get hierarchical category tree

- **Endpoint:** `/tags/`
  - `GET /tags/` - List tags
  - `POST /tags/` - Create tag
  - `GET /tags/{id}/` - Get tag
  - `PUT /tags/{id}/` - Update
  - `PATCH /tags/{id}/` - Partial update
  - `DELETE /tags/{id}/` - Delete

- **Endpoint:** `/collections/`
  - `GET /collections/` - List collections
  - `POST /collections/` - Create collection
  - `GET /collections/{id}/` - Get collection
  - `PUT /collections/{id}/` - Update
  - `PATCH /collections/{id}/` - Partial update
  - `DELETE /collections/{id}/` - Delete

#### 1.5 Block Types Management
- **Endpoint:** `/block-types/`
- **Class:** `BlockTypeViewSet`
- **Methods:**
  - `GET /block-types/` - List block types (paginated, searchable)
  - `POST /block-types/` - Create new block type
  - `GET /block-types/{id}/` - Get block type details
  - `PUT /block-types/{id}/` - Update block type
  - `PATCH /block-types/{id}/` - Partial update
  - `DELETE /block-types/{id}/` - Soft delete (deactivate)

**Custom Actions:**
  - `GET /block-types/categories/` - Get all block type categories
  - `POST /block-types/{id}/toggle_active/` - Toggle active status
  - `POST /block-types/{id}/duplicate/` - Duplicate block type configuration
  - `PATCH /block-types/bulk_update/` - Update multiple blocks at once
  - `GET /block-types/fetch_data/?block_type=...&filters=...&limit=10&offset=0` - Fetch dynamic data for block
  - `GET /block-types/stats/` - Get usage statistics
  - `GET /block-types/dashboard_data/` - Get all data for blocks dashboard

#### 1.6 Redirects (SEO)
- **Endpoint:** `/redirects/`
- **Class:** `RedirectViewSet`
- **Methods:**
  - `GET /redirects/` - List redirects (searchable, filterable)
  - `POST /redirects/` - Create redirect
  - `GET /redirects/{id}/` - Get redirect
  - `PUT /redirects/{id}/` - Update
  - `PATCH /redirects/{id}/` - Partial update
  - `DELETE /redirects/{id}/` - Delete

**Custom Actions:**
  - `GET /redirects/lookup/?path=/old-path` - Public lookup (heavily cached)
  - `POST /redirects/{id}/test/` - Test redirect
  - `POST /redirects/import_csv/` - Import redirects from CSV
  - `GET /redirects/export_csv/` - Export redirects to CSV
  - `POST /redirects/validate/` - Validate redirect rules for conflicts/loops

#### 1.7 SEO Settings
- **Endpoint:** `/seo-settings/`
- **Class:** `SeoSettingsViewSet`
- **Methods:** Standard CRUD operations

#### 1.8 Block Registry & Schemas
- `GET /blocks/` - List available block types and schemas
- `GET /blocks/{block_type}/schema/` - Get schema for specific block type

#### 1.9 Navigation & Footer
- `GET /navigation/?locale=en` - Get navigation menu items (cached)
- `GET /footer/?locale=en` - Get footer items
- `GET /site-settings/` - Get site settings

#### 1.10 Audit Trail
- **Endpoint:** `/audit/`
- **Class:** `AuditEntryViewSet`
- **Methods:**
  - `GET /audit/` - List audit entries (searchable, filterable)
  - `GET /audit/{id}/` - Get specific audit entry

#### 1.11 SEO & Structured Data
- `GET /public/seo-settings/{locale_code}/` - Get public SEO settings
- `GET /pages/{id}/schema/` - Get Schema.org markup for page
- `GET /blog/posts/{id}/schema/` - Get Schema.org markup for blog post
- `GET /schema/types/` - List supported schema types
- `GET /schema/templates/?type=...` - Get schema templates
- `POST /schema/validate/` - Validate Schema.org structure

#### 1.12 Sitemaps
- `GET /sitemap-{locale_code}.xml` - XML sitemap (cached, with hreflang)
- `GET /sitemap.xml` - Default locale sitemap redirect

---

## 2. CONTENT MODELS

### Core Models

#### Page Model (`cms.Page`)
**Fields:**
- `id` (AutoField, Primary Key)
- `group_id` (UUID, for content grouping across locales)
- `parent` (ForeignKey to self, nullable - hierarchical structure)
- `position` (PositiveIntegerField, for ordering siblings)
- `locale` (ForeignKey to i18n.Locale)
- `title` (CharField, max 180)
- `slug` (SlugField, max 120, unique per parent+locale)
- `path` (CharField, computed full path, unique per locale)
- `blocks` (JSONField, array of block objects, max 2MB)
- `seo` (JSONField, SEO overrides, max 0.5MB)
- `status` (CharField, choices: draft, pending_review, published, scheduled, rejected)
- `published_at` (DateTimeField, nullable)
- `scheduled_publish_at` (DateTimeField, for scheduled publishing)
- `scheduled_unpublish_at` (DateTimeField, for scheduled unpublishing)
- `in_main_menu` (BooleanField)
- `in_footer` (BooleanField)
- `is_homepage` (BooleanField)
- `submitted_for_review_at` (DateTimeField, nullable)
- `reviewed_by` (ForeignKey to User, nullable)
- `review_notes` (TextField)
- `categories` (ManyToManyField to Category)
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)
- `preview_token` (UUIDField, for draft previews)

**Status Workflow:**
- draft → pending_review → approved/rejected → published/scheduled
- published → scheduled (for future unpublish)

**Permissions:**
- `publish_page` - Publish pages
- `unpublish_page` - Unpublish pages
- `preview_page` - Preview draft pages
- `revert_page` - Revert to previous version
- `translate_page` - Translate pages
- `manage_page_seo` - Manage SEO settings
- `bulk_delete_pages`
- `export_pages`, `import_pages`
- `moderate_content`, `approve_content`, `reject_content`
- `view_moderation_queue`
- `schedule_content`

#### BlockType Model (`cms.BlockType`)
**Fields:**
- `type` (CharField, unique identifier, e.g., "hero", "richtext")
- `component` (CharField, frontend component name)
- `label` (CharField, human-readable label)
- `description` (TextField)
- `category` (CharField, choices: layout, content, media, marketing, dynamic, other)
- `icon` (CharField, Lucide icon name)
- `model_name` (CharField, for dynamic blocks, e.g., "blog.BlogPost")
- `data_source` (CharField, choices: static, single, list, custom)
- `api_endpoint` (CharField)
- `query_schema` (JSONField, for query parameters)
- `is_active` (BooleanField)
- `preload` (BooleanField)
- `editing_mode` (CharField, choices: inline, modal, sidebar)
- `schema` (JSONField, JSON schema for validation)
- `default_props` (JSONField, default properties)
- `order` (PositiveIntegerField, display order)
- `created_by` (ForeignKey to User)
- `updated_by` (ForeignKey to User)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

#### Redirect Model (`cms.Redirect`)
**Fields:**
- `from_path` (CharField, indexed)
- `to_path` (CharField)
- `status` (PositiveSmallIntegerField, choices: 301, 302, 307, 308)
- `is_active` (BooleanField)
- `notes` (TextField)
- `hits` (PositiveIntegerField, usage counter)
- `locale` (ForeignKey to Locale, nullable)
- `created_at` (DateTimeField)

**Unique Constraint:** (from_path, locale)

#### PageRevision Model (`cms.PageRevision`)
**Fields:**
- `id` (UUIDField, primary key)
- `page` (ForeignKey to Page)
- `snapshot` (JSONField, complete page data snapshot)
- `created_by` (ForeignKey to User, nullable)
- `created_at` (DateTimeField)
- `is_published_snapshot` (BooleanField)
- `is_autosave` (BooleanField)
- `comment` (TextField, optional)

#### Category Model (`cms.Category` / `blog.Category`)
**Fields:**
- `name` (CharField, max 100)
- `slug` (SlugField, unique)
- `description` (TextField)
- `parent` (ForeignKey to self, nullable - hierarchical)
- `color` (CharField, hex color)
- `icon` (CharField)
- `order` (IntegerField)
- `is_active` (BooleanField)
- `created_by` (ForeignKey to User)
- `created_at`, `updated_at` (DateTimeField)

#### Tag Model (`cms.Tag` / `blog.Tag`)
**Fields:**
- `name` (CharField, max 50, unique)
- `slug` (SlugField, unique)
- `description` (TextField)
- `color` (CharField, hex color)
- `created_by` (ForeignKey to User)
- `created_at`, `updated_at` (DateTimeField)

#### Collection Model (`cms.Collection`)
**Fields:**
- `name` (CharField, max 200)
- `slug` (SlugField, unique)
- `description` (TextField)
- `cover_image` (URLField)
- `status` (CharField, choices: draft, published, archived)
- `categories` (ManyToManyField to Category)
- `tags` (ManyToManyField to Tag)
- `meta_title`, `meta_description` (CharField/TextField)
- `created_by` (ForeignKey to User)
- `created_at`, `updated_at`, `published_at` (DateTimeField)

#### AuditEntry Model (from `apps.ops`)
**Fields:**
- `actor` (ForeignKey to User)
- `action` (CharField)
- `model_label` (CharField)
- `object_id` (CharField)
- `content_object` (GenericForeignKey)
- `metadata` (JSONField)
- `created_at` (DateTimeField)

---

## 3. BLOCK SYSTEM ARCHITECTURE

### Block Types Registry

The block system uses a **hybrid approach**:
1. **Database-Driven:** `BlockType` model stores block configuration
2. **Pydantic Models:** Python validation models (fallback)
3. **Dynamic:** Blocks can fetch data from other models

### Core Block Models (Pydantic)

```
BaseBlockModel
├── HeroBlockModel (type: "hero")
├── RichTextBlockModel (type: "richtext", "rich_text")
├── ImageBlockModel (type: "image")
├── GalleryBlockModel (type: "gallery")
├── ColumnsBlockModel (type: "columns", nested blocks support)
├── CTABandBlockModel (type: "cta", "cta_band")
├── FAQBlockModel (type: "faq")
└── ContentDetailBlockModel (type: "content_detail", for dynamic content)
```

### Block Structure (JSONField)
```json
{
  "id": "uuid",
  "type": "hero|richtext|image|...",
  "props": {
    "title": "...",
    "content": "...",
    ...
  },
  "schema_version": 1
}
```

### Block Features

**1. Static Blocks:** No data fetching
- Hero, RichText, Image, Gallery, CTA, FAQ

**2. Dynamic Blocks:** Fetch data from models
- Data sources: `single`, `list`, `custom`
- Can query BlogPost, Page, or other models
- Supports filtering, searching, pagination

**3. Content Detail Blocks:** Display specific content
- Configured per presentation page
- Links blog posts, pages to presentation layouts

**4. Nested Blocks:** Columns block supports child blocks
- `blocks` property contains nested block array

### Block Validation
- **File:** `/apps/cms/blocks/validation.py`
- **Classes:** `BaseBlockModel` + specific models
- **Features:**
  - Pydantic validation
  - Sanitization of block content
  - Size validation (2MB limit for page blocks)

### Block Data Fetching Endpoint
```
GET /block-types/fetch_data/?block_type=posts_list&filters={...}&limit=10&offset=0
```
- Supports filters, search, ordering, pagination
- Security: Whitelist of allowed filter fields
- Dynamic serializer generation from model

---

## 4. CONTENT CREATION & EDITING WORKFLOW

### Page Lifecycle

```
Create Draft → (Auto-save) → Submit for Review → Approve/Reject → Publish
                                     ↓
                                  Rejected ↻
                                  
Published → (Schedule Unpublish) → Draft
```

### Creation Workflow
1. **POST /pages/** - Create blank draft page
   - Requires `add_page` permission
   - Auto-computes path from slug + parent
   - Sets position at end of siblings
   
2. **Content Editing**
   - **Block Operations:**
     - Insert: `POST /pages/{id}/blocks/insert/`
     - Update: `PATCH /pages/{id}/update-block/`
     - Reorder: `POST /pages/{id}/blocks/reorder/`
     - Duplicate: `POST /pages/{id}/blocks/duplicate/`
     - Delete: `DELETE /pages/{id}/blocks/{index}/`
   
   - **Page Updates:** `PATCH /pages/{id}/`
     - Blocks, SEO, title, slug, categories
     - Validates block structure
     - Triggers revision creation
   
3. **Revision Management**
   - Auto-creates revision on save (if changed)
   - Autosave revisions (every N seconds frontend-side)
   - Published snapshots (on publish)
   - Manual comments on revisions

### Publishing Workflow
1. **Draft → Pending Review**
   - `POST /pages/{id}/submit_for_review/` (in model method)
   - Sets `submitted_for_review_at`
   - Clears review notes

2. **Pending Review → Published**
   - `POST /pages/{id}/publish/`
   - Requires `publish_page` permission
   - Sets `status = "published"`
   - Sets `published_at = now()`
   - Creates published snapshot revision
   - Triggers audit entry

3. **Published → Draft (Unpublish)**
   - `POST /pages/{id}/unpublish/`
   - Sets `status = "draft"`
   - Clears `published_at`
   - Creates audit entry

### Scheduling Workflow
1. **Schedule Publishing**
   - `POST /pages/{id}/schedule/`
   - Sets `status = "scheduled"`
   - Sets `scheduled_publish_at`
   - Background task publishes automatically

2. **Schedule Unpublishing**
   - Set `scheduled_unpublish_at` on published page
   - Background task unpublishes automatically

3. **Cancel Scheduling**
   - `POST /pages/{id}/unschedule/`

### Versioning & Revisions
- **Auto-revision:** Created on save via signals
- **Manual revision:** User can add comments
- **Diff:** Compare any two revisions or current state
- **Revert:** Restore page to previous revision
  - `POST /revisions/{id}/revert/?comment=...`
  - Requires `revert_page` permission

### Serializers
- **PageWriteSerializer:** For create/update
  - Validates blocks, SEO, parent
  - Handles locale assignment
  
- **PageReadSerializer:** For list/retrieve
  - Includes computed SEO, revisions, audit info
  - Optional resolved SEO data
  
- **PublicPageSerializer:** For frontend consumption
  - Minimal fields: id, title, slug, path, blocks, SEO, locale
  - Resolved SEO with canonical URLs
  - Cache headers

---

## 5. AUTHENTICATION & PERMISSION SYSTEMS

### Authentication

**Types:**
- Session authentication (standard Django)
- Token authentication (via DRF)
- User groups + roles

### Role-Based Access Control (RBAC)

**Models:**

1. **ScopedLocale**
   - Scope group permissions to specific locales
   - Users in group can only access content in scoped locales
   
2. **ScopedSection**
   - Scope group permissions to path prefixes
   - E.g., group "blog_editors" has section "/blog"
   - Supports hierarchical matching

**RBACMixin Methods:**
- `user_has_locale_access(user)` - Check locale permission
- `user_has_section_access(user)` - Check section permission
- `user_has_scope_access(user)` - Check both

### Permission System

**Custom Permissions (on Page model):**
- `cms.add_page`
- `cms.change_page`
- `cms.delete_page`
- `cms.publish_page` - Special permission for publishing
- `cms.unpublish_page`
- `cms.preview_page` - Preview draft pages
- `cms.revert_page` - Revert to previous version
- `cms.translate_page`
- `cms.manage_page_seo`
- `cms.bulk_delete_pages`
- `cms.export_pages`
- `cms.import_pages`
- `cms.moderate_content` - Review submissions
- `cms.approve_content`
- `cms.reject_content`
- `cms.view_moderation_queue`
- `cms.schedule_content`

**Permission Classes (DRF):**
- `AllowAny` - Public endpoints (get_by_path, navigation, redirects lookup)
- `IsAuthenticated` - Most management endpoints
- `DjangoModelPermissions` - Model-level CRUD
- `RBACPermission` - Custom RBAC enforcement
- `IsAuthenticatedOrReadOnly` - Read public, write authenticated

### View-Level Permission Control

**Example from PagesViewSet:**
```python
def get_permissions(self):
    if self.action in ["list", "retrieve", "get_by_path", "children", "tree"]:
        return [permissions.AllowAny()]  # Public read
    elif self.action in ["publish", "unpublish"]:
        return [IsAuthenticated(), DjangoModelPermissions()]  # Requires publish permission
    else:
        return [IsAuthenticated(), DjangoModelPermissions()]  # Standard CRUD
```

### Query Filtering by Permissions

**Pages ViewSet:**
- Anonymous users: Only see published pages
- Authenticated without permission: Only published pages
- Authenticated with permission: See draft + published
- Superuser: All pages

**Revisions ViewSet:**
- Authenticated only
- Filters based on page access

### Security Features

1. **Path Sanitization**
   - Double URL-decode prevention
   - Path traversal blocking ("../", "//")
   - Normalization

2. **Block Content Sanitization**
   - HTML sanitization (bleach library)
   - Allowed tags/attributes whitelist
   - Protocol whitelist (http, https, mailto, tel)

3. **Dynamic Data Filtering**
   - Whitelist of allowed filter fields
   - Prevents ORM injection
   - Safe serializer generation (excludes sensitive fields)

4. **File Upload Validation**
   - CSV import: File extension, MIME type, size checks
   - Max file size: 5MB

5. **Rate Limiting**
   - DjangoRatelimit on expensive operations
   - Sitemap: 10/hour per IP
   - Throttling: User, write operations, publish operations

### Audit Trail

**AuditEntry captures:**
- User (actor)
- Action (publish, unpublish, delete, create, approve, reject, etc.)
- Content object (generic FK)
- Metadata (changes, reasons, etc.)
- Timestamp

**Logged Actions:**
- Page creation, updates, deletion
- Publishing/unpublishing
- Revisions and reverts
- Approvals/rejections
- Content scheduling

### Admin Access

**Superuser capabilities:**
- Full access to all content
- All locales
- All sections
- Full audit visibility

---

## 6. KEY API PATTERNS

### Response Format
```json
{
  "id": 123,
  "title": "Page Title",
  "blocks": [...],
  "status": "published",
  "created_at": "2024-01-01T00:00:00Z",
  ...
}
```

### Pagination
- StandardResultsSetPagination
- Query params: `?page=1&page_size=20`
- Response includes: `count`, `next`, `previous`, `results`

### Filtering & Search
- DjangoFilterBackend
- SearchFilter for text fields
- OrderingFilter for sorting

### Caching Strategy
```
Published pages: 5 minutes (CDN cache)
Redirects lookup: 30 minutes
Navigation menu: Per locale key
Block types registry: 5 minutes
SEO settings: 1 hour
```

### Error Responses
```json
{
  "error": "Error message",
  "field_errors": {"field": ["error1", "error2"]}
}
```

### Sorting
- By position (for siblings)
- By created_at / updated_at
- Custom ordering per viewset

---

## SUMMARY

**Architecture Type:** Headless CMS with REST API
**Core Framework:** Django REST Framework
**Database Models:** 8+ core models (Page, BlockType, Redirect, PageRevision, Category, Tag, Collection, AuditEntry)
**Content Structure:** Block-based, JSON-stored, hierarchical pages
**Versioning:** Full snapshot-based with diff/revert
**Publishing:** Multi-status workflow with scheduling
**Security:** RBAC with scoped locales/sections, sanitization, audit trails
**Performance:** Heavy caching, indexed queries, pagination, CDN-friendly headers

