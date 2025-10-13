import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertCircle,
  CheckCircle2,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Sparkles,
  Copy,
  ExternalLink
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { SchemaObject, SchemaType, SchemaValidation } from '@/types/schema';
import { ArticleSchemaForm } from './schema-forms/ArticleSchemaForm';
import { WebPageSchemaForm } from './schema-forms/WebPageSchemaForm';

interface SchemaBuilderProps {
  schemas: SchemaObject[];
  pageData?: any;
  onChange: (schemas: SchemaObject[]) => void;
  autoGenerate?: boolean;
  pageId?: number;
}

export function SchemaBuilder({
  schemas = [],
  pageData,
  onChange,
  autoGenerate = false,
  pageId
}: SchemaBuilderProps) {
  const [localSchemas, setLocalSchemas] = useState<SchemaObject[]>(schemas);
  const [selectedSchema, setSelectedSchema] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'form' | 'json'>('form');
  const [autoGen, setAutoGen] = useState(autoGenerate);
  const [validation, setValidation] = useState<Record<string, SchemaValidation>>({});

  // Sync with parent
  useEffect(() => {
    setLocalSchemas(schemas);
  }, [schemas]);

  // Auto-generate on mount if enabled
  useEffect(() => {
    if (autoGen && localSchemas.length === 0 && pageId) {
      handleAutoGenerate();
    }
  }, [autoGen, pageId]);

  const handleAutoGenerate = async () => {
    if (!pageId) return;

    try {
      const response = await fetch(`/api/v1/cms/pages/${pageId}/schema/`);
      if (response.ok) {
        const data = await response.json();
        const newSchemas = data.schemas.map((schema: any, index: number) => ({
          id: `schema-${Date.now()}-${index}`,
          type: schema['@type'] as SchemaType,
          auto_generated: true,
          data: schema
        }));
        setLocalSchemas(newSchemas);
        onChange(newSchemas);
      }
    } catch (error) {
      console.error('Failed to auto-generate schema:', error);
    }
  };

  const handleAddSchema = () => {
    const newSchema: SchemaObject = {
      id: `schema-${Date.now()}`,
      type: 'WebPage',
      auto_generated: false,
      data: {
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        name: pageData?.title || '',
        description: pageData?.seo?.description || '',
        url: pageData?.path || ''
      }
    };

    const updated = [...localSchemas, newSchema];
    setLocalSchemas(updated);
    onChange(updated);
    setSelectedSchema(newSchema.id);
  };

  const handleRemoveSchema = (id: string) => {
    const updated = localSchemas.filter(s => s.id !== id);
    setLocalSchemas(updated);
    onChange(updated);
    if (selectedSchema === id) {
      setSelectedSchema(null);
    }
  };

  const handleUpdateSchema = (id: string, data: Partial<SchemaObject>) => {
    const updated = localSchemas.map(s =>
      s.id === id ? { ...s, ...data } : s
    );
    setLocalSchemas(updated);
    onChange(updated);
  };

  const handleValidate = async (id: string) => {
    const schema = localSchemas.find(s => s.id === id);
    if (!schema) return;

    try {
      const response = await fetch('/api/v1/cms/schema/validate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schema: schema.data })
      });

      if (response.ok) {
        const result = await response.json();
        setValidation(prev => ({
          ...prev,
          [id]: {
            valid: result.valid,
            errors: result.errors || [],
            warnings: result.warnings || []
          }
        }));
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleCopyJSON = (schema: SchemaObject) => {
    navigator.clipboard.writeText(JSON.stringify(schema.data, null, 2));
  };

  const selectedSchemaObject = localSchemas.find(s => s.id === selectedSchema);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Structured Data (Schema.org)</h3>
          <p className="text-sm text-muted-foreground">
            Add JSON-LD structured data to improve SEO and search appearance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="auto-generate" className="text-sm">Auto-generate</Label>
            <Switch
              id="auto-generate"
              checked={autoGen}
              onCheckedChange={setAutoGen}
            />
          </div>
          {autoGen && (
            <Button
              onClick={handleAutoGenerate}
              size="sm"
              variant="outline"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Regenerate
            </Button>
          )}
        </div>
      </div>

      {/* Schema List */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Schemas ({localSchemas.length})</Label>
            <Button onClick={handleAddSchema} size="sm" variant="outline">
              <Plus className="w-4 h-4 mr-2" />
              Add
            </Button>
          </div>

          <div className="space-y-2">
            {localSchemas.map((schema) => (
              <Card
                key={schema.id}
                className={`cursor-pointer transition-colors ${
                  selectedSchema === schema.id
                    ? 'border-primary bg-accent'
                    : 'hover:border-primary/50'
                }`}
                onClick={() => setSelectedSchema(schema.id)}
              >
                <CardHeader className="p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-sm">{schema.type}</CardTitle>
                      {schema.auto_generated && (
                        <Badge variant="secondary" className="text-xs mt-1">
                          Auto-generated
                        </Badge>
                      )}
                    </div>
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveSchema(schema.id);
                      }}
                      size="sm"
                      variant="ghost"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                  {validation[schema.id] && (
                    <div className="mt-2">
                      {validation[schema.id].valid ? (
                        <div className="flex items-center gap-1 text-green-600 text-xs">
                          <CheckCircle2 className="w-3 h-3" />
                          Valid
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-red-600 text-xs">
                          <AlertCircle className="w-3 h-3" />
                          {validation[schema.id].errors.length} errors
                        </div>
                      )}
                    </div>
                  )}
                </CardHeader>
              </Card>
            ))}
          </div>

          {localSchemas.length === 0 && (
            <Alert>
              <AlertDescription className="text-sm">
                No schemas yet. Click "Add" to create one or enable auto-generate.
              </AlertDescription>
            </Alert>
          )}
        </div>

        {/* Schema Editor */}
        <div className="md:col-span-2">
          {selectedSchemaObject ? (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{selectedSchemaObject.type} Schema</CardTitle>
                    <CardDescription>
                      Edit schema properties or switch to JSON mode
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => handleValidate(selectedSchemaObject.id)}
                      size="sm"
                      variant="outline"
                    >
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Validate
                    </Button>
                    <Button
                      onClick={() => handleCopyJSON(selectedSchemaObject)}
                      size="sm"
                      variant="outline"
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                    <Button
                      onClick={() => setViewMode(viewMode === 'form' ? 'json' : 'form')}
                      size="sm"
                      variant="outline"
                    >
                      {viewMode === 'form' ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {viewMode === 'form' ? (
                  <div>
                    {selectedSchemaObject.type === 'Article' || selectedSchemaObject.type === 'BlogPosting' ? (
                      <ArticleSchemaForm
                        schema={selectedSchemaObject.data}
                        onChange={(data) => handleUpdateSchema(selectedSchemaObject.id, { data })}
                        pageData={pageData}
                      />
                    ) : selectedSchemaObject.type === 'WebPage' ? (
                      <WebPageSchemaForm
                        schema={selectedSchemaObject.data}
                        onChange={(data) => handleUpdateSchema(selectedSchemaObject.id, { data })}
                        pageData={pageData}
                      />
                    ) : (
                      <div className="space-y-4">
                        <Alert>
                          <AlertDescription>
                            Form editor not yet available for {selectedSchemaObject.type}.
                            Please use JSON mode.
                          </AlertDescription>
                        </Alert>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <Textarea
                      value={JSON.stringify(selectedSchemaObject.data, null, 2)}
                      onChange={(e) => {
                        try {
                          const data = JSON.parse(e.target.value);
                          handleUpdateSchema(selectedSchemaObject.id, { data });
                        } catch (err) {
                          // Invalid JSON, don't update
                        }
                      }}
                      className="font-mono text-sm min-h-[400px]"
                    />
                  </div>
                )}

                {/* Validation Results */}
                {validation[selectedSchemaObject.id] && (
                  <div className="mt-4 space-y-2">
                    {validation[selectedSchemaObject.id].errors.length > 0 && (
                      <Alert variant="destructive">
                        <AlertCircle className="w-4 h-4" />
                        <AlertDescription>
                          <div className="font-semibold">Errors:</div>
                          <ul className="list-disc list-inside text-sm mt-1">
                            {validation[selectedSchemaObject.id].errors.map((error, i) => (
                              <li key={i}>{error}</li>
                            ))}
                          </ul>
                        </AlertDescription>
                      </Alert>
                    )}
                    {validation[selectedSchemaObject.id].warnings.length > 0 && (
                      <Alert>
                        <AlertDescription>
                          <div className="font-semibold">Warnings:</div>
                          <ul className="list-disc list-inside text-sm mt-1">
                            {validation[selectedSchemaObject.id].warnings.map((warning, i) => (
                              <li key={i}>{warning}</li>
                            ))}
                          </ul>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex items-center justify-center min-h-[400px] text-muted-foreground">
                Select a schema from the list to edit
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Help Links */}
      <div className="flex gap-4 text-sm text-muted-foreground">
        <a
          href="https://schema.org"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 hover:text-primary"
        >
          Schema.org Documentation
          <ExternalLink className="w-3 h-3" />
        </a>
        <a
          href="https://search.google.com/test/rich-results"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 hover:text-primary"
        >
          Google Rich Results Test
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}
