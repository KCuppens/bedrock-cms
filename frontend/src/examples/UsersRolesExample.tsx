import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api.ts';
import { User, Role } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import InviteUserModal from '@/components/modals/InviteUserModal';
import { UserPlus, Users, Shield, RefreshCw } from 'lucide-react';

/**
 * Example showing how to use the InviteUserModal with the user management API
 */
const UsersRolesExample: React.FC = () => {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingRoles, setLoadingRoles] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = () => {
    fetchUsers();
    fetchRoles();
  };

  const fetchUsers = async () => {
    try {
      setLoadingUsers(true);
      const response = await api.userManagement.users.list();
      setUsers(response.results || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      toast({
        title: 'Error',
        description: 'Failed to load users',
        variant: 'destructive',
      });
    } finally {
      setLoadingUsers(false);
    }
  };

  const fetchRoles = async () => {
    try {
      setLoadingRoles(true);
      const response = await api.userManagement.roles.list();
      setRoles(response.results || []);
    } catch (error) {
      console.error('Failed to fetch roles:', error);
      toast({
        title: 'Error',
        description: 'Failed to load roles',
        variant: 'destructive',
      });
    } finally {
      setLoadingRoles(false);
    }
  };

  const handleInviteSuccess = () => {
    // Refresh users list after successful invitation
    fetchUsers();
    toast({
      title: 'User Invited',
      description: 'The user list has been refreshed.',
    });
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Users & Roles Management</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={loadData}
            disabled={loadingUsers || loadingRoles}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowInviteModal(true)}>
            <UserPlus className="w-4 h-4 mr-2" />
            Invite User
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Users Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Users ({users.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingUsers ? (
              <p className="text-muted-foreground">Loading users...</p>
            ) : users.length === 0 ? (
              <p className="text-muted-foreground">No users found</p>
            ) : (
              <div className="space-y-2">
                {users.slice(0, 5).map((user) => (
                  <div
                    key={user.id}
                    className="flex justify-between items-center p-2 rounded hover:bg-accent"
                  >
                    <div>
                      <p className="font-medium">{user.email}</p>
                      <p className="text-sm text-muted-foreground">
                        {user.first_name} {user.last_name}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">
                        {user.is_active ? (
                          <span className="text-green-600">Active</span>
                        ) : (
                          <span className="text-red-600">Inactive</span>
                        )}
                      </p>
                    </div>
                  </div>
                ))}
                {users.length > 5 && (
                  <p className="text-sm text-muted-foreground text-center pt-2">
                    And {users.length - 5} more...
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Roles Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Roles ({roles.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingRoles ? (
              <p className="text-muted-foreground">Loading roles...</p>
            ) : roles.length === 0 ? (
              <p className="text-muted-foreground">No roles found</p>
            ) : (
              <div className="space-y-2">
                {roles.map((role) => (
                  <div
                    key={role.id}
                    className="flex justify-between items-center p-2 rounded hover:bg-accent"
                  >
                    <div>
                      <p className="font-medium">{role.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {role.permissions.length} permissions
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">
                        {role.user_count} {role.user_count === 1 ? 'user' : 'users'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Invite User Modal */}
      <InviteUserModal
        open={showInviteModal}
        onOpenChange={setShowInviteModal}
        onSuccess={handleInviteSuccess}
      />

      {/* Usage Instructions */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-lg">How to Use</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>1. Click "Invite User" to open the invitation modal</p>
          <p>2. The modal automatically fetches available roles</p>
          <p>3. Select multiple roles using checkboxes</p>
          <p>4. Add an optional welcome message</p>
          <p>5. The user receives an email with setup instructions</p>
          <div className="mt-4 p-3 bg-background rounded border">
            <p className="font-mono text-xs">
              {`// Import and use the modal`}<br/>
              {`import InviteUserModal from '@/components/modals/InviteUserModal';`}<br/>
              <br/>
              {`// In your component`}<br/>
              {`<InviteUserModal`}<br/>
              {`  open={showModal}`}<br/>
              {`  onOpenChange={setShowModal}`}<br/>
              {`  onSuccess={handleSuccess}`}<br/>
              {`/>`}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default UsersRolesExample;