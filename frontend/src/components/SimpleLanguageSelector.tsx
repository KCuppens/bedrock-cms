import { memo } from "react";
import { useLocale } from "@/contexts/LocaleContext";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const SimpleLanguageSelector = memo(() => {
  const { activeLocales, currentLocale, setCurrentLocale } = useLocale();

  // Don't show if only one or no languages available
  if (activeLocales.length <= 1) return null;

  // Always show as dropdown with flags
  return (
    <Select
      value={currentLocale?.code}
      onValueChange={(code) => {
        const locale = activeLocales.find(l => l.code === code);
        if (locale) setCurrentLocale(locale);
      }}
    >
      <SelectTrigger className="w-[140px] h-8">
        <SelectValue>
          {currentLocale && (
            <div className="flex items-center gap-2">
              <span className="text-base">{currentLocale.flag}</span>
              <span className="text-sm font-medium">
                {currentLocale.code.toUpperCase()}
              </span>
            </div>
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {activeLocales.map(locale => (
          <SelectItem key={locale.code} value={locale.code}>
            <div className="flex items-center gap-2">
              <span className="text-base">{locale.flag}</span>
              <span className="font-medium">{locale.name}</span>
              <span className="text-xs text-muted-foreground">
                ({locale.code.toUpperCase()})
              </span>
              {locale.is_default && (
                <span className="text-xs text-muted-foreground ml-1">(default)</span>
              )}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
});

SimpleLanguageSelector.displayName = 'SimpleLanguageSelector';

export default SimpleLanguageSelector;