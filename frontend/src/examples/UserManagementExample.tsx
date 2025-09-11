import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api.ts';
import { Role, UserInviteRequest } from '@/types/api';
import { useToast } from '@/hooks/use-toast';

/**
 * Example component showing how to use the user management endpoints
 * for inviting users and fetching roles.
 */
const UserManagementExample: React.FC = () => {
  const { toast } = useToast();
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  const [inviteMessage, setInviteMessage] = useState('');

  // Fetch all roles when component mounts
  useEffect(() => {
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    try {
      setLoading(true);
      const response = await api.userManagement.roles.list();
      
      // Handle paginated response
      if (response.results) {
        setRoles(response.results);
      } else {
        // In case the response is not paginated
        setRoles(response as any);
      }
      
      toast({
        title: "Roles loaded",
        description: `Loaded ${response.results?.length || 0} roles`,
      });
    } catch (error) {
      console.error('Failed to fetch roles:', error);
      toast({
        title: "Error",
        description: "Failed to fetch roles",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const inviteUser = async () => {
    if (!inviteEmail) {
      toast({
        title: "Error",
        description: "Please enter an email address",
        variant: "destructive",
      });
      return;
    }

    try {
      setLoading(true);
      
      const inviteData: UserInviteRequest = {
        email: inviteEmail,
        role: selectedRole || undefined,
        message: inviteMessage || undefined,
      };

      const response = await api.userManagement.users.invite(inviteData);
      
      toast({
        title: "User invited",
        description: response.data?.message || `Invitation sent to ${inviteEmail}`,
      });

      // Clear form
      setInviteEmail('');
      setSelectedRole('');
      setInviteMessage('');
    } catch (error: any) {
      console.error('Failed to invite user:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to invite user",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">User Management Example</h1>
      
      {/* Roles Section */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Available Roles</h2>
        {loading ? (
          <p>Loading roles...</p>
        ) : (
          <div className="space-y-2">
            {roles.length === 0 ? (
              <p className="text-gray-500">No roles available</p>
            ) : (
              roles.map(role => (
                <div key={role.id} className="p-3 border rounded">
                  <div className="font-medium">{role.name}</div>
                  <div className="text-sm text-gray-600">
                    {role.user_count} users • {role.permissions.length} permissions
                  </div>
                </div>
              ))
            )}
          </div>
        )}
        <button
          onClick={fetchRoles}
          disabled={loading}
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          Refresh Roles
        </button>
      </div>

      {/* Invite User Section */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Invite New User</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Email Address *
            </label>
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="user@example.com"
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Role (Optional)
            </label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">No role</option>
              {roles.map(role => (
                <option key={role.id} value={role.name}>
                  {role.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Custom Message (Optional)
            </label>
            <textarea
              value={inviteMessage}
              onChange={(e) => setInviteMessage(e.target.value)}
              placeholder="Welcome message for the invitation email..."
              rows={3}
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={inviteUser}
            disabled={loading || !inviteEmail}
            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            {loading ? 'Sending...' : 'Send Invitation'}
          </button>
        </div>
      </div>

      {/* Usage Notes */}
      <div className="mt-8 p-4 bg-gray-100 rounded">
        <h3 className="font-semibold mb-2">API Usage Notes:</h3>
        <ul className="text-sm space-y-1">
          <li>• <code>api.userManagement.roles.list()</code> - Fetch all roles</li>
          <li>• <code>api.userManagement.users.invite(data)</code> - Invite a new user</li>
          <li>• The invite endpoint sends an email with a setup link</li>
          <li>• Users are created as inactive until they complete setup</li>
        </ul>
      </div>
    </div>
  );
};

export default UserManagementExample;