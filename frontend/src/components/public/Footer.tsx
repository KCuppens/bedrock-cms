import React from 'react';
import { Link } from 'react-router-dom';
import { MenuItem } from '@/hooks/useSiteSettings';

interface FooterProps {
  footerItems: MenuItem[];
  siteName?: string;
  homeUrl?: string;
}

const Footer: React.FC<FooterProps> = ({
  footerItems,
  siteName = 'Your Site',
  homeUrl = '/'
}) => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:py-16 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Site Info */}
          <div className="col-span-1 md:col-span-2">
            <Link
              to={homeUrl}
              className="text-xl font-bold text-white hover:text-gray-300"
            >
              {siteName}
            </Link>
            <p className="mt-2 text-sm text-gray-400 max-w-md">
              Building amazing digital experiences with modern technology.
            </p>
          </div>

          {/* Quick Links */}
          {footerItems.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
                Quick Links
              </h3>
              <ul className="mt-4 space-y-2">
                {footerItems.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={item.path}
                      className="text-sm text-gray-400 hover:text-white transition-colors"
                    >
                      {item.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Contact Info or Additional Links */}
          <div>
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
              Contact
            </h3>
            <div className="mt-4 space-y-2">
              <p className="text-sm text-gray-400">
                Get in touch with us for more information about our services.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="mt-12 border-t border-gray-800 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <p className="text-sm text-gray-400">
              © {currentYear} {siteName}. All rights reserved.
            </p>

            {/* Additional Footer Links */}
            <div className="mt-4 md:mt-0">
              <div className="flex space-x-6">
                <Link
                  to="/privacy"
                  className="text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Privacy Policy
                </Link>
                <Link
                  to="/terms"
                  className="text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Terms of Service
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;