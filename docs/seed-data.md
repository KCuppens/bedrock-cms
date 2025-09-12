# Demo Data Seeding

The Bedrock CMS includes a comprehensive seeding system for setting up demo data quickly during development.

## Quick Start

```bash
# Create demo data
python manage.py seed_site

# Clear and recreate demo data
python manage.py seed_site --clear
```

## What Gets Created

### Locales
- **English (en-US)** - Default locale
- **Spanish (es-MX)** - With fallback to English

### Sample Pages
- **Home** (`/`) - Hero section with CTA
- **About** (`/about/`) - Company information with team image
- **Services** (`/services/`) - Three-column service layout
- **Contact** (`/contact/`) - Contact information and form

### Blog Content
- **5 Blog Posts** - Mix of English and Spanish content
- **2 Categories** - Technology and Business
- **5 Tags** - Django, Python, Web Development, Startup, Tips
- **Presentation Page** - Template for blog post rendering

### Media Assets
- **5 Sample Assets** - Placeholder images for hero, team, blog, gallery
- **Alt text** - Localized in both English and Spanish
- **Proper metadata** - Width, height, file size, checksums

### Redirects
- **4 Sample Redirects** - Common legacy URL patterns

### Demo User
- **Username**: demo
- **Password**: demo123
- **Permissions**: Staff and superuser access

## Content Structure

### Page Hierarchy
```
/ (Home)
├── /about/ (About Us)
├── /services/ (Our Services)
└── /contact/ (Contact Us)
```

### Spanish Pages
```
/ (Inicio)
├── /acerca/ (Acerca de Nosotros)
├── /servicios/ (Nuestros Servicios)
└── /contacto/ (Contactanos)
```

### Blog Posts
- "Getting Started with Django CMS" (English + Spanish)
- "5 Tips for Building Scalable Web Applications" (English)
- Various categories and tags for testing

## Block Examples

The seeded content demonstrates all major block types:

- **Hero blocks** - With titles, subtitles, CTAs, background images
- **Rich text** - With HTML content, headings, lists
- **Image blocks** - With alt text and captions
- **Columns** - Multi-column layouts with nested blocks
- **CTA bands** - Call-to-action sections
- **Content detail** - For blog post presentation

## SEO Examples

All pages include comprehensive SEO data:
- Meta titles and descriptions
- Keywords
- Open Graph data
- Canonical URLs
- Hreflang alternates (where applicable)

## Development Workflow

1. **Initial Setup**
   ```bash
   python manage.py migrate
   python manage.py seed_site
   ```

2. **Reset Data**
   ```bash
   python manage.py seed_site --clear
   ```

3. **Frontend Development**
   - Access demo pages at various URLs
   - Test multilingual content
   - Verify API responses

4. **Content Testing**
   - Login with demo/demo123
   - Edit pages and blocks
   - Test publishing workflow

## API Testing

Use the seeded data to test API endpoints:

```bash
# Get homepage
curl "http://localhost:8000/api/pages?path=/&locale=en-US"

# Get blog posts
curl "http://localhost:8000/api/content/blog.blogpost/"

# Search content
curl "http://localhost:8000/api/search?q=django&locale=en-US"
```

## Customization

The seed script can be extended to create additional content:

```python
# In seed_site.py
def create_custom_content(self):
    # Add your custom seeding logic
    pass
```

The script is designed to be:
- **Idempotent** - Safe to run multiple times
- **Extensible** - Easy to add new content types
- **Realistic** - Uses proper relationships and metadata
- **Multilingual** - Demonstrates i18n features

## Production Notes

**Never run this command in production!**

The seed script is designed for development and testing environments only. It creates demo data that should not be used in live systems.

## Related Commands

```bash
# Block scaffolder
python manage.py block_new testimonial

# Registry scaffolder
python manage.py cms_scaffold app.Model

# Other useful development commands
python manage.py runserver
python manage.py shell
python manage.py dbshell
```
