/**
 * Detects the user's preferred language from browser settings
 */
export function getBrowserLanguage(): string | null {
  // Check navigator.language (primary language)
  if (navigator.language) {
    return navigator.language.toLowerCase();
  }
  
  // Fallback to navigator.userLanguage (IE)
  if ((navigator as any).userLanguage) {
    return (navigator as any).userLanguage.toLowerCase();
  }
  
  return null;
}

/**
 * Gets all preferred languages from browser in order of preference
 */
export function getBrowserLanguages(): string[] {
  const languages: string[] = [];
  
  // Primary language
  if (navigator.language) {
    languages.push(navigator.language.toLowerCase());
  }
  
  // All preferred languages
  if (navigator.languages && navigator.languages.length > 0) {
    navigator.languages.forEach(lang => {
      const normalized = lang.toLowerCase();
      if (!languages.includes(normalized)) {
        languages.push(normalized);
      }
    });
  }
  
  // IE fallback
  if ((navigator as any).userLanguage && !languages.includes((navigator as any).userLanguage.toLowerCase())) {
    languages.push((navigator as any).userLanguage.toLowerCase());
  }
  
  return languages;
}

/**
 * Matches browser language to available locale
 * Tries exact match first, then language code only
 */
export function matchBrowserToLocale(
  browserLangs: string[], 
  availableLocales: Array<{ code: string; is_active: boolean }>
): string | null {
  // Only consider active locales
  const activeLocales = availableLocales.filter(l => l.is_active);
  
  for (const browserLang of browserLangs) {
    // Try exact match (e.g., "en-us" matches "en-US")
    const exactMatch = activeLocales.find(
      locale => locale.code.toLowerCase() === browserLang
    );
    if (exactMatch) {
      return exactMatch.code;
    }
    
    // Try language part only (e.g., "en-us" matches "en")
    const langPart = browserLang.split('-')[0];
    const partialMatch = activeLocales.find(
      locale => locale.code.toLowerCase().startsWith(langPart)
    );
    if (partialMatch) {
      return partialMatch.code;
    }
  }
  
  return null;
}

/**
 * Check if this is the user's first visit (no language preference stored)
 */
export function isFirstVisit(): boolean {
  return !localStorage.getItem('current_locale') && !localStorage.getItem('language_auto_detected');
}

/**
 * Mark that we've already auto-detected language for this browser
 */
export function markAutoDetected(): void {
  localStorage.setItem('language_auto_detected', 'true');
}