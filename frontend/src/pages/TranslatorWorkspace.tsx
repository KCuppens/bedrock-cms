import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import {
  Search,
  Languages,
  ExternalLink,
  Sparkles,
  Save,
  CheckCircle2,
  ArrowLeft,
  Book,
  BarChart3,
  Lightbulb,
  Clock,
  AlertCircle,
  Info,
} from "lucide-react";

interface TranslationUnit {
  id: string;
  key: string;
  model: string;
  objectId: string;
  field: string;
  sourceLocale: string;
  targetLocale: string;
  sourceText: string;
  targetText: string;
  status: 'missing' | 'draft' | 'needs_review' | 'approved';
  context?: string;
  objectTitle?: string;
  objectUrl?: string;
}

interface GlossaryEntry {
  term: string;
  translation: string;
  context?: string;
  category: string;
}

const mockUnit: TranslationUnit = {
  id: "1",
  key: "page#1.title",
  model: "page",
  objectId: "1",
  field: "title",
  sourceLocale: "EN",
  targetLocale: "ES",
  sourceText: "Welcome to Our Amazing Platform - Discover the future of web development with cutting-edge tools, innovative solutions, and seamless integration capabilities that will transform your digital presence.",
  targetText: "Bienvenido a Nuestra Increíble Plataforma",
  status: "draft",
  context: "Homepage main heading - should convey excitement and innovation",
  objectTitle: "Homepage",
  objectUrl: "/preview/page/1"
};

const mockGlossary: GlossaryEntry[] = [
  {
    term: "platform",
    translation: "plataforma",
    context: "Software/Technology context",
    category: "Technical"
  },
  {
    term: "cutting-edge",
    translation: "vanguardista, de última generación",
    context: "When referring to technology",
    category: "Marketing"
  },
  {
    term: "innovative",
    translation: "innovador(a)",
    context: "General business context",
    category: "Business"
  },
  {
    term: "seamless",
    translation: "sin interrupciones, fluido",
    context: "User experience context",
    category: "UX"
  }
];

