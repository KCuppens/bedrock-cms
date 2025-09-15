# SEO Metadata Tests Documentation

This document describes the comprehensive SEO metadata test suite located in `test_seo_metadata.py`.

## Test Coverage Overview

### 1. SEO Metadata Tests (`SeoMetadataTestCase`)
- **Basic metadata generation**: Tests title, description, keywords, and robots directives
- **Fallback mechanisms**: Tests when pages have no custom SEO data
- **Draft page handling**: Ensures draft pages get `noindex,nofollow`
- **Open Graph metadata**: Tests OG title, description, type, and image generation
- **Twitter Card metadata**: Tests Twitter card type, title, description, and image
- **JSON-LD structured data**: Tests Schema.org structured data merging and generation
- **Deep merge functionality**: Tests the utility function for merging nested SEO dictionaries

### 2. SEO Validation Tests (`SeoValidationTestCase`)
- **Title length validation**: Ensures titles are under 60 characters (Google truncation limit)
- **Description length validation**: Validates 120-160 character optimal range
- **Robots directive validation**: Tests valid/invalid robots meta directives
- **JSON-LD structure validation**: Ensures JSON-LD is properly structured as a list

### 3. Multilingual SEO Tests (`MultilingualSeoTestCase`)
- **Hreflang alternates**: Tests generation of hreflang links for all active locales
- **Canonical URL generation**: Tests canonical URL generation with various base URLs
- **SEO links generation**: Tests combined canonical + alternates functionality
- **Settings integration**: Tests that settings respect Django configuration
- **Locale-specific settings**: Tests different SEO settings per locale

### 4. Dynamic SEO Generation Tests (`DynamicSeoGenerationTestCase`)
- **Auto-generation from page title**: Tests automatic SEO generation when no custom data
- **Partial override with fallback**: Tests mixing custom and auto-generated SEO data
- **Template-based generation**: Tests SEO generation from page content blocks
- **Custom field override logic**: Ensures manual SEO data always takes precedence

### 5. SEO Utility Functions Tests (`SeoUtilityFunctionsTestCase`)
- **Meta tags HTML generation**: Tests HTML meta tag generation from SEO data
- **Schema.org JSON-LD generation**: Tests JSON-LD script tag generation
- **Context handling**: Tests proper @context insertion in JSON-LD

### 6. API Integration Tests (`SeoApiIntegrationTestCase`)
- **CRUD operations**: Tests creating, reading, updating, deleting SEO settings via API
- **Validation**: Tests API-level validation for robots, JSON-LD, and file uploads
- **Public API**: Tests unauthenticated public SEO settings endpoint
- **Preview functionality**: Tests SEO preview API for editors
- **Bulk operations**: Tests bulk update and duplication of SEO settings
- **Image handling**: Tests file upload validation for OG and Twitter images

### 7. SEO Performance Tests (`SeoPerformanceTestCase`)
- **Large JSON-LD handling**: Tests performance with large structured data
- **Mobile optimization**: Tests viewport meta tag for mobile-first indexing
- **Core Web Vitals**: Tests SEO integration considerations for performance metrics

## Key Features Tested

### Metadata Generation
- Title suffix handling and customization
- Meta description with length optimization
- Open Graph tags (og:title, og:description, og:image, og:type, og:site_name)
- Twitter Card metadata (card type, title, description, image)
- Canonical URL generation with domain handling
- Hreflang alternates for multilingual sites

### Validation & Quality Control
- SEO field length validation (title 60 chars, description 120-160 chars)
- Robots directive validation against standard values
- JSON-LD structure validation
- File type validation for social media images
- Duplicate content prevention via canonical URLs

### Multilingual Support
- Hreflang generation for active locales only
- Locale-specific SEO settings and defaults
- Cross-locale canonical URL handling
- Language-specific fallback mechanisms

### Dynamic Features
- Auto-generation from page content when no custom SEO
- Template-based SEO from page blocks/content
- Fallback hierarchy: Custom → Auto-generated → Global defaults
- Draft page protection (forced noindex,nofollow)

### API & Integration
- Full CRUD API for SEO settings management
- Public SEO data API for frontend consumption
- SEO preview functionality for editors
- Bulk operations for multi-locale management
- File upload handling for social media images

## Running the Tests

```bash
# Run all SEO metadata tests
python manage.py test apps.cms.tests.test_seo_metadata --settings=apps.config.settings.test

# Run specific test class
python manage.py test apps.cms.tests.test_seo_metadata.SeoMetadataTestCase --settings=apps.config.settings.test

# Run with verbose output
python manage.py test apps.cms.tests.test_seo_metadata --settings=apps.config.settings.test --verbosity=2
```

## Test Data Setup

Each test class sets up comprehensive test data including:
- Multiple locales (English, Spanish, French, German)
- Test file uploads for social media images
- SEO settings with all field types populated
- Pages with various SEO configurations
- User accounts for API authentication testing

## Coverage Areas

This test suite provides comprehensive coverage for:
- ✅ **SEO Metadata Generation**: Title, description, OG, Twitter Card, JSON-LD
- ✅ **SEO Validation**: Length limits, format validation, duplicate detection
- ✅ **Multilingual SEO**: Hreflang, locale-specific metadata, canonical URLs
- ✅ **Dynamic Generation**: Auto-generation, fallbacks, template-based SEO
- ✅ **Schema.org Structured Data**: JSON-LD generation and validation
- ✅ **API Integration**: Full API coverage including public endpoints
- ✅ **Performance Considerations**: Large data handling, mobile optimization

The test suite ensures that the SEO functionality works correctly across all supported scenarios and provides confidence in the robustness of the SEO implementation.
