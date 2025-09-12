import { useState } from 'react';
import { useTranslation } from '@/contexts/TranslationContext';
import { useLocale } from '@/contexts/LocaleContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RefreshCw, Globe, CheckCircle, AlertCircle, Code } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import TopNavbar from '@/components/TopNavbar';
import HeroBlock from '@/components/blocks/HeroBlock';

export default function TestTranslations() {
  const { t, locale, isLoading, missingKeys, registerKey } = useTranslation();
  const { locales, currentLocale, setCurrentLocale } = useLocale();
  const [testKey, setTestKey] = useState('');

  // Test different translation scenarios
  const testCases = [
    { key: 'blocks.hero.loading', expected: 'Loading hero content...' },
    { key: 'blocks.hero.error', expected: 'Failed to load hero block' },
    { key: 'blocks.hero.defaultTitle', expected: 'Welcome' },
    { key: 'blocks.common.edit', expected: 'Edit' },
    { key: 'non.existent.key', expected: 'non.existent.key' },
  ];

  const handleTestTranslation = () => {
    if (testKey) {
      const result = t(testKey, `Default for ${testKey}`);
      alert(`Translation for "${testKey}": ${result}`);
    }
  };

  const handleRegisterKey = () => {
    registerKey({
      key: 'test.dynamic.key',
      defaultValue: 'This is a dynamically registered key',
      description: 'Registered from test page',
      namespace: 'test'
    });
    alert('Key registered! It will be synced in the next batch.');
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <TopNavbar />
        <div className="flex-1 p-6 bg-gray-50">
          <div className="max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div>
              <h1 className="text-3xl font-bold mb-2">Translation System Test</h1>
              <p className="text-gray-600">Test and verify the automatic translation system</p>
            </div>

            {/* Status Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  System Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Current Locale</p>
                    <p className="font-semibold">{locale}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Loading State</p>
                    <Badge variant={isLoading ? "secondary" : "success"}>
                      {isLoading ? 'Loading...' : 'Ready'}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Missing Keys</p>
                    <Badge variant={missingKeys.size > 0 ? "destructive" : "success"}>
                      {missingKeys.size}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Available Locales</p>
                    <p className="font-semibold">{locales.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Locale Switcher */}
            <Card>
              <CardHeader>
                <CardTitle>Locale Switcher</CardTitle>
                <CardDescription>Change the current locale to test translations</CardDescription>
              </CardHeader>
              <CardContent>
                <Select value={currentLocale?.code} onValueChange={(code) => {
                  const locale = locales.find(l => l.code === code);
                  if (locale) setCurrentLocale(locale);
                }}>
                  <SelectTrigger className="w-64">
                    <SelectValue placeholder="Select a locale" />
                  </SelectTrigger>
                  <SelectContent>
                    {locales.map(locale => (
                      <SelectItem key={locale.id} value={locale.code}>
                        {locale.flag} {locale.name} ({locale.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

            {/* Test Cases */}
            <Tabs defaultValue="auto" className="w-full">
              <TabsList>
                <TabsTrigger value="auto">Automatic Tests</TabsTrigger>
                <TabsTrigger value="manual">Manual Test</TabsTrigger>
                <TabsTrigger value="block">Block Preview</TabsTrigger>
                <TabsTrigger value="missing">Missing Keys</TabsTrigger>
              </TabsList>

              <TabsContent value="auto">
                <Card>
                  <CardHeader>
                    <CardTitle>Automatic Translation Tests</CardTitle>
                    <CardDescription>Pre-defined test cases for common translation keys</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {testCases.map(({ key, expected }) => {
                        const actual = t(key);
                        const isCorrect = actual === expected || (!expected && actual === key);

                        return (
                          <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex-1">
                              <code className="text-sm font-mono text-blue-600">{key}</code>
                              <p className="text-sm text-gray-600 mt-1">Result: "{actual}"</p>
                            </div>
                            {isCorrect ? (
                              <CheckCircle className="h-5 w-5 text-green-500" />
                            ) : (
                              <AlertCircle className="h-5 w-5 text-orange-500" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="manual">
                <Card>
                  <CardHeader>
                    <CardTitle>Manual Translation Test</CardTitle>
                    <CardDescription>Test any translation key manually</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        className="flex-1 px-3 py-2 border rounded-md"
                        placeholder="Enter translation key (e.g., blocks.hero.loading)"
                        value={testKey}
                        onChange={(e) => setTestKey(e.target.value)}
                      />
                      <Button onClick={handleTestTranslation}>
                        Test Key
                      </Button>
                    </div>

                    <div className="flex gap-2">
                      <Button onClick={handleRegisterKey} variant="outline">
                        <Code className="h-4 w-4 mr-2" />
                        Register Dynamic Key
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="block">
                <Card>
                  <CardHeader>
                    <CardTitle>Block with Translations</CardTitle>
                    <CardDescription>Preview how blocks use the translation system</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="border rounded-lg overflow-hidden">
                      <HeroBlock
                        type="hero"
                        props={{
                          title: "",
                          subtitle: "",
                          backgroundColor: "bg-blue-600",
                          textColor: "text-white"
                        }}
                        isEditable={true}
                      />
                    </div>
                    <Alert className="mt-4">
                      <AlertDescription>
                        This HeroBlock is in edit mode with no content, so it shows default translated text.
                      </AlertDescription>
                    </Alert>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="missing">
                <Card>
                  <CardHeader>
                    <CardTitle>Missing Translation Keys</CardTitle>
                    <CardDescription>Keys that were requested but not found</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {missingKeys.size === 0 ? (
                      <Alert>
                        <CheckCircle className="h-4 w-4" />
                        <AlertDescription>
                          No missing keys detected. All translations are available.
                        </AlertDescription>
                      </Alert>
                    ) : (
                      <div className="space-y-2">
                        {Array.from(missingKeys).map(key => (
                          <div key={key} className="flex items-center justify-between p-2 bg-orange-50 rounded">
                            <code className="text-sm font-mono text-orange-600">{key}</code>
                            <Badge variant="outline">Missing</Badge>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>

            {/* Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Button onClick={() => window.location.reload()} variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Reload Page
                  </Button>
                  <Button
                    onClick={() => {
                      console.log('Translation Registry:', (window as any).TRANSLATION_REGISTRY);
                      alert('Check console for translation registry');
                    }}
                    variant="outline"
                  >
                    View Registry
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}