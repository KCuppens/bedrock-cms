# 📋 Implementation Plan: Automatic Blurred Placeholders on File Upload

## Overview
Automatically generate and store blurred placeholders for every image uploaded to the CMS, then serve them for progressive loading.

## Architecture Design

```
User uploads image → Django receives file → Generate placeholders → Store in DB → Serve via API
                           ↓                      ↓
                     [Original File]      [Base64 Blur, BlurHash, Color]
                           ↓                      ↓
                        S3/MinIO              PostgreSQL
```

## Phase 1: Database Schema Changes

### 1.1 Update FileUpload Model
```python
class FileUpload(models.Model):
    # Existing fields...

    # New placeholder fields
    placeholder_base64 = TextField(null=True)      # ~500-800 bytes
    placeholder_blurhash = CharField(max_length=50) # ~30 bytes
    placeholder_color = CharField(max_length=7)     # 7 bytes (#RRGGBB)
    image_width = IntegerField(null=True)
    image_height = IntegerField(null=True)

    # Performance tracking
    placeholder_generated_at = DateTimeField(null=True)
    placeholder_generation_time_ms = IntegerField(null=True)
```

### 1.2 Migration Strategy
- Add fields as nullable first
- Backfill existing images in batches
- Make required after backfill complete

## Phase 2: Image Processing Pipeline

### 2.1 Processing Flow
```
1. File Upload Received
2. Validate it's an image
3. Generate placeholders:
   - Base64 (20x20px, blurred)
   - BlurHash string
   - Dominant color
4. Store metadata (width, height)
5. Save to database
6. Upload original to S3/MinIO
```

### 2.2 Processing Options

**Option A: Synchronous (Simple)**
- Process during request
- Pros: Immediate, simple
- Cons: Slower upload (adds ~200ms)

**Option B: Async with Celery (Recommended)**
- Queue for processing
- Pros: Fast upload, scalable
- Cons: Requires Celery setup

**Option C: Hybrid**
- Generate base64 sync (fast)
- Queue BlurHash/responsive versions
- Pros: Best of both
- Cons: More complex

## Phase 3: Implementation Details

### 3.1 Signal Handler Structure
```python
@receiver(pre_save, sender=FileUpload)
def generate_placeholders(sender, instance, **kwargs):
    # Only for new images
    if instance.pk or not is_image(instance):
        return

    # Generate placeholders
    # Store in instance fields
    # They'll be saved with the model
```

### 3.2 Image Processing Service
```python
class ImagePlaceholderService:
    def process_image(self, file):
        # Open with Pillow
        # Generate base64 thumbnail
        # Generate BlurHash
        # Extract dominant color
        # Return all placeholders

    def generate_base64_blur(self, image, size=(20, 20)):
        # Resize to 20x20
        # Apply Gaussian blur
        # Convert to JPEG (low quality)
        # Encode as base64
        # Return data URI
```

### 3.3 Performance Considerations
- Cache PIL Image object during processing
- Use threading for parallel generation
- Limit placeholder size to 1KB max
- Consider WebP for placeholders (30% smaller)

## Phase 4: API Response Structure

### 4.1 Updated Serializer
```python
class FileUploadSerializer(serializers.ModelSerializer):
    placeholders = serializers.SerializerMethodField()

    def get_placeholders(self, obj):
        return {
            'base64': obj.placeholder_base64,
            'blurhash': obj.placeholder_blurhash,
            'color': obj.placeholder_color,
            'lqip': obj.placeholder_base64,  # Alias for compatibility
        }

    class Meta:
        fields = [..., 'placeholders', 'image_width', 'image_height']
```

### 4.2 API Response Example
```json
{
  "id": "uuid",
  "url": "https://cdn.example.com/image.jpg",
  "placeholders": {
    "base64": "data:image/jpeg;base64,/9j/4AAQ...",
    "blurhash": "LEHV6nWB2yk8pyo0adR*.7kCMdnj",
    "color": "#4A90E2",
    "lqip": "data:image/jpeg;base64,/9j/4AAQ..."
  },
  "image_width": 1920,
  "image_height": 1080
}
```

## Phase 5: Frontend Integration

### 5.1 Update Media Component
```typescript
interface MediaFile {
  url: string;
  placeholders?: {
    base64?: string;
    blurhash?: string;
    color?: string;
  };
  width?: number;
  height?: number;
}
```

### 5.2 Progressive Loading Component
```typescript
<ProgressiveImage
  src={media.url}
  placeholder={media.placeholders?.base64}
  width={media.width}
  height={media.height}
/>
```

## Phase 6: Optimization Strategies

### 6.1 Batch Processing
- Process multiple images in parallel
- Use connection pooling for DB
- Batch insert placeholders

### 6.2 Caching
- Cache processed placeholders in Redis
- Use CDN for placeholder delivery
- Browser cache with long TTL

### 6.3 Fallback Strategy
```
1. Try base64 placeholder
2. Fall back to BlurHash
3. Fall back to dominant color
4. Fall back to skeleton loader
5. Show generic loading state
```

## Phase 7: Migration for Existing Images

### 7.1 Management Command
```bash
python manage.py generate_placeholders --batch-size=100
```

### 7.2 Migration Strategy
1. Count total images
2. Process in batches of 100
3. Skip already processed
4. Log progress
5. Handle failures gracefully

## Phase 8: Monitoring & Testing

### 8.1 Metrics to Track
- Placeholder generation time
- Placeholder file sizes
- Cache hit rates
- API response times
- Frontend render performance

### 8.2 Testing Plan
- Unit tests for processor
- Integration tests for upload
- Performance tests for batch processing
- Frontend visual regression tests

## Implementation Timeline

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Database migration | 2 hours | High |
| 2 | Image processor class | 3 hours | High |
| 3 | Signal handlers | 2 hours | High |
| 4 | API serializer updates | 1 hour | High |
| 5 | Frontend integration | 2 hours | High |
| 6 | Celery async (optional) | 3 hours | Medium |
| 7 | Batch migration | 2 hours | Medium |
| 8 | Testing & monitoring | 2 hours | Medium |

**Total: 17 hours (2-3 days)**

## Risk Mitigation

### Potential Issues & Solutions

1. **Large placeholder sizes**
   - Solution: Reduce quality, smaller dimensions

2. **Slow processing**
   - Solution: Move to async, use Celery

3. **Memory issues with large images**
   - Solution: Stream processing, size limits

4. **Failed generation**
   - Solution: Graceful fallback, retry queue

## Configuration Options

```python
# settings.py
IMAGE_PLACEHOLDER_CONFIG = {
    'ENABLE_PLACEHOLDERS': True,
    'BASE64_SIZE': (20, 20),
    'BASE64_QUALITY': 40,
    'BLURHASH_COMPONENTS': (4, 3),
    'MAX_PLACEHOLDER_SIZE': 1024,  # 1KB
    'USE_CELERY': True,
    'BATCH_SIZE': 100,
}
```

## Success Criteria

- [ ] All new uploads get placeholders
- [ ] Placeholders < 1KB each
- [ ] Generation < 200ms per image
- [ ] Frontend shows blur instantly
- [ ] Smooth transition to full image
- [ ] No increase in error rates
- [ ] LCP improves by 30%+

## Decision Points

1. **Sync vs Async?**
   - Recommend: Hybrid (base64 sync, rest async)

2. **Which placeholder types?**
   - Recommend: All three (base64, blurhash, color)

3. **Backfill old images?**
   - Recommend: Yes, in batches

4. **Storage location?**
   - Recommend: Database (small size, fast access)

This plan ensures smooth, progressive image loading throughout the CMS with minimal performance impact.
