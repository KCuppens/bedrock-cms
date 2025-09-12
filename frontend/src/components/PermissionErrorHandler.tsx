import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Component to handle global permission and auth errors
 * Listens for custom events dispatched by the API client
 */
export const PermissionErrorHandler: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  useEffect(() => {
    // Handle permission errors
    const handlePermissionError = (event: CustomEvent) => {
      const { message, url, data } = event.detail;

      // Show user-friendly error message
      if (data?.detail?.includes('locale')) {
        toast.error('You don\'t have access to content in this locale');
      } else if (data?.detail?.includes('section')) {
        toast.error('You don\'t have access to this section');
      } else if (data?.detail?.includes('permission')) {
        toast.error('You don\'t have permission to perform this action');
      } else {
        toast.error(message || 'Access denied');
      }

      // Optional: Log for debugging
      console.warn('Permission denied:', { url, message, data });
    };

    // Handle authentication errors
    const handleAuthError = () => {
      toast.error('Your session has expired. Please sign in again.');

      // Redirect to login page
      setTimeout(() => {
        logout();
        navigate('/sign-in', { replace: true });
      }, 1500);
    };

    // Add event listeners
    window.addEventListener('permission-error', handlePermissionError);
    window.addEventListener('auth-error', handleAuthError);

    // Cleanup
    return () => {
      window.removeEventListener('permission-error', handlePermissionError);
      window.removeEventListener('auth-error', handleAuthError);
    };
  }, [navigate, logout]);

  // This component doesn't render anything
  return null;
};

export default PermissionErrorHandler;