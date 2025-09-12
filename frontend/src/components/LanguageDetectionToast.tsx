import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useLocale } from "@/contexts/LocaleContext";
import { Button } from "@/components/ui/button";
import { getBrowserLanguages, matchBrowserToLocale } from "@/utils/browserLanguage";

/**
 * Optional component to show a toast when we detect a different language
 * than the current one based on browser preferences
 */
export const LanguageDetectionToast = () => {
  const { activeLocales, currentLocale, setCurrentLocale, defaultLocale } = useLocale();
  const [hasShownSuggestion, setHasShownSuggestion] = useState(false);

  useEffect(() => {
    // Only run once and if we have multiple locales
    if (hasShownSuggestion || activeLocales.length <= 1 || !currentLocale) {
      return;
    }

    // Check if we've already shown the suggestion this session
    const sessionShown = sessionStorage.getItem('language_suggestion_shown');
    if (sessionShown) {
      return;
    }

    // Get browser languages
    const browserLanguages = getBrowserLanguages();
    const suggestedLocaleCode = matchBrowserToLocale(browserLanguages, activeLocales);

    // If browser language is different from current and not the default
    if (suggestedLocaleCode &&
        suggestedLocaleCode !== currentLocale.code &&
        suggestedLocaleCode !== defaultLocale?.code) {

      const suggestedLocale = activeLocales.find(l => l.code === suggestedLocaleCode);

      if (suggestedLocale) {
        // Show toast with suggestion
        toast(
          <div className="flex flex-col gap-2">
            <p className="text-sm">
              Would you like to switch to {suggestedLocale.name}?
            </p>
            <p className="text-xs text-muted-foreground">
              We detected this might be your preferred language.
            </p>
            <div className="flex gap-2 mt-2">
              <Button
                size="sm"
                variant="default"
                onClick={() => {
                  setCurrentLocale(suggestedLocale);
                  toast.dismiss();
                  toast.success(`Switched to ${suggestedLocale.name}`);
                }}
              >
                Switch to {suggestedLocale.name}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  toast.dismiss();
                }}
              >
                Keep {currentLocale.name}
              </Button>
            </div>
          </div>,
          {
            duration: 10000, // Show for 10 seconds
            position: "bottom-right",
          }
        );

        setHasShownSuggestion(true);
        sessionStorage.setItem('language_suggestion_shown', 'true');
      }
    }
  }, [activeLocales, currentLocale, defaultLocale, setCurrentLocale, hasShownSuggestion]);

  return null;
};

export default LanguageDetectionToast;
