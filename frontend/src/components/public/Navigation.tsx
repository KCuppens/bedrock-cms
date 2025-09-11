import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { MenuItem } from '@/hooks/useSiteSettings';
import { Menu, X, ChevronDown } from 'lucide-react';
import SimpleLanguageSelector from '@/components/SimpleLanguageSelector';

interface NavigationProps {
  menuItems: MenuItem[];
  siteName?: string;
  homeUrl?: string;
}

const Navigation: React.FC<NavigationProps> = ({ 
  menuItems, 
  siteName = 'Your Site',
  homeUrl = '/'
}) => {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<number | null>(null);

  const isActiveLink = (path: string) => {
    return location.pathname === path;
  };

  const hasChildren = (item: MenuItem) => {
    return item.children && item.children.length > 0;
  };

  const toggleDropdown = (itemId: number) => {
    setOpenDropdown(openDropdown === itemId ? null : itemId);
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
    setOpenDropdown(null);
  };

  return (
    <nav className="bg-white shadow-sm border-b sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo/Site Name */}
          <div className="flex items-center">
            <Link 
              to={homeUrl} 
              className="flex-shrink-0 font-bold text-xl text-gray-900 hover:text-gray-700"
            >
              {siteName}
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            {menuItems.map((item) => (
              <div key={item.id} className="relative group">
                {hasChildren(item) ? (
                  <div className="relative">
                    <button
                      className={cn(
                        "flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                        isActiveLink(item.path)
                          ? "text-blue-600 bg-blue-50"
                          : "text-gray-700 hover:text-gray-900 hover:bg-gray-50"
                      )}
                      onClick={() => toggleDropdown(item.id)}
                    >
                      <span>{item.title}</span>
                      <ChevronDown className="h-4 w-4" />
                    </button>
                    
                    {/* Dropdown Menu */}
                    <div className="absolute left-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
                      <div className="py-1">
                        {item.children?.map((child) => (
                          <Link
                            key={child.id}
                            to={child.path}
                            className={cn(
                              "block px-4 py-2 text-sm transition-colors",
                              isActiveLink(child.path)
                                ? "text-blue-600 bg-blue-50"
                                : "text-gray-700 hover:text-gray-900 hover:bg-gray-50"
                            )}
                          >
                            {child.title}
                          </Link>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <Link
                    to={item.path}
                    className={cn(
                      "px-3 py-2 rounded-md text-sm font-medium transition-colors",
                      isActiveLink(item.path)
                        ? "text-blue-600 bg-blue-50"
                        : "text-gray-700 hover:text-gray-900 hover:bg-gray-50"
                    )}
                  >
                    {item.title}
                  </Link>
                )}
              </div>
            ))}
            
            {/* Language Selector */}
            <div className="ml-4">
              <SimpleLanguageSelector />
            </div>
          </div>

          {/* Mobile menu button and Language Selector */}
          <div className="md:hidden flex items-center gap-2">
            <SimpleLanguageSelector />
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 hover:text-gray-900 hover:bg-gray-100"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t">
            <div className="px-2 pt-2 pb-3 space-y-1 bg-white">
              {menuItems.map((item) => (
                <div key={item.id}>
                  {hasChildren(item) ? (
                    <div>
                      <button
                        onClick={() => toggleDropdown(item.id)}
                        className={cn(
                          "w-full flex items-center justify-between px-3 py-2 rounded-md text-base font-medium transition-colors text-left",
                          isActiveLink(item.path)
                            ? "text-blue-600 bg-blue-50"
                            : "text-gray-700 hover:text-gray-900 hover:bg-gray-50"
                        )}
                      >
                        <span>{item.title}</span>
                        <ChevronDown 
                          className={cn(
                            "h-4 w-4 transition-transform",
                            openDropdown === item.id ? "rotate-180" : ""
                          )} 
                        />
                      </button>
                      
                      {openDropdown === item.id && item.children && (
                        <div className="ml-4 space-y-1">
                          {item.children.map((child) => (
                            <Link
                              key={child.id}
                              to={child.path}
                              onClick={closeMobileMenu}
                              className={cn(
                                "block px-3 py-2 rounded-md text-sm transition-colors",
                                isActiveLink(child.path)
                                  ? "text-blue-600 bg-blue-50"
                                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                              )}
                            >
                              {child.title}
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <Link
                      to={item.path}
                      onClick={closeMobileMenu}
                      className={cn(
                        "block px-3 py-2 rounded-md text-base font-medium transition-colors",
                        isActiveLink(item.path)
                          ? "text-blue-600 bg-blue-50"
                          : "text-gray-700 hover:text-gray-900 hover:bg-gray-50"
                      )}
                    >
                      {item.title}
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navigation;