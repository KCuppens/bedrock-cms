import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { WebPageSchema } from '@/types/schema';

interface WebPageSchemaFormProps {
  schema: Partial<WebPageSchema>;
  onChange: (schema: Partial<WebPageSchema>) => void;
  pageData?: any;
}

export function WebPageSchemaForm({ schema, onChange, pageData }: WebPageSchemaFormProps) {
  const handleChange = (field: string, value: any) => {
    onChange({ ...schema, [field]: value });
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">
          Page Name <span className="text-red-500">*</span>
        </Label>
        <Input
          id="name"
          value={schema.name || ''}
          onChange={(e) => handleChange('name', e.target.value)}
          placeholder={pageData?.title || 'Enter page name'}
        />
        <p className="text-xs text-muted-foreground">
          The name of the web page
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
          A short description of the page
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="url">Page URL</Label>
        <Input
          id="url"
          value={schema.url || ''}
          onChange={(e) => handleChange('url', e.target.value)}
          placeholder={pageData?.path || 'https://example.com/page'}
        />
        <p className="text-xs text-muted-foreground">
          The full URL of the page
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
          URL to the page's main image
        </p>
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
