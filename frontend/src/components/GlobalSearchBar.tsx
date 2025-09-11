import { useState, useCallback, useEffect, useMemo } from "react";
import { Search, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

interface SearchResult {
  id: string | number;
  title: string;
  type: string;
  icon: string;
  description?: string;
  url: string;
  status?: string;
  [key: string]: any;
}

interface SearchResults {
  [key: string]: SearchResult[];
}

export const GlobalSearchBar = () => {
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResults>({});
  const [isSearching, setIsSearching] = useState(false);
  const navigate = useNavigate();
  
  // Debounce search query
  const debouncedSearchValue = useDebounce(searchValue, 300);

  // Perform search when debounced value changes
  useEffect(() => {
    const performSearch = async () => {
      if (debouncedSearchValue.length < 2) {
        setSearchResults({});
        return;
      }

      setIsSearching(true);
      try {
        const response = await fetch(
          `${import.meta.env.VITE_API_URL || '/api/v1'}/search/global/?q=${encodeURIComponent(debouncedSearchValue)}`,
          {
            credentials: 'include',
            headers: {
              'Accept': 'application/json',
            },
          }
        );
        
        if (response.ok) {
          const data = await response.json();
          setSearchResults(data.results || {});
        } else {
          console.error('Search failed:', response.status);
          setSearchResults({});
        }
      } catch (error) {
        console.error('Search error:', error);
        setSearchResults({});
      } finally {
        setIsSearching(false);
      }
    };

    performSearch();
  }, [debouncedSearchValue]);

  // Group labels for search results
  const groupLabels: Record<string, string> = {
    pages: "Pages",
    blog_posts: "Blog Posts",
    media: "Media Files",
    collections: "Collections",
    categories: "Categories",
    tags: "Tags",
    translations: "Translations",
    users: "Users",
    redirects: "Redirects",
  };

  // Get total results count
  const totalResults = useMemo(() => {
    return Object.values(searchResults).reduce((total, items) => 
      total + (Array.isArray(items) ? items.length : 0), 0
    );
  }, [searchResults]);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchValue(e.target.value);
    if (e.target.value.length > 0) {
      setSearchOpen(true);
    } else {
      setSearchOpen(false);
    }
  }, []);

  const handleSearchFocus = useCallback(() => {
    if (searchValue.length > 0) {
      setSearchOpen(true);
    }
  }, [searchValue]);

  const handleSearchItemSelect = useCallback((url: string) => {
    setSearchValue("");
    setSearchOpen(false);
    setSearchResults({});
    navigate(url);
  }, [navigate]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // Close on Escape
    if (e.key === 'Escape') {
      setSearchOpen(false);
    }
  }, []);

  return (
    <div className="flex-1 max-w-md">
      <Popover open={searchOpen} onOpenChange={setSearchOpen}>
        <PopoverTrigger asChild>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground z-10 pointer-events-none" />
            <Input
              placeholder="Search pages, media, translations..."
              value={searchValue}
              onChange={handleSearchChange}
              onFocus={handleSearchFocus}
              onKeyDown={handleKeyDown}
              className="pl-10 pr-10 bg-white border-border/40 focus:bg-white focus:border-primary/50 focus-visible:ring-primary/20"
            />
            {isSearching && (
              <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground animate-spin pointer-events-none" />
            )}
          </div>
        </PopoverTrigger>
        <PopoverContent 
          className="w-[400px] p-0 bg-card border border-border/40 shadow-xl rounded-lg" 
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <Command>
            <CommandList className="max-h-[400px] overflow-y-auto">
              {/* Loading state */}
              {isSearching && (
                <div className="p-4 text-sm text-muted-foreground text-center flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Searching...
                </div>
              )}
              
              {/* Minimum characters message */}
              {!isSearching && searchValue.length > 0 && searchValue.length < 2 && (
                <div className="p-4 text-sm text-muted-foreground text-center">
                  Type at least 2 characters to search
                </div>
              )}
              
              {/* No results */}
              {!isSearching && totalResults === 0 && searchValue.length >= 2 && (
                <CommandEmpty>
                  <div className="p-4 text-center">
                    <p className="text-sm text-muted-foreground">No results found for</p>
                    <p className="text-sm font-medium">"{searchValue}"</p>
                  </div>
                </CommandEmpty>
              )}
              
              {/* Search results by group */}
              {!isSearching && Object.entries(searchResults).map(([groupKey, items]) => {
                if (!Array.isArray(items) || items.length === 0) return null;
                
                return (
                  <CommandGroup key={groupKey} heading={groupLabels[groupKey] || groupKey}>
                    {items.map((item) => (
                      <CommandItem
                        key={`${groupKey}-${item.id}`}
                        value={item.title}
                        onSelect={() => handleSearchItemSelect(item.url)}
                        className="cursor-pointer hover:bg-accent/50 px-3 py-2"
                      >
                        <div className="flex items-center gap-3 w-full">
                          <span className="text-lg flex-shrink-0">{item.icon}</span>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{item.title}</div>
                            {item.description && (
                              <div className="text-xs text-muted-foreground truncate">
                                {item.description}
                              </div>
                            )}
                          </div>
                          {item.status && (
                            <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${
                              item.status === 'published' ? 'bg-green-100 text-green-700' :
                              item.status === 'draft' ? 'bg-yellow-100 text-yellow-700' :
                              item.status === 'active' ? 'bg-blue-100 text-blue-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {item.status}
                            </span>
                          )}
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                );
              })}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
};