const TranslatorWorkspace = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const unitId = searchParams.get('unit');

  const [unit, setUnit] = useState<TranslationUnit>(mockUnit);
  const [targetText, setTargetText] = useState(unit.targetText);
  const [status, setStatus] = useState(unit.status);
  const [sourceLocale, setSourceLocale] = useState(unit.sourceLocale);
  const [targetLocale, setTargetLocale] = useState(unit.targetLocale);
  const [searchTerm, setSearchTerm] = useState("");
  const [lastSaved, setLastSaved] = useState<Date>(new Date());
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [mtSuggestion, setMtSuggestion] = useState("");
  const [showMtSuggestion, setShowMtSuggestion] = useState(false);

  // Word and character counts
  const sourceWordCount = unit.sourceText.split(/\s+/).filter(word => word.length > 0).length;
  const sourceCharCount = unit.sourceText.length;
  const targetWordCount = targetText.split(/\s+/).filter(word => word.length > 0).length;
  const targetCharCount = targetText.length;

  // Filter glossary based on search
  const filteredGlossary = mockGlossary.filter(entry =>
    entry.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
    entry.translation.toLowerCase().includes(searchTerm.toLowerCase()) ||
    entry.category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Auto-save functionality
  useEffect(() => {
    if (hasUnsavedChanges) {
      const timer = setTimeout(() => {
        handleSave();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [targetText, status, hasUnsavedChanges, handleSave]);

  const handleTargetTextChange = (value: string) => {
    setTargetText(value);
    setHasUnsavedChanges(true);
  };

  const handleStatusChange = (newStatus: string) => {
    setStatus(newStatus as typeof status);
    setHasUnsavedChanges(true);
  };

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));
    setLastSaved(new Date());
    setHasUnsavedChanges(false);
    setIsSaving(false);
  }, []);

  const handleMtSuggest = async () => {
    setShowMtSuggestion(true);
    try {
      // Call real MT API
      const response = await api.i18n.translations.mtSuggest(
        unit.id,
        unit.sourceText,
        unit.sourceLocale || 'en',
        unit.targetLocale || 'en',
        'deepl'
      );
      const suggestion = response.data?.suggestion || response.suggestion;
      if (suggestion) {
        setMtSuggestion(suggestion);
      } else {
        setMtSuggestion("No translation suggestion available");
      }
    } catch (error) {
      console.error('Failed to get MT suggestion:', error);
      // Fallback to a message
      setMtSuggestion("Translation service temporarily unavailable");
    }
  };

  const acceptMtSuggestion = () => {
    setTargetText(mtSuggestion);
    setShowMtSuggestion(false);
    setHasUnsavedChanges(true);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />

        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />

          {/* Workspace Header */}
          <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Button variant="ghost" size="sm" onClick={() => navigate('/translations/queue')}>
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Queue
                  </Button>

                  <Separator orientation="vertical" className="h-6" />

                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <a href={unit.objectUrl} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="w-4 h-4 mr-2" />
                        {unit.objectTitle}
                      </a>
                    </Button>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Select value={sourceLocale} onValueChange={setSourceLocale}>
                      <SelectTrigger className="w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="EN">EN</SelectItem>
                        <SelectItem value="ES">ES</SelectItem>
                        <SelectItem value="FR">FR</SelectItem>
                        <SelectItem value="DE">DE</SelectItem>
                      </SelectContent>
                    </Select>

                    <Languages className="w-4 h-4 text-muted-foreground" />

                    <Select value={targetLocale} onValueChange={setTargetLocale}>
                      <SelectTrigger className="w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ES">ES</SelectItem>
                        <SelectItem value="FR">FR</SelectItem>
                        <SelectItem value="DE">DE</SelectItem>
                        <SelectItem value="IT">IT</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Unit Info */}
              <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
                <code className="bg-muted px-2 py-1 rounded">{unit.key}</code>
                <Badge variant="secondary">{unit.model}</Badge>
                {unit.context && (
                  <div className="flex items-center gap-1">
                    <Info className="w-3 h-3" />
                    <span>{unit.context}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex-1 flex">
            {/* Left Panel - Source */}
            <div className="w-1/2 border-r bg-background">
              <div className="p-4 border-b">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-foreground">Source ({sourceLocale})</h2>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>{sourceWordCount} words</span>
                    <span>{sourceCharCount} chars</span>
                  </div>
                </div>
              </div>

              <div className="p-4 h-full flex flex-col">
                {/* Search within source */}
                <div className="relative mb-4">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Search in source text..."
                    className="pl-10"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>

                {/* Source text - read only */}
                <div className="flex-1 bg-muted/30 p-4 rounded-lg overflow-y-auto">
                  <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                    {unit.sourceText}
                  </p>
                </div>

                {/* Glossary */}
                <div className="mt-4">
                  <h3 className="font-medium mb-2 flex items-center gap-2">
                    <Book className="w-4 h-4" />
                    Glossary
                  </h3>
                  <div className="max-h-48 overflow-y-auto space-y-2">
                    {filteredGlossary.map((entry, index) => (
                      <div key={index} className="bg-muted/30 p-2 rounded text-xs">
                        <div className="font-medium">{entry.term} → {entry.translation}</div>
                        {entry.context && (
                          <div className="text-muted-foreground mt-1">{entry.context}</div>
                        )}
                        <Badge variant="outline" className="text-xs mt-1">
                          {entry.category}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Right Panel - Target */}
            <div className="w-1/2 bg-background">
              <div className="p-4 border-b">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-foreground">Target ({targetLocale})</h2>
                  <div className="flex items-center gap-4">
                    <div className="text-sm text-muted-foreground">
                      <span>{targetWordCount} words</span>
                      <span className="ml-2">{targetCharCount} chars</span>
                    </div>
                    <Select value={status} onValueChange={handleStatusChange}>
                      <SelectTrigger className="w-36">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="draft">Draft</SelectItem>
                        <SelectItem value="needs_review">Needs Review</SelectItem>
                        <SelectItem value="approved">Approved</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <div className="p-4 h-full flex flex-col">
                {/* MT Suggestion */}
                {showMtSuggestion && mtSuggestion && (
                  <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-blue-600" />
                        <span className="text-sm font-medium text-blue-800">MT Suggestion</span>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={acceptMtSuggestion}>
                          Accept
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setShowMtSuggestion(false)}>
                          Dismiss
                        </Button>
                      </div>
                    </div>
                    <p className="text-sm text-blue-700 bg-white p-2 rounded border">
                      {mtSuggestion}
                    </p>
                  </div>
                )}

                {/* Target text editor */}
                <div className="flex-1 mb-4">
                  <Textarea
                    value={targetText}
                    onChange={(e) => handleTargetTextChange(e.target.value)}
                    placeholder="Enter translation..."
                    className="h-full resize-none font-mono text-sm leading-relaxed"
                  />
                </div>

                {/* Hints and Validation */}
                <div className="mb-4 space-y-2">
                  {targetText.length > unit.sourceText.length * 1.5 && (
                    <div className="flex items-center gap-2 text-yellow-600 text-sm">
                      <AlertCircle className="w-4 h-4" />
                      Translation is significantly longer than source
                    </div>
                  )}

                  {targetWordCount < sourceWordCount * 0.5 && targetText.length > 0 && (
                    <div className="flex items-center gap-2 text-yellow-600 text-sm">
                      <AlertCircle className="w-4 h-4" />
                      Translation seems incomplete
                    </div>
                  )}
                </div>

                {/* Progress indicator */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Completion</span>
                    <span className="text-muted-foreground">
                      {Math.min(Math.round((targetCharCount / sourceCharCount) * 100), 100)}%
                    </span>
                  </div>
                  <Progress
                    value={Math.min((targetCharCount / sourceCharCount) * 100, 100)}
                    className="h-2"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleMtSuggest}
                    disabled={showMtSuggestion}
                  >
                    <Sparkles className="w-4 h-4 mr-2" />
                    MT Suggest
                  </Button>

                  <Button variant="outline" size="sm">
                    <Lightbulb className="w-4 h-4 mr-2" />
                    Glossary Hints
                  </Button>

                  <Button variant="outline" size="sm">
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Quality Check
                  </Button>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-sm text-muted-foreground flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    {hasUnsavedChanges ? (
                      <span className="text-yellow-600">Unsaved changes</span>
                    ) : (
                      <span>Last saved: {formatTime(lastSaved)}</span>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={handleSave}
                      disabled={isSaving || !hasUnsavedChanges}
                    >
                      <Save className="w-4 h-4 mr-2" />
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>

                    <Button
                      onClick={() => {
                        handleStatusChange('approved');
                        handleSave();
                      }}
                      disabled={!targetText.trim()}
                    >
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Save & Approve
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranslatorWorkspace;