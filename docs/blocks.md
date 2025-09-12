# Block System Overview

The Bedrock CMS block system provides a flexible way to create structured content using composable components.

## What are Blocks?

Blocks are JSON-defined content components with:
- **Type**: Unique identifier (e.g., `rich_text`, `hero`, `image`)
- **Schema Version**: For forward compatibility
- **Props**: Block-specific configuration and content

## Block Structure

```json
{
  "type": "block_type",
  "schema_version": 1,
  "props": {
    "property": "value"
  }
}
```

## Available Block Types

### Core Blocks

- **`rich_text`** - Rich text content with HTML
- **`image`** - Single image with alt text and caption
- **`hero`** - Hero section with background and text
- **`columns`** - Multi-column layout with nested blocks
- **`gallery`** - Image gallery
- **`cta_band`** - Call-to-action banner
- **`faq`** - Frequently asked questions
- **`content_detail`** - Dynamic content from registered models

## Creating Custom Blocks

Use the block scaffolder to create new block types:

```bash
python manage.py block_new testimonial \\
  --description "Customer testimonial with quote and author" \\
  --props "quote:str:Enter testimonial quote" "author:str:Author Name" "rating:int:5"
```

This generates:
- Pydantic validation model in `apps/cms/blocks/validation.py`
- Test file in `tests/unit/test_blocks_testimonial.py`
- Documentation in `docs/blocks/testimonial.md`

## Block Validation

All blocks are validated using Pydantic models:

```python
from apps.cms.blocks.validation import validate_blocks

blocks = [
    {
        "type": "rich_text",
        "props": {
            "content": "<p>Hello world!</p>"
        }
    }
]

validated_blocks = validate_blocks(blocks)
```

### Security

HTML content in blocks is automatically sanitized to prevent XSS attacks:
- Dangerous tags (`<script>`, etc.) are removed
- Event handlers (`onclick`, etc.) are stripped
- Invalid URLs are cleaned

## Nested Blocks

The `columns` block supports nesting other blocks:

```json
{
  "type": "columns",
  "props": {
    "columns": ["50%", "50%"],
    "gap": "md"
  },
  "blocks": [
    {
      "type": "rich_text",
      "props": {
        "content": "<p>Left column</p>"
      }
    },
    {
      "type": "image",
      "props": {
        "src": "/media/image.jpg",
        "alt": "Right column image"
      }
    }
  ]
}
```

## Frontend Integration

In your frontend, create a block renderer:

```javascript
// React example
function BlockRenderer({ blocks }) {
  return blocks.map((block, index) => {
    switch (block.type) {
      case 'rich_text':
        return <RichTextBlock key={index} props={block.props} />;
      case 'image':
        return <ImageBlock key={index} props={block.props} />;
      case 'hero':
        return <HeroBlock key={index} props={block.props} />;
      default:
        console.warn(`Unknown block type: ${block.type}`);
        return null;
    }
  });
}
```

## Block Development Workflow

1. **Plan your block**: Define the content structure and properties
2. **Generate scaffold**: Use `python manage.py block_new <type>`
3. **Customize schema**: Update the Pydantic model as needed
4. **Write tests**: Ensure validation works correctly
5. **Frontend implementation**: Create the rendering component
6. **Documentation**: Update the generated docs

## Best Practices

- **Keep blocks focused**: Each block should have a single responsibility
- **Use semantic naming**: Block types should be descriptive (`testimonial` not `box`)
- **Provide defaults**: All properties should have sensible default values
- **Validate thoroughly**: Use Pydantic's rich validation features
- **Document properties**: Include clear descriptions for all fields
- **Test edge cases**: Ensure blocks handle invalid/missing data gracefully

## API Usage

Blocks are used in Pages and other content models:

```http
POST /api/v1/cms/pages/
{
  "title": "My Page",
  "slug": "my-page",
  "blocks": [
    {
      "type": "hero",
      "props": {
        "title": "Welcome",
        "subtitle": "To our amazing site"
      }
    }
  ]
}
```

## Common Issues

### Validation Errors
- Check property names and types match the schema
- Ensure required fields are provided
- Use the correct block type string

### HTML Sanitization
- HTML is automatically cleaned for security
- Use allowed tags only (see `HTML_SANITIZER_ALLOWED_TAGS` in settings)
- Test with various HTML inputs

### Performance
- Large numbers of blocks (50+) may impact validation performance
- Consider pagination for content with many blocks
- Use caching for frequently accessed content

## Related Documentation

- [Block Validation](validation.md)
- [Custom Blocks](custom-blocks.md)
- [Content Registry](registry.md)
- [Security](security.md)