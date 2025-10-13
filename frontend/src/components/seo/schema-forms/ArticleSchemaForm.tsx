import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ArticleSchema } from '@/types/schema';

interface ArticleSchemaFormProps {
  schema: Partial<ArticleSchema>;
  onChange: (schema: Partial<ArticleSchema>) => void;
  pageData?: any;
}

export function ArticleSchemaForm({ schema, onChange, pageData }: ArticleSchemaFormProps) {
  const handleChange = (field: string, value: any) => {
    onChange({ ...schema, [field]: value });
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="headline">
          Headline <span className="text-red-500">*</span>
        </Label>
        <Input
          id="headline"
          value={schema.headline || ''}
          onChange={(e) => handleChange('headline', e.target.value)}
          placeholder={pageData?.title || 'Enter headline'}
        />
        <p className="text-xs text-muted-foreground">
          The headline of the article (max 110 characters)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={schema.description || ''}
          onChange={(e) => handleChange('description', e.target.value)}
          placeholder={pageData?.seo?.description || 'Enter description'}
          rows={3}
        />
        <p className="text-xs text-muted-foreground">
          A short description of the article
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="image">Image URL</Label>
        <Input
          id="image"
          value={typeof schema.image === 'string' ? schema.image : ''}
          onChange={(e) => handleChange('image', e.target.value)}
          placeholder="https://example.com/image.jpg"
        />
        <p className="text-xs text-muted-foreground">
          URL to the main image (recommended: 1200x630px)
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="author-name">Author Name</Label>
          <Input
            id="author-name"
            value={schema.author && typeof schema.author === 'object' ? schema.author.name : ''}
            onChange={(e) =>
              handleChange('author', {
                '@type': 'Person',
                name: e.target.value
              })
            }
            placeholder="John Doe"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="publisher-name">Publisher Name</Label>
          <Input
            id="publisher-name"
            value={schema.publisher && typeof schema.publisher === 'object' ? schema.publisher.name : ''}
            onChange={(e) =>
              handleChange('publisher', {
                '@type': 'Organization',
                name: e.target.value
              })
            }
            placeholder="Your Organization"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="datePublished">Date Published</Label>
          <Input
            id="datePublished"
            type="datetime-local"
            value={schema.datePublished ? schema.datePublished.slice(0, 16) : ''}
            onChange={(e) => handleChange('datePublished', e.target.value + ':00.000Z')}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="dateModified">Date Modified</Label>
          <Input
            id="dateModified"
            type="datetime-local"
            value={schema.dateModified ? schema.dateModified.slice(0, 16) : ''}
            onChange={(e) => handleChange('dateModified', e.target.value + ':00.000Z')}
          />
        </div>
      </div>
    </div>
  );
}
