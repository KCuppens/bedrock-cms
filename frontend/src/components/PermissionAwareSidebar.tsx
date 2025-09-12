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
  BarChart3,
  Settings,
  Shield,
  Redirect
} from "lucide-react";
import { useState, useCallback, useMemo, memo, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { SignOutConfirmModal } from "@/components/modals/SignOutConfirmModal";
import { useAuth } from "@/contexts/AuthContext";
import { usePermissions } from "@/hooks/usePermissions";

interface MenuItem {
  id: string;
  icon: any;
  label: string;
  href?: string;
  expandable?: boolean;
  children?: Array<{
    label: string;
    href: string;
    permissions?: string[];
    roles?: string[];
  }>;
  permissions?: string[];
  roles?: string[];
  customCheck?: (perms: ReturnType<typeof usePermissions>) => boolean;
}

const PermissionAwareSidebar = memo(() => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const permissions = usePermissions();
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [showSignOutModal, setShowSignOutModal] = useState(false);
  const [versionInfo, setVersionInfo] = useState<any>(null);

  // Define all menu items with their permission requirements
  const allMenuItems: MenuItem[] = useMemo(() => [
    {
      id: "home",
      icon: Home,
      label: "Dashboard",
      href: "/dashboard"
    },
    {
      id: "pages",
      icon: FileText,
      label: "Pages",
      href: "/dashboard/pages",
      permissions: ['cms.view_page']
    },
    {
      id: "blog",
      icon: BookOpen,
      label: "Blog",
      expandable: true,
      permissions: ['blog.view_blogpost'],
      children: [
        {
          label: "Posts",
          href: "/dashboard/blog",
          permissions: ['blog.view_blogpost']
        },
        {
          label: "Categories",
          href: "/dashboard/blog/categories",
          permissions: ['blog.view_category']
        },
        {
          label: "Tags",
          href: "/dashboard/blog/tags",
          permissions: ['blog.view_tag']
        }
      ]
    },
    {
      id: "collections",
      icon: FolderOpen,
      label: "Collections",
      expandable: true,
      permissions: ['cms.view_collection'],
      children: [
        {
          label: "All Collections",
          href: "/dashboard/collections",
          permissions: ['cms.view_collection']
        },
        {
          label: "Categories",
          href: "/dashboard/categories",
          permissions: ['cms.view_category']
        },
        {
          label: "Tags",
          href: "/dashboard/tags",
          permissions: ['cms.view_tag']
        }
      ]
    },
    {
      id: "media",
      icon: Image,
      label: "Media",
      href: "/dashboard/media",
      permissions: ['files.view_fileupload']
    },
    {
      id: "translations",
      icon: Globe,
      label: "Translations",
      expandable: true,
      permissions: ['i18n.view_translationunit'],
      children: [
        {
          label: "Queue",
          href: "/dashboard/translations/queue",
          permissions: ['i18n.view_translationqueue']
        },
        {
          label: "UI Messages",
          href: "/dashboard/translations/ui-messages",
          permissions: ['i18n.view_uimessage']
        },
        {
          label: "Locales",
          href: "/dashboard/translations/locales",
          permissions: ['i18n.view_locale']
        },
        {
          label: "Glossary",
          href: "/dashboard/translations/glossary",
          permissions: ['i18n.view_glossary']
        }
      ]
    },
    {
      id: "seo",
      icon: Search,
      label: "SEO & Redirects",
      expandable: true,
      permissions: ['cms.view_redirect'],
      children: [
        {
          label: "Redirects",
          href: "/dashboard/seo/redirects",
          permissions: ['cms.view_redirect']
        },
        {
          label: "SEO Settings",
          href: "/dashboard/seo/settings",
          permissions: ['cms.view_seosettings']
        }
      ]
    },
    {
      id: "analytics",
      icon: BarChart3,
      label: "Analytics",
      href: "/dashboard/analytics",
      permissions: ['analytics.view_analytics']
    },
    {
      id: "users-roles",
      icon: Users,
      label: "Users & Roles",
      href: "/dashboard/users-roles",
      roles: ['admin', 'manager']
    },
    {
      id: "settings",
      icon: Settings,
      label: "Settings",
      href: "/dashboard/settings",
      roles: ['admin']
    }
  ], []);

  // Filter menu items based on user permissions
  const visibleMenuItems = useMemo(() => {
    if (permissions.isLoading) return [];

    const filterItem = (item: MenuItem): MenuItem | null => {
      // Check custom permission function
      if (item.customCheck && !item.customCheck(permissions)) {
        return null;
      }

      // Check required permissions
      if (item.permissions && item.permissions.length > 0) {
        if (!permissions.hasAnyPermission(item.permissions)) {
          return null;
        }
      }

      // Check required roles
      if (item.roles && item.roles.length > 0) {
        if (!permissions.hasAnyRole(item.roles)) {
          return null;
        }
      }

      // Filter children if expandable
      if (item.expandable && item.children) {
        const visibleChildren = item.children.filter(child => {
          // Check child permissions
          if (child.permissions && child.permissions.length > 0) {
            if (!permissions.hasAnyPermission(child.permissions)) {
              return false;
            }
          }

          // Check child roles
          if (child.roles && child.roles.length > 0) {
            if (!permissions.hasAnyRole(child.roles)) {
              return false;
            }
          }

          return true;
        });

        // If no children are visible, hide the parent
        if (visibleChildren.length === 0) {
          return null;
        }

        return {
          ...item,
          children: visibleChildren
        };
      }

      return item;
    };

    return allMenuItems
      .map(filterItem)
      .filter((item): item is MenuItem => item !== null);
  }, [allMenuItems, permissions]);

  // Function to check if a menu item has active children
  const hasActiveChild = useCallback((item: MenuItem) => {
    if (!item.expandable || !item.children) return false;
    return item.children.some(child => location.pathname === child.href);
  }, [location.pathname]);

  // Function to check if a menu item should be active
  const isItemActive = useCallback((item: MenuItem) => {
    if (item.expandable) {
      return hasActiveChild(item);
    }
    return item.href && location.pathname === item.href;
  }, [location.pathname, hasActiveChild]);

  // Function to get all parent items that should be expanded
  const getRequiredExpansions = useCallback(() => {
    const required: string[] = [];
    visibleMenuItems.forEach(item => {
      if (item.expandable && item.children) {
        const hasActive = item.children.some(child => location.pathname === child.href);
        if (hasActive) {
          required.push(item.id);
        }
      }
    });
    return required;
  }, [visibleMenuItems, location.pathname]);

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
    setProfileMenuOpen(false); // Close profile menu on navigation
  }, [navigate]);

  // Get user display name with fallback to email
  const getUserDisplayName = useCallback(() => {
    if (!user) return "User";

    if (user.first_name || user.last_name) {
      const firstName = user.first_name || "";
      const lastName = user.last_name || "";
      return `${firstName} ${lastName}`.trim();
    }

    if (user.name) {
      return user.name;
    }

    return user.email;
  }, [user]);

  // Get user initials for avatar
  const getUserInitials = useCallback(() => {
    if (!user) return "U";

    if (user.first_name || user.last_name) {
      const firstInitial = user.first_name ? user.first_name[0].toUpperCase() : "";
      const lastInitial = user.last_name ? user.last_name[0].toUpperCase() : "";
      return `${firstInitial}${lastInitial}` || "U";
    }

    if (user.name) {
      const nameParts = user.name.split(" ");
      if (nameParts.length >= 2) {
        return `${nameParts[0][0]}${nameParts[nameParts.length - 1][0]}`.toUpperCase();
      }
      return user.name[0].toUpperCase();
    }

    return user.email[0].toUpperCase();
  }, [user]);

  // Get user role badge
  const getUserRoleBadge = useCallback(() => {
    if (!user) return "";

    if (permissions.isSuperuser()) return "Super Admin";
    if (permissions.isAdmin()) return "Admin";
    if (permissions.isManager()) return "Manager";

    return user.role?.charAt(0).toUpperCase() + user.role?.slice(1) || "User";
  }, [user, permissions]);

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

  // Show loading state while permissions are loading
  if (permissions.isLoading) {
    return (
      <div className="w-72 h-screen bg-background border-r border-border">
        <div className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-16 bg-gray-200 rounded" />
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="h-10 bg-gray-200 rounded" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-72 h-screen overflow-y-auto fixed left-0 top-0 z-10 bg-background border-r border-border">
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
          {visibleMenuItems.map((item) => (
            <div key={item.id}>
              <div
                className={cn(
                  "flex items-center justify-between w-full px-3 py-2.5 text-sm rounded-lg transition-colors cursor-pointer",
                  isItemActive(item)
                    ? "bg-primary text-primary-foreground"
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
                  <div className="absolute left-[-16px] top-[-4px] bottom-[14px] w-px bg-border"></div>

                  {item.children.map((child, idx) => (
                    <div key={idx} className="relative">
                      <div className="absolute left-[-16px] top-[14px] w-4 h-4">
                        <div className="w-full h-full border-l border-b border-border rounded-bl-md border-r-0 border-t-0"></div>
                      </div>
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
                            ? "bg-primary text-primary-foreground font-medium"
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
            className="flex items-center justify-between px-3 py-2 rounded-lg bg-card cursor-pointer hover:bg-muted transition-colors shadow-sm border border-border"
            onClick={handleProfileMenuToggle}
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground text-sm font-medium">
                {getUserInitials()}
              </div>
              <div className="text-sm">
                <div className="font-medium text-foreground">{getUserDisplayName()}</div>
                <div className="text-xs text-muted-foreground">{getUserRoleBadge()}</div>
              </div>
            </div>
            <div className="flex items-center">
              {profileMenuOpen ? (
                <ChevronUp className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              )}
            </div>
          </div>

          {/* Profile Dropdown Menu */}
          {profileMenuOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-2 bg-popover rounded-lg shadow-lg border border-border z-50">
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
                  <span>Profile Settings</span>
                </a>

                {permissions.hasPermission('api.view_documentation') && (
                  <>
                    <hr className="my-1 border-border" />
                    <div className="px-2 py-1">
                      <div className="text-xs font-medium text-muted-foreground px-2 mb-1">Developer</div>
                      <a
                        onClick={(e) => {
                          e.preventDefault();
                          handleNavigation("/dashboard/api-docs");
                        }}
                        href="/dashboard/api-docs"
                        className="flex items-center gap-3 px-4 py-2 text-sm text-popover-foreground hover:bg-accent hover:text-accent-foreground transition-colors rounded-md cursor-pointer"
                      >
                        <FileText className="w-4 h-4" />
                        <span>API Documentation</span>
                      </a>
                    </div>
                  </>
                )}

                <hr className="my-1 border-border" />
                <button
                  onClick={() => setShowSignOutModal(true)}
                  className="flex items-center gap-3 px-4 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors w-full text-left"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
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
                <span className="text-muted-foreground/50">Loading version...</span>
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

PermissionAwareSidebar.displayName = 'PermissionAwareSidebar';

export default PermissionAwareSidebar;
