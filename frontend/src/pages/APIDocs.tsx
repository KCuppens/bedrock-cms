import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Copy, 
  Download, 
  Key, 
  Play, 
  Search,
  Lock,
  Unlock,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  ChevronRight,
  Code
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import TopNavbar from '@/components/TopNavbar';
import Sidebar from '@/components/Sidebar';

interface OpenAPISchema {
  openapi: string;
  info: {
    title: string;
    version: string;
    description?: string;
  };
  servers?: Array<{
    url: string;
    description?: string;
  }>;
  paths: Record<string, Record<string, any>>;
  components?: {
    schemas?: Record<string, any>;
    securitySchemes?: Record<string, any>;
  };
  tags?: Array<{
    name: string;
    description?: string;
  }>;
}

interface ParsedEndpoint {
  id: string;
  method: string;
  path: string;
  summary: string;
  description: string;
  tags: string[];
  parameters: Array<{
    name: string;
    in: 'query' | 'path' | 'header';
    required: boolean;
    type: string;
    description?: string;
    example?: any;
  }>;
  requestBody?: {
    required: boolean;
    contentType: string;
    example?: any;
  };
  responses: Array<{
    status: string;
    description: string;
    example?: any;
  }>;
  security: boolean;
}

const APIDocs = () => {
  const { toast } = useToast();
  
  // State
  const [schema, setSchema] = useState<OpenAPISchema | null>(null);
  const [endpoints, setEndpoints] = useState<ParsedEndpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // UI State
  const [activeTag, setActiveTag] = useState<string>('all');
  const [selectedEndpoint, setSelectedEndpoint] = useState<ParsedEndpoint | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [authToken, setAuthToken] = useState('');
  const [testParams, setTestParams] = useState<Record<string, any>>({});
  const [testResponse, setTestResponse] = useState<any>(null);
  const [isTestLoading, setIsTestLoading] = useState(false);

  // Fetch OpenAPI schema
  useEffect(() => {
    const fetchSchema = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch('http://localhost:8000/api/schema/', {
          headers: {
            'Accept': 'application/json',
          },
          credentials: 'include'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const schemaData: OpenAPISchema = await response.json();
        console.log('Fetched schema:', schemaData);
        
        setSchema(schemaData);
        
        // Parse endpoints from schema
        const parsedEndpoints = parseEndpointsFromSchema(schemaData);
        console.log('Parsed endpoints:', parsedEndpoints);
        
        setEndpoints(parsedEndpoints);
        
      } catch (err: any) {
        console.error('Failed to fetch API schema:', err);
        setError(err.message || 'Failed to load API documentation');
        toast({
          title: 'Error',
          description: 'Failed to load API documentation. Please try again.',
          variant: 'destructive'
        });
      } finally {
        setLoading(false);
      }
    };

    fetchSchema();
  }, [toast]);

  // Parse endpoints from OpenAPI schema
  const parseEndpointsFromSchema = (schema: OpenAPISchema): ParsedEndpoint[] => {
    const parsedEndpoints: ParsedEndpoint[] = [];
    
    Object.entries(schema.paths).forEach(([path, methods]) => {
      Object.entries(methods).forEach(([method, spec]: [string, any]) => {
        if (method === 'parameters' || typeof spec !== 'object') return;
        
        const endpoint: ParsedEndpoint = {
          id: `${method}-${path}`.replace(/[{}]/g, '-').replace(/\//g, '-'),
          method: method.toUpperCase(),
          path,
          summary: spec.summary || `${method.toUpperCase()} ${path}`,
          description: spec.description || '',
          tags: spec.tags || ['General'],
          parameters: (spec.parameters || []).map((param: any) => ({
            name: param.name,
            in: param.in,
            required: param.required || false,
            type: param.schema?.type || 'string',
            description: param.description || '',
            example: param.example || param.schema?.example
          })),
          requestBody: spec.requestBody ? {
            required: spec.requestBody.required || false,
            contentType: Object.keys(spec.requestBody.content || {})[0] || 'application/json',
            example: getRequestBodyExample(spec.requestBody)
          } : undefined,
          responses: Object.entries(spec.responses || {}).map(([status, resp]: [string, any]) => ({
            status,
            description: resp.description || '',
            example: getResponseExample(resp)
          })),
          security: !!(spec.security && spec.security.length > 0)
        };
        
        parsedEndpoints.push(endpoint);
      });
    });
    
    return parsedEndpoints;
  };

  // Helper to get request body example
  const getRequestBodyExample = (requestBody: any) => {
    if (!requestBody?.content) return null;
    
    const contentTypes = Object.keys(requestBody.content);
    const firstContentType = contentTypes[0];
    const content = requestBody.content[firstContentType];
    
    if (content?.example) return content.example;
    if (content?.examples) {
      const firstExample = Object.values(content.examples)[0] as any;
      return firstExample?.value || firstExample;
    }
    
    return null;
  };

  // Helper to get response example
  const getResponseExample = (response: any) => {
    if (!response?.content) return null;
    
    const contentTypes = Object.keys(response.content);
    const firstContentType = contentTypes[0];
    const content = response.content[firstContentType];
    
    if (content?.example) return content.example;
    if (content?.examples) {
      const firstExample = Object.values(content.examples)[0] as any;
      return firstExample?.value || firstExample;
    }
    
    return null;
  };

  // Get available tags
  const availableTags = useMemo(() => {
    const tagCounts: Record<string, number> = {};
    
    endpoints.forEach(endpoint => {
      endpoint.tags.forEach(tag => {
        tagCounts[tag] = (tagCounts[tag] || 0) + 1;
      });
    });

    const tags = Object.entries(tagCounts).map(([name, count]) => ({
      name,
      description: schema?.tags?.find(t => t.name === name)?.description || '',
      count
    }));

    // Add "all" tag
    return [
      { name: 'all', description: 'All endpoints', count: endpoints.length },
      ...tags
    ];
  }, [endpoints, schema]);

  // Filter endpoints
  const filteredEndpoints = useMemo(() => {
    let filtered = endpoints;
    
    // Filter by active tag
    if (activeTag && activeTag !== 'all') {
      filtered = filtered.filter(ep => ep.tags.includes(activeTag));
    }
    
    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(ep => 
        ep.path.toLowerCase().includes(query) ||
        ep.summary.toLowerCase().includes(query) ||
        ep.description.toLowerCase().includes(query) ||
        ep.method.toLowerCase().includes(query)
      );
    }
    
    return filtered.sort((a, b) => a.path.localeCompare(b.path));
  }, [endpoints, activeTag, searchQuery]);

  // Method color coding
  const getMethodColor = (method: string) => {
    const colors = {
      GET: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
      POST: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
      PUT: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
      PATCH: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400',
      DELETE: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
    };
    return colors[method as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  // Copy to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied to clipboard',
      description: 'The content has been copied to your clipboard.',
    });
  };

  // Generate cURL command
  const generateCurl = (endpoint: ParsedEndpoint) => {
    let curl = `curl -X ${endpoint.method} '${window.location.origin}${endpoint.path}'`;
    
    // Add headers
    const headers = ['-H "Accept: application/json"'];
    
    if (authToken) {
      headers.push(`-H "Authorization: Bearer ${authToken}"`);
    }
    
    if (endpoint.requestBody) {
      headers.push('-H "Content-Type: application/json"');
    }
    
    if (headers.length > 0) {
      curl += ' \\\n  ' + headers.join(' \\\n  ');
    }
    
    // Add request body for non-GET methods
    if (endpoint.requestBody && endpoint.method !== 'GET' && endpoint.requestBody.example) {
      curl += ` \\\n  -d '${JSON.stringify(endpoint.requestBody.example, null, 2)}'`;
    }
    
    return curl;
  };

  // Test endpoint
  const tryEndpoint = async (endpoint: ParsedEndpoint) => {
    let url = `${window.location.origin}${endpoint.path}`;
    
    // Replace path parameters
    endpoint.parameters
      .filter(param => param.in === 'path' && testParams[param.name])
      .forEach(param => {
        url = url.replace(`{${param.name}}`, testParams[param.name]);
      });

    // Add query parameters
    const queryParams = new URLSearchParams();
    endpoint.parameters
      .filter(param => param.in === 'query' && testParams[param.name])
      .forEach(param => {
        queryParams.set(param.name, testParams[param.name]);
      });
    
    if (queryParams.toString()) {
      url += `?${queryParams.toString()}`;
    }

    const options: RequestInit = {
      method: endpoint.method,
      headers: {
        'Accept': 'application/json',
      } as any,
      credentials: 'include'
    };

    if (authToken) {
      options.headers!['Authorization'] = `Bearer ${authToken}`;
    }

    if (endpoint.requestBody && endpoint.method !== 'GET') {
      options.headers!['Content-Type'] = 'application/json';
      const bodyData = testParams.requestBody || endpoint.requestBody.example;
      if (bodyData) {
        options.body = JSON.stringify(bodyData);
      }
    }

    setIsTestLoading(true);
    setTestResponse(null);

    try {
      const response = await fetch(url, options);
      const contentType = response.headers.get('content-type');
      
      let data;
      if (contentType?.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      setTestResponse({
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries()),
        data: data
      });

      toast({
        title: response.ok ? 'Request Successful' : 'Request Failed',
        description: `${endpoint.method} ${endpoint.path} returned ${response.status}`,
        variant: response.ok ? 'default' : 'destructive'
      });
    } catch (error: any) {
      setTestResponse({
        error: error.message,
        status: 0,
        statusText: 'Network Error'
      });
      
      toast({
        title: 'Request Failed',
        description: error.message || 'Failed to send API request',
        variant: 'destructive'
      });
    } finally {
      setIsTestLoading(false);
    }
  };

  // Download schema
  const downloadSchema = async (format: 'json' | 'yaml') => {
    try {
      const url = format === 'json' ? '/api/schema/' : '/api/schema.yaml';
      const response = await fetch(url, { credentials: 'include' });
      
      if (!response.ok) throw new Error('Failed to download schema');
      
      const content = await response.text();
      const blob = new Blob([content], { 
        type: format === 'json' ? 'application/json' : 'text/yaml' 
      });
      
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `openapi-schema.${format}`;
      link.click();
      
      toast({
        title: 'Schema Downloaded',
        description: `OpenAPI schema downloaded as ${format.toUpperCase()}`,
      });
    } catch (error: any) {
      toast({
        title: 'Download Failed',
        description: error.message || 'Failed to download schema',
        variant: 'destructive'
      });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="flex">
          <Sidebar />
          <div className="flex-1 flex flex-col ml-72">
            <TopNavbar />
            <main className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-4">
                <Loader2 className="w-8 h-8 animate-spin mx-auto" />
                <div>
                  <h2 className="text-lg font-semibold">Loading API Documentation</h2>
                  <p className="text-muted-foreground">Fetching OpenAPI schema...</p>
                </div>
              </div>
            </main>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen">
        <div className="flex">
          <Sidebar />
          <div className="flex-1 flex flex-col ml-72">
            <TopNavbar />
            <main className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-4 max-w-md">
                <XCircle className="w-12 h-12 text-destructive mx-auto" />
                <div>
                  <h2 className="text-lg font-semibold">Failed to Load API Documentation</h2>
                  <p className="text-muted-foreground mt-2">{error}</p>
                </div>
                <Button onClick={() => window.location.reload()}>
                  Try Again
                </Button>
              </div>
            </main>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />
        
        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />
          
          <main className="flex-1 p-8">
            <div className="max-w-7xl mx-auto">
              {/* Header */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h1 className="text-3xl font-bold text-foreground">
                      {schema?.info?.title || 'API Documentation'}
                    </h1>
                    <p className="text-muted-foreground">
                      {schema?.info?.description || 'Interactive API documentation'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-lg px-3 py-1">
                      {schema?.info?.version || 'v1.0'}
                    </Badge>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => downloadSchema('json')}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      JSON Schema
                    </Button>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">
                  {endpoints.length} endpoints across {availableTags.length - 1} categories
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Sidebar Navigation */}
                <div className="lg:col-span-1 space-y-4">
                  {/* Search */}
                  <Card>
                    <CardContent className="p-3">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          placeholder="Search endpoints..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="pl-9 text-sm"
                        />
                      </div>
                    </CardContent>
                  </Card>

                  {/* API Categories */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium">API Categories</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <ScrollArea className="h-[300px]">
                        <div className="p-3 space-y-1">
                          {availableTags.map((tag) => {
                            const isActive = activeTag === tag.name;
                            
                            return (
                              <Button
                                key={tag.name}
                                variant={isActive ? 'default' : 'ghost'}
                                className="w-full justify-between text-sm h-auto py-2 px-3"
                                onClick={() => {
                                  setActiveTag(tag.name);
                                  setSelectedEndpoint(null);
                                }}
                              >
                                <span>{tag.name === 'all' ? 'All Endpoints' : tag.name}</span>
                                <Badge variant={isActive ? 'secondary' : 'outline'} className="text-xs">
                                  {tag.count}
                                </Badge>
                              </Button>
                            );
                          })}
                        </div>
                      </ScrollArea>
                    </CardContent>
                  </Card>

                  {/* Authentication */}
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Key className="w-4 h-4" />
                        Authentication
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-3 space-y-3">
                      <div>
                        <Label className="text-xs">Bearer Token</Label>
                        <Input
                          type="password"
                          placeholder="Enter your API token"
                          value={authToken}
                          onChange={(e) => setAuthToken(e.target.value)}
                          className="text-xs mt-1"
                        />
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Token will be used for authenticated API requests
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Main Content */}
                <div className="lg:col-span-3">
                  {!selectedEndpoint ? (
                    <div className="space-y-4">
                      {/* Category Overview */}
                      <Card>
                        <CardHeader>
                          <CardTitle>
                            {activeTag === 'all' ? 'All Endpoints' : `${activeTag} Endpoints`}
                          </CardTitle>
                          <div className="text-sm text-muted-foreground">
                            {availableTags.find(t => t.name === activeTag)?.description}
                          </div>
                        </CardHeader>
                      </Card>

                      {/* Endpoints List */}
                      <Card>
                        <CardContent className="p-0">
                          {filteredEndpoints.length === 0 ? (
                            <div className="p-8 text-center text-muted-foreground">
                              <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
                              <p>No endpoints found</p>
                              <p className="text-sm mt-1">Try adjusting your search or category</p>
                            </div>
                          ) : (
                            <div className="divide-y">
                              {filteredEndpoints.map((endpoint) => (
                                <div
                                  key={endpoint.id}
                                  className="p-4 hover:bg-muted/50 cursor-pointer transition-colors"
                                  onClick={() => setSelectedEndpoint(endpoint)}
                                >
                                  <div className="flex items-center gap-3 mb-2">
                                    <Badge className={getMethodColor(endpoint.method)}>
                                      {endpoint.method}
                                    </Badge>
                                    <code className="text-sm font-mono flex-1">{endpoint.path}</code>
                                    {endpoint.security ? (
                                      <Lock className="w-3 h-3 text-yellow-600" title="Authentication required" />
                                    ) : (
                                      <Unlock className="w-3 h-3 text-green-600" title="No authentication required" />
                                    )}
                                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                                  </div>
                                  <p className="text-sm font-medium">{endpoint.summary}</p>
                                  {endpoint.description && (
                                    <p className="text-sm text-muted-foreground mt-1">{endpoint.description}</p>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    </div>
                  ) : (
                    // Endpoint Details
                    <div className="space-y-6">
                      {/* Header */}
                      <div className="flex items-center gap-4">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => setSelectedEndpoint(null)}
                        >
                          ← Back to {activeTag === 'all' ? 'All Endpoints' : activeTag}
                        </Button>
                      </div>

                      {/* Endpoint Info */}
                      <Card>
                        <CardHeader>
                          <div className="space-y-3">
                            <div className="flex items-center gap-3">
                              <Badge className={`${getMethodColor(selectedEndpoint.method)} text-base px-3 py-1`}>
                                {selectedEndpoint.method}
                              </Badge>
                              <code className="text-lg font-mono flex-1">{selectedEndpoint.path}</code>
                              {selectedEndpoint.security ? (
                                <Lock className="w-4 h-4 text-yellow-600" title="Authentication required" />
                              ) : (
                                <Unlock className="w-4 h-4 text-green-600" title="No authentication required" />
                              )}
                            </div>
                            <div>
                              <h2 className="text-xl font-semibold">{selectedEndpoint.summary}</h2>
                              {selectedEndpoint.description && (
                                <p className="text-muted-foreground mt-1">{selectedEndpoint.description}</p>
                              )}
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <Tabs defaultValue="parameters" className="w-full">
                            <TabsList className="grid w-full grid-cols-4">
                              <TabsTrigger value="parameters">Parameters</TabsTrigger>
                              <TabsTrigger value="responses">Responses</TabsTrigger>
                              <TabsTrigger value="code">Code</TabsTrigger>
                              <TabsTrigger value="try">Try It</TabsTrigger>
                            </TabsList>
                            
                            <TabsContent value="parameters" className="mt-4">
                              <div className="space-y-4">
                                {selectedEndpoint.parameters.length > 0 && (
                                  <div>
                                    <h3 className="font-medium text-sm mb-3">Parameters</h3>
                                    <div className="space-y-3">
                                      {selectedEndpoint.parameters.map((param, index) => (
                                        <div key={index} className="border rounded-lg p-3 space-y-2">
                                          <div className="flex items-center gap-2">
                                            <code className="text-sm font-mono font-semibold">{param.name}</code>
                                            <Badge variant="outline" className="text-xs">
                                              {param.in}
                                            </Badge>
                                            <Badge variant="outline" className="text-xs">
                                              {param.type}
                                            </Badge>
                                            {param.required && (
                                              <Badge variant="destructive" className="text-xs">
                                                required
                                              </Badge>
                                            )}
                                          </div>
                                          {param.description && (
                                            <p className="text-sm text-muted-foreground">{param.description}</p>
                                          )}
                                          {param.example !== undefined && (
                                            <div className="flex items-center gap-2">
                                              <span className="text-xs text-muted-foreground">Example:</span>
                                              <code className="text-xs bg-muted px-2 py-1 rounded">
                                                {JSON.stringify(param.example)}
                                              </code>
                                            </div>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {selectedEndpoint.requestBody && (
                                  <div>
                                    <h3 className="font-medium text-sm mb-3">Request Body</h3>
                                    <div className="border rounded-lg p-3 space-y-2">
                                      <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="text-xs">
                                          {selectedEndpoint.requestBody.contentType}
                                        </Badge>
                                        {selectedEndpoint.requestBody.required && (
                                          <Badge variant="destructive" className="text-xs">
                                            required
                                          </Badge>
                                        )}
                                      </div>
                                      {selectedEndpoint.requestBody.example && (
                                        <pre className="text-xs bg-muted p-2 rounded overflow-auto">
                                          {JSON.stringify(selectedEndpoint.requestBody.example, null, 2)}
                                        </pre>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {selectedEndpoint.parameters.length === 0 && !selectedEndpoint.requestBody && (
                                  <p className="text-muted-foreground">No parameters required for this endpoint.</p>
                                )}
                              </div>
                            </TabsContent>

                            <TabsContent value="responses" className="mt-4">
                              <div className="space-y-4">
                                <h3 className="font-medium text-sm">Response Codes</h3>
                                {selectedEndpoint.responses.map((response, index) => (
                                  <div key={index} className="border rounded-lg p-4 space-y-3">
                                    <div className="flex items-center gap-2">
                                      {parseInt(response.status) < 300 ? (
                                        <CheckCircle className="w-4 h-4 text-green-600" />
                                      ) : parseInt(response.status) < 400 ? (
                                        <AlertCircle className="w-4 h-4 text-yellow-600" />
                                      ) : (
                                        <XCircle className="w-4 h-4 text-red-600" />
                                      )}
                                      <Badge 
                                        variant={parseInt(response.status) < 400 ? "default" : "destructive"}
                                        className="font-mono"
                                      >
                                        {response.status}
                                      </Badge>
                                      <span className="font-medium">{response.description}</span>
                                    </div>
                                    {response.example && (
                                      <pre className="bg-muted p-3 rounded-lg text-sm overflow-auto">
                                        {typeof response.example === 'string' 
                                          ? response.example 
                                          : JSON.stringify(response.example, null, 2)}
                                      </pre>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </TabsContent>

                            <TabsContent value="code" className="mt-4 space-y-4">
                              <div>
                                <div className="flex items-center justify-between mb-2">
                                  <h3 className="font-medium text-sm">cURL</h3>
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    onClick={() => copyToClipboard(generateCurl(selectedEndpoint))}
                                  >
                                    <Copy className="w-3 h-3 mr-2" />
                                    Copy
                                  </Button>
                                </div>
                                <pre className="bg-muted p-4 rounded-lg text-sm overflow-auto">
                                  {generateCurl(selectedEndpoint)}
                                </pre>
                              </div>
                            </TabsContent>

                            <TabsContent value="try" className="mt-4">
                              <div className="space-y-4">
                                <h3 className="font-medium text-sm">Test Endpoint</h3>
                                
                                {/* Parameters Input */}
                                {selectedEndpoint.parameters.length > 0 && (
                                  <div className="space-y-3">
                                    <h4 className="text-sm font-medium">Parameters</h4>
                                    {selectedEndpoint.parameters.map((param, index) => (
                                      <div key={index}>
                                        <Label className="text-sm">
                                          {param.name}
                                          {param.required && <span className="text-red-500 ml-1">*</span>}
                                        </Label>
                                        <Input
                                          placeholder={param.example?.toString() || param.description || `Enter ${param.name}`}
                                          value={testParams[param.name] || ''}
                                          onChange={(e) => setTestParams(prev => ({
                                            ...prev,
                                            [param.name]: e.target.value
                                          }))}
                                          className="mt-1"
                                        />
                                        {param.description && (
                                          <p className="text-xs text-muted-foreground mt-1">{param.description}</p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Request Body Input */}
                                {selectedEndpoint.requestBody && (
                                  <div>
                                    <Label className="text-sm">
                                      Request Body (JSON)
                                      {selectedEndpoint.requestBody.required && <span className="text-red-500 ml-1">*</span>}
                                    </Label>
                                    <Textarea
                                      placeholder={JSON.stringify(selectedEndpoint.requestBody.example || {}, null, 2)}
                                      rows={8}
                                      className="font-mono text-sm mt-1"
                                      onChange={(e) => {
                                        try {
                                          const body = JSON.parse(e.target.value);
                                          setTestParams(prev => ({ ...prev, requestBody: body }));
                                        } catch (err) {
                                          // Invalid JSON, ignore
                                        }
                                      }}
                                    />
                                  </div>
                                )}

                                {/* Action Buttons */}
                                <div className="flex gap-3">
                                  <Button 
                                    onClick={() => tryEndpoint(selectedEndpoint)}
                                    disabled={isTestLoading}
                                  >
                                    {isTestLoading ? (
                                      <>
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                        Sending...
                                      </>
                                    ) : (
                                      <>
                                        <Play className="w-4 h-4 mr-2" />
                                        Send Request
                                      </>
                                    )}
                                  </Button>
                                  <Button 
                                    variant="outline"
                                    onClick={() => {
                                      setTestParams({});
                                      setTestResponse(null);
                                    }}
                                  >
                                    Clear
                                  </Button>
                                </div>

                                {/* Response Display */}
                                {testResponse && (
                                  <div className="space-y-3">
                                    <Separator />
                                    <h4 className="text-sm font-medium">Response</h4>
                                    
                                    <div className="flex items-center gap-2">
                                      <Badge 
                                        variant={testResponse.status < 400 ? "default" : "destructive"}
                                      >
                                        {testResponse.status} {testResponse.statusText}
                                      </Badge>
                                      {testResponse.headers?.['content-type'] && (
                                        <Badge variant="outline">
                                          {testResponse.headers['content-type']}
                                        </Badge>
                                      )}
                                    </div>
                                    
                                    {testResponse.error ? (
                                      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                                        <p className="text-sm text-red-800 dark:text-red-200">{testResponse.error}</p>
                                      </div>
                                    ) : (
                                      <pre className="bg-muted p-4 rounded-lg text-sm overflow-auto max-h-96">
                                        {typeof testResponse.data === 'string' 
                                          ? testResponse.data 
                                          : JSON.stringify(testResponse.data, null, 2)}
                                      </pre>
                                    )}
                                  </div>
                                )}
                              </div>
                            </TabsContent>
                          </Tabs>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default APIDocs;