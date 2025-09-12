import {
  Home,
  FileText,
  Users,
  FileCheck,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  User,
  LogOut,
  Bell,
  Image,
  Globe,
  Clock,
  MessageSquare,
  Search,
  FolderOpen,
  BookOpen,
  Folder,
  Tag,
  Blocks
} from "lucide-react";
import { useState, useCallback, useMemo, memo, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { SignOutConfirmModal } from "@/components/modals/SignOutConfirmModal";
import { useAuth } from "@/contexts/AuthContext";
import { useTranslation } from "@/contexts/TranslationContext";

const Sidebar = memo(() => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [showSignOutModal, setShowSignOutModal] = useState(false);
  const [versionInfo, setVersionInfo] = useState<any>(null);

  const menuItems = useMemo(() => [
    { id: "home", icon: Home, label: t('dashboard.menu.home', 'Home'), href: "/dashboard" },
    { id: "pages", icon: FileText, label: t('dashboard.menu.pages', 'Pages'), href: "/dashboard/pages" },
    {
      id: "collections",
      icon: FolderOpen,
      label: t('dashboard.menu.collections', 'Collections'),
      expandable: true,
      children: [
        { label: t('dashboard.menu.blog_posts', 'Blog Posts'), href: "/dashboard/blog-posts" },
        { label: t('dashboard.menu.categories', 'Categories'), href: "/dashboard/categories" },
        { label: t('dashboard.menu.tags', 'Tags'), href: "/dashboard/tags" }
      ]
    },
    { id: "media", icon: Image, label: t('dashboard.menu.media', 'Media'), href: "/dashboard/media" },
    {
      id: "translations",
      icon: Globe,
      label: t('dashboard.menu.translations', 'Translations'),
      expandable: true,
      children: [
        { label: t('dashboard.menu.queue', 'Queue'), href: "/dashboard/translations/queue" },
        { label: t('dashboard.menu.ui_messages', 'UI Messages'), href: "/dashboard/translations/ui-messages" },
        { label: t('dashboard.menu.locales', 'Locales'), href: "/dashboard/translations/locales" }
      ]
    },
    { id: "blocks", icon: Blocks, label: t('dashboard.menu.blocks', 'Blocks'), href: "/dashboard/blocks" },
    { id: "users-roles", icon: Users, label: t('dashboard.menu.users_roles', 'Users & Roles'), href: "/dashboard/users-roles" },
    { id: "seo-redirects", icon: Search, label: t('dashboard.menu.seo_redirects', 'SEO & Redirects'), href: "/dashboard/seo" }
  ], [t]);

  // Function to check if a menu item has active children
  const hasActiveChild = useCallback((item: any) => {
    if (!item.expandable || !item.children) return false;
    return item.children.some((child: any) => location.pathname === child.href);
  }, [location.pathname]);

  // Function to check if a menu item should be active (for parent items)
  const isItemActive = useCallback((item: any) => {
    // For expandable items, they should be active if they have an active child
    if (item.expandable) {
      return hasActiveChild(item);
    }
    // For regular items, they should be active if their href matches exactly
    return item.href && location.pathname === item.href;
  }, [location.pathname, hasActiveChild]);

  // Function to get all parent items that should be expanded
  const getRequiredExpansions = useCallback(() => {
    const required: string[] = [];
    menuItems.forEach(item => {
      if (item.expandable && item.children) {
        const hasActive = item.children.some((child: any) => location.pathname === child.href);
        if (hasActive) {
          required.push(item.id);
        }
      }
    });
    return required;
  }, [menuItems, location.pathname]);

  // Auto-expand parent items when their children are active
  useEffect(() => {
    const requiredExpansions = getRequiredExpansions();
    setExpandedItems(prev => {
      const newExpanded = [...prev];
      let changed = false;

      requiredExpansions.forEach(itemId => {
        if (!newExpanded.includes(itemId)) {
          newExpanded.push(itemId);
          changed = true;
        }
      });

      return changed ? newExpanded : prev;
    });
  }, [getRequiredExpansions]);

  const toggleExpanded = useCallback((item: string) => {
    setExpandedItems(prev =>
      prev.includes(item)
        ? prev.filter(i => i !== item)
        : [...prev, item]
    );
  }, []);

  const handleProfileMenuToggle = useCallback(() => {
    setProfileMenuOpen(prev => !prev);
  }, []);

  const handleNavigation = useCallback((href: string) => {
    navigate(href);
  }, [navigate]);

  // Get user display name with fallback to email
  const getUserDisplayName = useCallback(() => {
    if (!user) return "User";

    // Try to use first name and last name
    if (user.first_name || user.last_name) {
      const firstName = user.first_name || "";
      const lastName = user.last_name || "";
      return `${firstName} ${lastName}`.trim();
    }

    // Fallback to name field if available
    if (user.name) {
      return user.name;
    }

    // Final fallback to email
    return user.email;
  }, [user]);

  // Get user initials for avatar
  const getUserInitials = useCallback(() => {
    if (!user) return "U";

    // Try to use first name and last name initials
    if (user.first_name || user.last_name) {
      const firstInitial = user.first_name ? user.first_name[0].toUpperCase() : "";
      const lastInitial = user.last_name ? user.last_name[0].toUpperCase() : "";
      return `${firstInitial}${lastInitial}` || "U";
    }

    // Try to use name field
    if (user.name) {
      const nameParts = user.name.split(" ");
      if (nameParts.length >= 2) {
        return `${nameParts[0][0]}${nameParts[nameParts.length - 1][0]}`.toUpperCase();
      }
      return user.name[0].toUpperCase();
    }

    // Fallback to email initial
    return user.email[0].toUpperCase();
  }, [user]);

  // Fetch version info on mount
  useEffect(() => {
    const fetchVersionInfo = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/system/version/');
        if (response.ok) {
          const data = await response.json();
          setVersionInfo(data);
        }
      } catch (error) {
        console.error('Failed to fetch version info:', error);
      }
    };

    fetchVersionInfo();
  }, []);

  return (
    <div className="w-72 h-screen overflow-y-auto fixed left-0 top-0 z-10">
      <div className="p-6 h-full flex flex-col">
        <div className="flex items-center gap-2 mb-8 bg-transparent relative">
          <img
            src="/bedrock-logo.png"
            alt="Bedrock"
            className="h-16 w-auto"
            style={{ background: 'transparent' }}
          />
        </div>

        <nav className="space-y-1 flex-1">
          {menuItems.map((item) => (
            <div key={item.id}>
        <div
          className={cn(
            "flex items-center justify-between w-full px-3 py-2.5 text-sm rounded-lg transition-colors cursor-pointer",
            isItemActive(item)
              ? "bg-foreground text-white"
              : "text-foreground/70 hover:bg-secondary hover:text-foreground"
          )}
        onClick={() => {
          if (item.expandable) {
            toggleExpanded(item.id);
          } else if (item.href) {
            handleNavigation(item.href);
          }
        }}
      >
                <div className="flex items-center gap-3">
                  <item.icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                {item.expandable && (
                  expandedItems.includes(item.id) ?
                    <ChevronDown className="w-4 h-4" /> :
                    <ChevronRight className="w-4 h-4" />
                )}
              </div>

              {item.expandable && item.children && expandedItems.includes(item.id) && (
                <div className="ml-7 mt-1 space-y-1 relative">
                  {/* Main vertical line connecting all items */}
                  <div className="absolute left-[-16px] top-[-4px] bottom-[14px] w-px bg-foreground/30"></div>

                  {item.children.map((child, idx) => (
                    <div key={idx} className="relative">
                      {/* Rounded corner connector for each item */}
                      <div className="absolute left-[-16px] top-[14px] w-4 h-4">
                        <div className="w-full h-full border-l border-b border-foreground/30 rounded-bl-md border-r-0 border-t-0"></div>
                      </div>
                      {/* Cover the vertical line after the last item */}
                      {idx === item.children!.length - 1 && (
                        <div className="absolute left-[-16px] top-[28px] w-px h-4 bg-background"></div>
                      )}
                      <a
                        onClick={(e) => {
                          e.preventDefault();
                          handleNavigation(child.href);
                        }}
                        href={child.href}
                        className={cn(
                          "block px-3 py-2 text-sm rounded-md transition-colors cursor-pointer",
                          location.pathname === child.href
                            ? "bg-foreground text-white font-medium"
                            : "text-foreground/60 hover:text-foreground hover:bg-secondary/50"
                        )}
                      >
                        {child.label}
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>

        <div className="mt-8 relative">
          <div
            className="flex items-center justify-between px-1 py-0.5 rounded-full bg-card cursor-pointer hover:bg-muted transition-colors shadow-subtle border border-border"
            onClick={handleProfileMenuToggle}
          >
            <div className="flex items-center gap-1">
              <div className="w-8 h-8 bg-foreground rounded-full flex items-center justify-center text-primary-foreground text-sm font-medium">
                {getUserInitials()}
              </div>
              <div className="text-sm">
                <div className="font-medium text-foreground">{getUserDisplayName()}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {profileMenuOpen ? (
                <ChevronUp className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              )}
            </div>
          </div>

          {/* Profile Dropdown Menu */}
          {profileMenuOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-2 bg-popover rounded-lg shadow-card border border-border z-50">
              <div className="py-2">
                <a
                  onClick={(e) => {
                    e.preventDefault();
                    handleNavigation("/dashboard/profile");
                  }}
                  href="/dashboard/profile"
                  className="flex items-center gap-3 px-4 py-2 text-sm text-popover-foreground hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer"
                >
                  <User className="w-4 h-4" />
                  <span>{t('dashboard.menu.profile_settings', 'Profile Settings')}</span>
                </a>
                <hr className="my-1 border-border" />
                <div className="px-2 py-1">
                  <div className="text-xs font-medium text-muted-foreground px-2 mb-1">{t('dashboard.menu.developer_api', 'Developer / API')}</div>
                  <a
                    onClick={(e) => {
                      e.preventDefault();
                      handleNavigation("/dashboard/api-docs");
                    }}
                    href="/dashboard/api-docs"
                    className="flex items-center gap-3 px-4 py-2 text-sm text-popover-foreground hover:bg-accent hover:text-accent-foreground transition-colors rounded-md cursor-pointer"
                  >
                    <FileText className="w-4 h-4" />
                    <span>{t('dashboard.menu.api_docs', 'API Docs (OpenAPI)')}</span>
                  </a>
                </div>
                <hr className="my-1 border-border" />
                <button
                  onClick={() => setShowSignOutModal(true)}
                  className="flex items-center gap-3 px-4 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors w-full text-left"
                >
                  <LogOut className="w-4 h-4" />
                  <span>{t('dashboard.menu.sign_out', 'Sign Out')}</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Version and Environment Info */}
        <div className="mt-auto pt-4 pb-2 px-2">
          <div className="text-xs text-muted-foreground space-y-1">
            <div className="flex items-center gap-2">
              {versionInfo && (
                <>
                  <span className={cn(
                    "w-2 h-2 rounded-full animate-pulse",
                    versionInfo.environment === 'production' ? 'bg-green-500' :
                    versionInfo.environment === 'staging' ? 'bg-yellow-500' :
                    versionInfo.environment === 'development' ? 'bg-blue-500' : 'bg-gray-500'
                  )} />
                  <span className="font-medium">
                    v{versionInfo.version || '0.0.0'}
                  </span>
                  <span className="text-muted-foreground/70">
                    {versionInfo.environment}
                  </span>
                </>
              )}
              {!versionInfo && (
                <span className="text-muted-foreground/50">{t('dashboard.menu.loading_version', 'Loading version...')}</span>
              )}
            </div>
            {versionInfo && versionInfo.branch && (
              <div className="text-[10px] text-muted-foreground/50 pl-4">
                {versionInfo.branch}
                {versionInfo.ahead > 0 && ` (+${versionInfo.ahead})`}
                {versionInfo.dirty && ' • modified'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sign Out Confirmation Modal */}
      <SignOutConfirmModal
        open={showSignOutModal}
        onOpenChange={setShowSignOutModal}
      />
    </div>
  );
});

Sidebar.displayName = 'Sidebar';

export default Sidebar;
