import { lazy, Suspense, useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { HelmetProvider } from "react-helmet-async";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { AuthProvider } from "@/contexts/AuthContext";
import { LocaleProvider } from "@/contexts/LocaleContext";
import { TranslationProvider } from "@/contexts/TranslationContext";
import { ErrorBoundary } from "react-error-boundary";
import { initPerformanceMonitoring } from "@/utils/performance-monitor";
import { initMemoryGuard } from "@/utils/memory-guard";

// Eager load critical pages
import Index from "./pages/Index";
import SignIn from "./pages/SignIn";
import NotFound from "./pages/NotFound";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LocaleRedirect } from "./components/LocaleRedirect";

// Eager load public pages for better SEO and performance
import HomePage from "./pages/public/HomePage";
import BlogIndex from "./pages/public/BlogIndex";
import BlogPost from "./pages/public/BlogPost";
import RedirectHandler from "./components/RedirectHandler";

// Dynamic page component for CMS pages
const DynamicPage = lazy(() => import("./pages/DynamicPage"));

// Content detail page for blog posts with presentation templates
const ContentDetailPage = lazy(() => import("./pages/ContentDetailPage"));

// Lazy load all other pages for code splitting
const Profile = lazy(() => import("./pages/Profile"));
const Pages = lazy(() => import("./pages/Pages"));
const PageEditor = lazy(() => import("./pages/PageEditor"));
const Collections = lazy(() => import("./pages/Collections"));
const BlogPosts = lazy(() => import("./pages/BlogPosts"));
const BlogPostEditor = lazy(() => import("./pages/BlogPostEditor"));
const Categories = lazy(() => import("./pages/Categories"));
const Tags = lazy(() => import("./pages/Tags"));
const Media = lazy(() => import("./pages/Media"));
const TranslationsQueue = lazy(() => import("./pages/TranslationsQueue"));
const TranslatorWorkspace = lazy(() => import("./pages/TranslatorWorkspace"));
const UIMessages = lazy(() => import("./pages/UIMessages"));
const LocalesManagement = lazy(() => import("./pages/LocalesManagement"));
const UsersRoles = lazy(() => import("./pages/UsersRoles"));
const SEORedirects = lazy(() => import("./pages/SEORedirects"));
const Blocks = lazy(() => import("./pages/Blocks"));
const APIDocs = lazy(() => import("./pages/APIDocs"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const PasswordResetConfirm = lazy(() => import("./pages/auth/PasswordResetConfirm"));
const TestTranslations = lazy(() => import("./pages/TestTranslations"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes - shorter for better data freshness
      gcTime: 10 * 60 * 1000, // 10 minutes cache (renamed from cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchInterval: false, // Disable automatic refetching
      // Add network-aware options
      networkMode: 'online',
    },
    mutations: {
      retry: 1,
      networkMode: 'online',
    },
  },
  // Configure cache management
  logger: {
    log: import.meta.env.DEV ? console.log : () => {},
    warn: import.meta.env.DEV ? console.warn : () => {},
    error: console.error,
  },
});

// Loading component for lazy loaded routes
const LoadingSpinner = lazy(() => import("@/components/LoadingSpinner").then(module => ({ default: module.LoadingSpinner })));

