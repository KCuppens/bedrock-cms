import { ChevronRight, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useState, useCallback, useMemo, memo } from "react";

const DashboardHeader = memo(() => {
  const [languageDropdownOpen, setLanguageDropdownOpen] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState({ code: 'en', name: 'English', flag: '🇺🇸' });

  const languages = useMemo(() => [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'fr', name: 'Français', flag: '🇫🇷' },
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
    { code: 'it', name: 'Italiano', flag: '🇮🇹' },
    { code: 'pt', name: 'Português', flag: '🇵🇹' },
  ], []);

  const handleLanguageSelect = useCallback((language: typeof selectedLanguage) => {
    setSelectedLanguage(language);
    setLanguageDropdownOpen(false);
  }, []);

  const toggleLanguageDropdown = useCallback(() => {
    setLanguageDropdownOpen(prev => !prev);
  }, []);

  return (
    <div className="flex flex-col gap-4 mb-6">
      {/* Language Selector - Top Right */}
      <div className="flex justify-end">
        <div className="relative">
          <div
            className="flex items-center gap-2 px-3 py-1.5 bg-accent rounded-lg cursor-pointer hover:bg-accent/80 transition-colors"
            onClick={toggleLanguageDropdown}
          >
            <span className="text-lg">{selectedLanguage.flag}</span>
            <span className="text-sm text-accent-foreground">{selectedLanguage.name}</span>
            <ChevronDown className="w-3 h-3 text-accent-foreground" />
          </div>

          {/* Dropdown Menu */}
          {languageDropdownOpen && (
            <div className="absolute top-full right-0 mt-1 bg-popover border border-border rounded-lg shadow-card z-50 min-w-[140px]">
              <div className="py-2">
                {languages.map((language) => (
                  <div
                    key={language.code}
                    className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors"
                    onClick={() => handleLanguageSelect(language)}
                  >
                    <span className="text-lg">{language.flag}</span>
                    <span>{language.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>Homepage</span>
        <ChevronRight className="w-4 h-4" />
        <span>Risk Management</span>
        <ChevronRight className="w-4 h-4" />
        <span>Risk Register</span>
        <ChevronRight className="w-4 h-4" />
        <span className="text-foreground font-medium">Details</span>
      </nav>

      {/* Header with actions */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">R-143: Vendors Data Leak Due To Human Error</h1>
      </div>
    </div>
  );
});

DashboardHeader.displayName = 'DashboardHeader';

export default DashboardHeader;
