import { Suspense, useEffect } from "react";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/contexts/AuthContext";
import { LanguageProvider } from "@/contexts/LanguageContext";
import LoadingSpinner from "@/components/LoadingSpinner";
import { lazyWithPreload, preloadOnIdle, preloadOnFastConnection } from "@/utils/lazyWithPreload";

// Configure QueryClient with optimized settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Lazy load all routes with preload capability
const Login = lazyWithPreload(() => import("@/pages/Login"), "Login");
const Dashboard = lazyWithPreload(() => import("@/pages/Dashboard"), "Dashboard");
const Pages = lazyWithPreload(() => import("@/pages/Pages"), "Pages");
const PageEditor = lazyWithPreload(() => import("@/pages/PageEditor"), "PageEditor");
const BlogPosts = lazyWithPreload(() => import("@/pages/BlogPosts"), "BlogPosts");
const BlogPostEditor = lazyWithPreload(() => import("@/pages/BlogPostEditor"), "BlogPostEditor");
const Media = lazyWithPreload(() => import("@/pages/Media"), "Media");
const SEORedirects = lazyWithPreload(() => import("@/pages/SEORedirects"), "SEORedirects");
const UsersRoles = lazyWithPreload(() => import("@/pages/UsersRoles"), "UsersRoles");
const Locales = lazyWithPreload(() => import("@/pages/Locales"), "Locales");
const TranslationsQueue = lazyWithPreload(() => import("@/pages/TranslationsQueue"), "TranslationsQueue");
const TranslatorWorkspace = lazyWithPreload(() => import("@/pages/TranslatorWorkspace"), "TranslatorWorkspace");
const UIMessages = lazyWithPreload(() => import("@/pages/UIMessages"), "UIMessages");
const Profile = lazyWithPreload(() => import("@/pages/Profile"), "Profile");
const APIDocs = lazyWithPreload(() => import("@/pages/APIDocs"), "APIDocs");
const CMSSettings = lazyWithPreload(() => import("@/pages/CMSSettings"), "CMSSettings");
const BlockTypeManager = lazyWithPreload(() => import("@/pages/BlockTypeManager"), "BlockTypeManager");
const RegistryManager = lazyWithPreload(() => import("@/pages/RegistryManager"), "RegistryManager");
const LiveContent = lazyWithPreload(() => import("@/pages/LiveContent"), "LiveContent");
const BlogPage = lazyWithPreload(() => import("@/pages/BlogPage"), "BlogPage");
const BlogPostPage = lazyWithPreload(() => import("@/pages/BlogPostPage"), "BlogPostPage");
const PublicPage = lazyWithPreload(() => import("@/pages/PublicPage"), "PublicPage");

// Group components for strategic preloading
const coreComponents = [Dashboard, Pages, BlogPosts];
const editorComponents = [PageEditor, BlogPostEditor];
const adminComponents = [UsersRoles, SEORedirects, CMSSettings];
const translationComponents = [TranslationsQueue, TranslatorWorkspace, UIMessages];

const App = () => {
  useEffect(() => {
    // Preload core components after initial render
    preloadOnIdle(coreComponents, 2000);

    // Preload admin components on fast connections
    preloadOnFastConnection(adminComponents);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="light"
        enableSystem={false}
        disableTransitionOnChange
      >
        <TooltipProvider delayDuration={300}>
          <LanguageProvider>
            <AuthProvider>
              <Toaster position="top-right" duration={4000} />
              <BrowserRouter>
                <Suspense fallback={<LoadingSpinner fullScreen />}>
                  <Routes>
                    {/* Public routes */}
                    <Route path="/login" element={<Login />} />

                    {/* Main app routes */}
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />

                    {/* Content management */}
                    <Route path="/pages" element={<Pages />} />
                    <Route path="/pages/new" element={<PageEditor />} />
                    <Route path="/pages/:id/edit" element={<PageEditor />} />
                    <Route path="/blog" element={<BlogPosts />} />
                    <Route path="/blog/new" element={<BlogPostEditor />} />
                    <Route path="/blog/:id/edit" element={<BlogPostEditor />} />
                    <Route path="/media" element={<Media />} />

                    {/* SEO & Settings */}
                    <Route path="/seo/redirects" element={<SEORedirects />} />
                    <Route path="/settings" element={<CMSSettings />} />
                    <Route path="/settings/blocks" element={<BlockTypeManager />} />
                    <Route path="/settings/registry" element={<RegistryManager />} />

                    {/* Users & Permissions */}
                    <Route path="/users" element={<UsersRoles />} />
                    <Route path="/profile" element={<Profile />} />

                    {/* Localization */}
                    <Route path="/locales" element={<Locales />} />
                    <Route path="/translations" element={<TranslationsQueue />} />
                    <Route path="/translations/workspace" element={<TranslatorWorkspace />} />
                    <Route path="/translations/ui-messages" element={<UIMessages />} />

                    {/* Documentation */}
                    <Route path="/api-docs" element={<APIDocs />} />

                    {/* Live preview routes */}
                    <Route path="/live/*" element={<LiveContent />} />
                    <Route path="/blog-preview" element={<BlogPage />} />
                    <Route path="/blog-preview/:slug" element={<BlogPostPage />} />
                    <Route path="/preview/*" element={<PublicPage />} />
                  </Routes>
                </Suspense>
              </BrowserRouter>
            </AuthProvider>
          </LanguageProvider>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;