const AppContent = () => {
  // Initialize memory guard
  useEffect(() => {
    // TEMPORARILY DISABLED: Memory guard might be causing issues
    // const memoryGuard = initMemoryGuard();
    
    return () => {
      // memoryGuard.destroy();
    };
  }, []);

  // Query cache cleanup on memory pressure
  useEffect(() => {
    const handleMemoryPressure = () => {
      // Clear old queries when memory pressure is detected
      queryClient.clear();
    };

    // Listen for custom memory pressure events from memory guard
    window.addEventListener('memory-pressure', handleMemoryPressure);
    
    return () => {
      window.removeEventListener('memory-pressure', handleMemoryPressure);
    };
  }, []);
  
  // Initialize performance monitoring only in development
  useEffect(() => {
    if (import.meta.env.DEV) {
      const monitor = initPerformanceMonitoring({
        debug: true,
        reportEndpoint: import.meta.env.VITE_ANALYTICS_ENDPOINT,
      });

      return () => {
        monitor.destroy();
      };
    }
  }, []);

  // Global keyboard shortcuts
  useKeyboardShortcuts();

  return (
    <RedirectHandler>
      <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>}>
        <Routes>
          {/* Root redirect to default locale */}
          <Route path="/" element={<LocaleRedirect><HomePage /></LocaleRedirect>} />
          
          {/* Language-prefixed public routes */}
          <Route path="/:locale" element={<HomePage />} />
          <Route path="/:locale/blog" element={<BlogIndex />} />
          <Route path="/:locale/blog/:slug" element={
            <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><LoadingSpinner /></div>}>
              <ContentDetailPage />
            </Suspense>
          } />
          
          {/* Legacy routes without language prefix - auto-redirect to locale-prefixed version */}
          <Route path="/blog" element={<LocaleRedirect><BlogIndex /></LocaleRedirect>} />
          <Route path="/blog/:slug" element={
            <LocaleRedirect>
              <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><LoadingSpinner /></div>}>
                <ContentDetailPage />
              </Suspense>
            </LocaleRedirect>
          } />
          
          {/* Dashboard interface entry point */}
          <Route path="/dashboard" element={<Index />} />
          
          {/* Protected dashboard routes */}
          <Route path="/dashboard/*" element={<ProtectedRoute />}>
            <Route path="" element={<Index />} />
            <Route path="profile" element={<Suspense fallback={<LoadingSpinner />}><Profile /></Suspense>} />
            <Route path="pages" element={<Suspense fallback={<LoadingSpinner />}><Pages /></Suspense>} />
            <Route path="pages/:id/edit" element={<Suspense fallback={<LoadingSpinner />}><PageEditor /></Suspense>} />
            <Route path="collections" element={<Suspense fallback={<LoadingSpinner />}><Collections /></Suspense>} />
            <Route path="blog-posts" element={<Suspense fallback={<LoadingSpinner />}><BlogPosts /></Suspense>} />
            <Route path="blog-posts/:id/edit" element={<Suspense fallback={<LoadingSpinner />}><BlogPostEditor /></Suspense>} />
            <Route path="categories" element={<Suspense fallback={<LoadingSpinner />}><Categories /></Suspense>} />
            <Route path="tags" element={<Suspense fallback={<LoadingSpinner />}><Tags /></Suspense>} />
            <Route path="media" element={<Suspense fallback={<LoadingSpinner />}><Media /></Suspense>} />
            <Route path="translations/queue" element={<Suspense fallback={<LoadingSpinner />}><TranslationsQueue /></Suspense>} />
            <Route path="translations/workspace" element={<Suspense fallback={<LoadingSpinner />}><TranslatorWorkspace /></Suspense>} />
            <Route path="translations/ui-messages" element={<Suspense fallback={<LoadingSpinner />}><UIMessages /></Suspense>} />
            <Route path="translations/locales" element={<Suspense fallback={<LoadingSpinner />}><LocalesManagement /></Suspense>} />
            <Route path="translations/test" element={<Suspense fallback={<LoadingSpinner />}><TestTranslations /></Suspense>} />
            <Route path="users-roles" element={<Suspense fallback={<LoadingSpinner />}><UsersRoles /></Suspense>} />
            <Route path="blocks" element={<Suspense fallback={<LoadingSpinner />}><Blocks /></Suspense>} />
            <Route path="seo/*" element={<Suspense fallback={<LoadingSpinner />}><SEORedirects /></Suspense>} />
            <Route path="api-docs" element={<Suspense fallback={<LoadingSpinner />}><APIDocs /></Suspense>} />
          </Route>

          {/* Authentication routes */}
          <Route path="/sign-in" element={<SignIn />} />
          <Route path="/dashboard/sign-in" element={<SignIn />} />
          <Route path="/forgot-password" element={<Suspense fallback={<LoadingSpinner />}><ForgotPassword /></Suspense>} />
          <Route path="/password-reset/:uid/:token" element={<Suspense fallback={<LoadingSpinner />}><PasswordResetConfirm /></Suspense>} />
          {/* Allauth-style password reset URL */}
          <Route path="/accounts/password/reset/key/:fulltoken" element={<Suspense fallback={<LoadingSpinner />}><PasswordResetConfirm /></Suspense>} />
          
          {/* Language-prefixed dynamic CMS pages */}
          <Route path="/:locale/*" element={<Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>}><DynamicPage /></Suspense>} />
          
          {/* Legacy dynamic CMS pages without language prefix for backward compatibility */}
          <Route path="*" element={<Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>}><DynamicPage /></Suspense>} />
        </Routes>
      </Suspense>
    </RedirectHandler>
  );
};

const App = () => (
  <ErrorBoundary
    fallback={({ error, resetErrorBoundary }) => (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold">Application Error</h1>
          <p className="text-muted-foreground">Something went wrong. Please try again.</p>
          <button
            onClick={resetErrorBoundary}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md"
          >
            Reload Application
          </button>
        </div>
      </div>
    )}
  >
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <AuthProvider>
                <LocaleProvider>
                  <TranslationProvider 
                    enableAutoSync={import.meta.env.DEV}
                    reportMissing={true}
                    syncInterval={30000}
                  >
                    <AppContent />
                  </TranslationProvider>
                </LocaleProvider>
              </AuthProvider>
            </BrowserRouter>
          </TooltipProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </HelmetProvider>
  </ErrorBoundary>
);

export default App;
