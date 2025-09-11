import React, { useState, useEffect, useMemo, useCallback, memo } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { useTranslation } from "@/contexts/TranslationContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Plus, MoreHorizontal, Mail, Shield, Clock, Trash2 } from "lucide-react";
import TopNavbar from "@/components/TopNavbar";
import Sidebar from "@/components/Sidebar";

const UsersRoles = memo(() => {
  const { t } = useTranslation();
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [editUserDialogOpen, setEditUserDialogOpen] = useState(false);
  const [deleteUserDialogOpen, setDeleteUserDialogOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<any>(null);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [userToDelete, setUserToDelete] = useState<any>(null);
  const [roleToDelete, setRoleToDelete] = useState<any>(null);
  const [deleteRoleDialogOpen, setDeleteRoleDialogOpen] = useState(false);
  const [editUserForm, setEditUserForm] = useState<any>({});
  const [isUpdatingUser, setIsUpdatingUser] = useState(false);
  const [isDeletingUser, setIsDeletingUser] = useState(false);
  const [isDeletingRole, setIsDeletingRole] = useState(false);
  const [openDropdownId, setOpenDropdownId] = useState<number | null>(null);
  const [isSavingRole, setIsSavingRole] = useState(false);
  
  // Resend invite states
  const [resendInviteDialogOpen, setResendInviteDialogOpen] = useState(false);
  const [selectedUserForInvite, setSelectedUserForInvite] = useState<any>(null);
  const [isResendingInvite, setIsResendingInvite] = useState(false);
  
  // API data states
  const [users, setUsers] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [permissions, setPermissions] = useState<any[]>([]);
  const [locales, setLocales] = useState<any[]>([]);
  const [scopes, setScopes] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  // Memoized function to extract user role IDs
  const extractUserRoleIds = useCallback((user: any, roles: any[]) => {
    const userRoles = user.roles || user.groups || user.user_permissions || [];
    
    const currentRoleIds = userRoles.map((r: any) => {
      // Handle different API response formats
      if (typeof r === 'object') {
        // If it's a role object with ID
        if (r.id) return r.id;
        // If it's a role object with role_id
        if (r.role_id) return r.role_id;
        // If it's a group object
        if (r.group && r.group.id) return r.group.id;
      }
      // If it's a string (role name), find the corresponding role ID
      if (typeof r === 'string') {
        const role = roles.find((role: any) => 
          role.name === r || role.name.toLowerCase() === r.toLowerCase()
        );
        return role ? role.id : null;
      }
      return null;
    }).filter((id: any) => id !== null && id !== undefined);
    
    return currentRoleIds;
  }, []);

  // Fetch data from API
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Fetch all data in parallel
        const [usersResponse, rolesResponse, permissionsResponse, localesResponse, scopesResponse] = await Promise.all([
          api.userManagement.users.list(),
          api.userManagement.roles.list(),
          api.userManagement.permissions.list(),
          api.i18n.locales.list(),
          api.userManagement.scopes()
        ]);

        setUsers(usersResponse.results || []);
        setRoles(rolesResponse.results || []);
        setPermissions(permissionsResponse.results || []);
        setLocales(localesResponse.results || []);
        setScopes(scopesResponse.data || []);
      } catch (error) {
        console.error('Failed to fetch data:', error);
        toast({
          title: "Error",
          description: "Failed to load users and roles data. Please try again.",
          variant: "destructive",
        });
        // Set default empty arrays on error
        setUsers([]);
        setRoles([]);
        setPermissions([]);
        setLocales([]);
        setScopes([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [toast]);
  
  // Dynamically build permission categories and actions from fetched permissions
  const getPermissionMatrix = () => {
    const matrix: Record<string, Set<string>> = {};
    const actionMap: Record<string, string> = {
      'add': 'create',
      'view': 'read',
      'change': 'update',
      'delete': 'delete',
      'publish': 'publish'
    };
    
    permissions.forEach((perm: any) => {
      const contentType = perm.content_type_display || perm.content_type;
      if (!matrix[contentType]) {
        matrix[contentType] = new Set();
      }
      
      // Extract action from codename (e.g., 'add_page' -> 'add')
      const parts = perm.codename.split('_');
      const action = parts[0];
      const mappedAction = actionMap[action] || action;
      matrix[contentType].add(mappedAction);
    });
    
    return matrix;
  };
  
  const permissionMatrix = getPermissionMatrix();
  const permissionCategories = Object.keys(permissionMatrix).sort();
  const permissionActions = ['create', 'read', 'update', 'delete', 'publish']; // Keep standard order

  // Form states for invite dialog
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("");
  const [isInviting, setIsInviting] = useState(false);

  const handleInviteUser = async () => {
    if (!inviteEmail || !inviteRole) {
      toast({
        title: "Error",
        description: "Please fill in all fields",
        variant: "destructive",
      });
      return;
    }

    setIsInviting(true);
    try {
      await api.userManagement.users.invite({
        email: inviteEmail,
        roles: [parseInt(inviteRole)]  // Use 'roles' field for multiple role IDs
      });
      
      toast({
        title: "Success",
        description: `Invitation sent to ${inviteEmail}`,
      });
      
      // Refresh users list
      const usersResponse = await api.userManagement.users.list();
      setUsers(usersResponse.results || []);
      
      setInviteDialogOpen(false);
      setInviteEmail("");
      setInviteRole("");
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send invitation. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsInviting(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;

    setIsDeletingUser(true);
    try {
      await api.userManagement.users.delete(userToDelete.id);
      
      toast({
        title: "Success",
        description: `User ${userToDelete.email} has been deleted.`,
      });
      
      // Refresh users list
      const usersResponse = await api.userManagement.users.list();
      setUsers(usersResponse.results || []);
      
      // Close dialog
      setDeleteUserDialogOpen(false);
      setUserToDelete(null);
    } catch (error: any) {
      console.error('Failed to delete user:', error);
      toast({
        title: "Error",
        description: error?.response?.data?.error || "Failed to delete user.",
        variant: "destructive",
      });
    } finally {
      setIsDeletingUser(false);
    }
  };

  const handleDeleteRole = async () => {
    if (!roleToDelete) return;

    setIsDeletingRole(true);
    try {
      await api.userManagement.roles.delete(roleToDelete.id);
      
      toast({
        title: "Success",
        description: `Role "${roleToDelete.name}" has been deleted.`,
      });
      
      // Refresh roles list
      const rolesResponse = await api.userManagement.roles.list();
      setRoles(rolesResponse.results || []);
      
      // Close dialog
      setDeleteRoleDialogOpen(false);
      setRoleToDelete(null);
    } catch (error: any) {
      console.error('Failed to delete role:', error);
      toast({
        title: "Error",
        description: error?.response?.data?.error || "Failed to delete role.",
        variant: "destructive",
      });
    } finally {
      setIsDeletingRole(false);
    }
  };

  const handleResendInvite = async () => {
    if (!selectedUserForInvite) return;

    setIsResendingInvite(true);
    try {
      await api.userManagement.users.invite({
        email: selectedUserForInvite.email,
        resend: true  // Flag to indicate this is a resend
      });
      
      toast({
        title: "Success",
        description: `Invite has been resent to ${selectedUserForInvite.email}`,
      });
      
      // Close dialog and reset state
      setResendInviteDialogOpen(false);
      setSelectedUserForInvite(null);
    } catch (error: any) {
      console.error('Failed to resend invite:', error);
      toast({
        title: "Error",
        description: error?.response?.data?.error || "Failed to resend invite.",
        variant: "destructive",
      });
    } finally {
      setIsResendingInvite(false);
    }
  };


  const generateRolePreview = (role: any) => {
    const actions = [];
    
    // If permissions is an array (backend format)
    if (Array.isArray(role.permissions)) {
      const grouped: Record<string, string[]> = {};
      
      role.permissions.forEach((perm: any) => {
        const contentType = perm.content_type || 'unknown';
        if (!grouped[contentType]) {
          grouped[contentType] = [];
        }
        
        // Extract and format the action
        const parts = perm.codename.split('_');
        const action = parts[0];
        const actionMap: Record<string, string> = {
          'add': 'create',
          'view': 'read',
          'change': 'update',
          'delete': 'delete',
          'publish': 'publish'
        };
        const mappedAction = actionMap[action] || action;
        grouped[contentType].push(mappedAction);
      });
      
      // Format grouped permissions
      Object.entries(grouped).forEach(([contentType, perms]) => {
        if (perms.length > 0) {
          actions.push(`${perms.join('/')} ${contentType}`);
        }
      });
    } else if (typeof role.permissions === 'object' && role.permissions) {
      // UI format (object structure)
      Object.entries(role.permissions).forEach(([category, perms]: [string, any]) => {
        const categoryActions = [];
        if (perms && typeof perms === 'object') {
          Object.entries(perms).forEach(([action, enabled]) => {
            if (enabled) categoryActions.push(action);
          });
        }
        if (categoryActions.length > 0) {
          actions.push(`${categoryActions.join('/')} ${category}`);
        }
      });
    }

    const locales = role.locale_scopes?.length 
      ? `[${role.locale_scopes.map((ls: any) => ls.code || ls).join(", ")}]` 
      : "[all locales]";

    return actions.length > 0 
      ? `This role can: ${actions.join(", ")} in ${locales}`
      : `This role has no specific permissions configured`;
  };

  return (
    <TooltipProvider>
      <div className="min-h-screen">
        <div className="flex">
          <Sidebar />
          
          <div className="flex-1 flex flex-col ml-72">
            <TopNavbar />
          
          <main className="flex-1 p-8">
            <div className="max-w-7xl mx-auto">
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-foreground mb-2">{t('users_roles.title', 'Users & Roles')}</h1>
                <p className="text-muted-foreground">Manage user access and permissions</p>
              </div>

              <Tabs defaultValue="users" className="space-y-6">
                <TabsList className="grid w-full grid-cols-2 max-w-md">
                  <TabsTrigger value="users">{t('users_roles.tabs.users', 'Users')}</TabsTrigger>
                  <TabsTrigger value="roles">{t('users_roles.tabs.roles', 'Roles (Groups)')}</TabsTrigger>
                </TabsList>

                <TabsContent value="users" className="space-y-6">
                  <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Users
                </CardTitle>
                <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
                  <DialogTrigger asChild>
                    <Button>
                      <Plus className="h-4 w-4 mr-2" />
                      Invite User
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Invite New User</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="email">Email Address</Label>
                        <Input 
                          id="email" 
                          type="email" 
                          placeholder="user@example.com"
                          value={inviteEmail}
                          onChange={(e) => setInviteEmail(e.target.value)}
                          disabled={isInviting}
                        />
                      </div>
                      <div>
                        <Label htmlFor="role">Role</Label>
                        <Select value={inviteRole} onValueChange={setInviteRole} disabled={isInviting}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select a role" />
                          </SelectTrigger>
                          <SelectContent>
                            {roles.map(role => (
                              <SelectItem key={role.id} value={String(role.id)}>
                                {role.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex gap-2">
                        <Button 
                          type="button"
                          className="flex-1" 
                          onClick={handleInviteUser}
                          disabled={isInviting}
                        >
                          <Mail className="h-4 w-4 mr-2" />
                          {isInviting ? "Sending..." : "Send Invite"}
                        </Button>
                        <Button 
                          type="button"
                          variant="outline" 
                          onClick={() => {
                            setInviteDialogOpen(false);
                            setInviteEmail("");
                            setInviteRole("");
                          }}
                          disabled={isInviting}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Roles</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Seen</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {isLoading ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8">
                          <div className="flex items-center justify-center">
                            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mr-2" />
                            Loading users...
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : users.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                          No users found. Invite your first user to get started.
                        </TableCell>
                      </TableRow>
                    ) : (
                      users.map(user => (
                        <TableRow key={user.id}>
                          <TableCell className="font-medium">
                            {user.first_name && user.last_name 
                              ? `${user.first_name} ${user.last_name}`
                              : user.username || user.email}
                          </TableCell>
                          <TableCell className="text-muted-foreground">{user.email}</TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              {(user.roles || user.groups || []).map((role: any) => (
                                <Badge key={role.id || role} variant="secondary" className="text-xs">
                                  {typeof role === 'string' ? role : role.name}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Badge 
                                variant={user.is_active ? "default" : "secondary"}
                                className={user.is_active ? "bg-green-100 text-green-800" : ""}
                              >
                                {user.is_active ? "Active" : "Inactive"}
                              </Badge>
                              {!user.is_active && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    setSelectedUserForInvite(user);
                                    setResendInviteDialogOpen(true);
                                  }}
                                  title="Resend invite email"
                                >
                                  <Mail className="h-3 w-3" />
                                </Button>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {user.last_seen 
                                ? new Date(user.last_seen).toLocaleString()
                                : "Never"}
                            </div>
                          </TableCell>
                        <TableCell>
                          <DropdownMenu 
                            open={openDropdownId === user.id} 
                            onOpenChange={(open) => setOpenDropdownId(open ? user.id : null)}
                          >
                            <DropdownMenuTrigger asChild>
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => console.log('Dropdown clicked for user:', user.id)}
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="bg-background border shadow-md z-50">
                              <DropdownMenuItem onClick={() => {
                                setSelectedUser(user);
                                
                                // Use memoized function to extract role IDs
                                const currentRoleIds = extractUserRoleIds(user, roles);
                                
                                setEditUserForm({
                                  first_name: user.first_name || '',
                                  last_name: user.last_name || '',
                                  email: user.email || '',
                                  is_active: user.is_active !== undefined ? user.is_active : true,
                                  role_ids: currentRoleIds
                                });
                                setEditUserDialogOpen(true);
                                setOpenDropdownId(null); // Close dropdown when opening dialog
                              }}>
                                Edit User
                              </DropdownMenuItem>
                              {user.is_superuser ? (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div>
                                      <DropdownMenuItem 
                                        disabled
                                        className="text-muted-foreground cursor-not-allowed"
                                      >
                                        <Trash2 className="w-4 h-4 mr-2" />
                                        Delete User
                                      </DropdownMenuItem>
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Cannot delete superuser accounts</p>
                                  </TooltipContent>
                                </Tooltip>
                              ) : (
                                <DropdownMenuItem 
                                  className="text-destructive" 
                                  onClick={() => {
                                    console.log('Delete clicked for user:', user);
                                    setUserToDelete(user);
                                    setDeleteUserDialogOpen(true);
                                    setOpenDropdownId(null);
                                  }}>
                                  <Trash2 className="w-4 h-4 mr-2" />
                                  Delete User
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    )))
                    }
                  </TableBody>
                </Table>
              </CardContent>
                  </Card>

                  {/* Edit User Dialog */}
                  <Dialog open={editUserDialogOpen} onOpenChange={(open) => {
                    setEditUserDialogOpen(open);
                    if (!open) {
                      setEditUserForm({});
                      setSelectedUser(null);
                    }
                  }}>
                    <DialogContent className="bg-background border shadow-md z-50">
                      <DialogHeader>
                        <DialogTitle>Edit User: {selectedUser?.first_name} {selectedUser?.last_name || selectedUser?.email}</DialogTitle>
                      </DialogHeader>
                      {selectedUser && (
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <Label htmlFor="userFirstName">First Name</Label>
                              <Input 
                                id="userFirstName" 
                                value={editUserForm.first_name || ''}
                                onChange={(e) => setEditUserForm({...editUserForm, first_name: e.target.value})}
                                className="mt-1"
                                disabled={isUpdatingUser}
                              />
                            </div>
                            <div>
                              <Label htmlFor="userLastName">Last Name</Label>
                              <Input 
                                id="userLastName" 
                                value={editUserForm.last_name || ''}
                                onChange={(e) => setEditUserForm({...editUserForm, last_name: e.target.value})}
                                className="mt-1"
                                disabled={isUpdatingUser}
                              />
                            </div>
                          </div>
                          <div>
                            <Label htmlFor="userEmail">Email Address</Label>
                            <Input 
                              id="userEmail" 
                              type="email"
                              value={editUserForm.email || ''}
                              onChange={(e) => setEditUserForm({...editUserForm, email: e.target.value})}
                              className="mt-1"
                              disabled={isUpdatingUser}
                            />
                          </div>
                          <div>
                            <Label htmlFor="userStatus">Status</Label>
                            <Select 
                              value={editUserForm.is_active !== undefined ? (editUserForm.is_active ? 'active' : 'inactive') : 'active'}
                              onValueChange={(value) => setEditUserForm({...editUserForm, is_active: value === 'active'})}
                              disabled={isUpdatingUser}
                            >
                              <SelectTrigger className="mt-1">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent className="bg-background border shadow-md z-50">
                                <SelectItem value="active">Active</SelectItem>
                                <SelectItem value="inactive">Inactive</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label>Assigned Roles</Label>
                            <div className="mt-2 space-y-2 max-h-48 overflow-y-auto border rounded p-3">
                              {roles.length === 0 ? (
                                <p className="text-sm text-muted-foreground">No roles available</p>
                              ) : (
                                roles.map(role => {
                                  const isChecked = (editUserForm.role_ids || []).includes(role.id);
                                  console.log(`Role ${role.name} (ID: ${role.id}) - isChecked: ${isChecked}, current role_ids:`, editUserForm.role_ids);
                                  
                                  return (
                                    <div key={role.id} className="flex items-start space-x-2">
                                      <Checkbox 
                                        id={`role-${role.id}`}
                                        checked={isChecked}
                                        onCheckedChange={(checked) => {
                                          console.log(`Toggling role ${role.name} (ID: ${role.id}) to ${checked}`);
                                          const currentRoles = editUserForm.role_ids || [];
                                          let newRoleIds;
                                          
                                          if (checked) {
                                            newRoleIds = [...currentRoles, role.id];
                                          } else {
                                            newRoleIds = currentRoles.filter((id: number) => id !== role.id);
                                          }
                                          
                                          console.log('Setting new role IDs:', newRoleIds);
                                          setEditUserForm({...editUserForm, role_ids: newRoleIds});
                                        }}
                                        disabled={isUpdatingUser}
                                        className="mt-1"
                                      />
                                      <div className="flex-1">
                                        <Label htmlFor={`role-${role.id}`} className="text-sm font-medium cursor-pointer">
                                          {role.name}
                                          {isChecked && <span className="ml-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Selected</span>}
                                        </Label>
                                        {role.description && (
                                          <p className="text-xs text-muted-foreground mt-0.5">
                                            {role.description}
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })
                              )}
                            </div>
                          </div>
                          <div className="flex gap-2 pt-4">
                            <Button 
                              onClick={async () => {
                                setIsUpdatingUser(true);
                                try {
                                  const updatePromises = [];
                                  
                                  // Update basic user information if any field has changed
                                  const hasProfileChanges = 
                                    editUserForm.first_name !== selectedUser.first_name ||
                                    editUserForm.last_name !== selectedUser.last_name ||
                                    editUserForm.email !== selectedUser.email;
                                  
                                  if (hasProfileChanges) {
                                    const updateData = {
                                      first_name: editUserForm.first_name,
                                      last_name: editUserForm.last_name,
                                      email: editUserForm.email,
                                    };
                                    updatePromises.push(
                                      api.userManagement.users.update(selectedUser.id, updateData)
                                        .catch(err => {
                                          // If update fails due to throttling or missing endpoint, try alternative
                                          console.warn('User update failed, trying alternative:', err);
                                          // You could try an alternative endpoint here
                                          throw err;
                                        })
                                    );
                                  }
                                  
                                  // Update user status if changed
                                  if (editUserForm.is_active !== selectedUser.is_active) {
                                    if (editUserForm.is_active) {
                                      updatePromises.push(api.userManagement.users.reactivate(selectedUser.id));
                                    } else {
                                      updatePromises.push(api.userManagement.users.deactivate(selectedUser.id));
                                    }
                                  }
                                  
                                  // Update user roles if they have been modified
                                  const userRoles = selectedUser.roles || selectedUser.groups || selectedUser.user_permissions || [];
                                  const currentRoleIds = userRoles.map((r: any) => {
                                    if (typeof r === 'object') {
                                      if (r.id) return r.id;
                                      if (r.role_id) return r.role_id;
                                      if (r.group && r.group.id) return r.group.id;
                                    }
                                    if (typeof r === 'string') {
                                      const role = roles.find((role: any) => role.name === r || role.name.toLowerCase() === r.toLowerCase());
                                      return role ? role.id : null;
                                    }
                                    return null;
                                  }).filter((id: any) => id !== null && id !== undefined);
                                  
                                  const newRoleIds = editUserForm.role_ids || [];
                                  const rolesChanged = JSON.stringify(currentRoleIds.sort()) !== JSON.stringify(newRoleIds.sort());
                                  
                                  console.log('Role update check:', {
                                    currentRoleIds,
                                    newRoleIds,
                                    rolesChanged
                                  });
                                  
                                  if (rolesChanged) {
                                    console.log('Updating roles for user:', selectedUser.id, 'with roles:', newRoleIds);
                                    updatePromises.push(
                                      api.userManagement.users.updateRoles(selectedUser.id, newRoleIds)
                                        .then(() => console.log('Role update successful'))
                                        .catch(err => {
                                          console.error('Role update failed:', err);
                                          throw err;
                                        })
                                    );
                                  }
                                  
                                  // Execute all updates
                                  if (updatePromises.length > 0) {
                                    await Promise.all(updatePromises);
                                    
                                    toast({
                                      title: "Success",
                                      description: "User updated successfully",
                                    });
                                    
                                    // Refresh users list
                                    const usersResponse = await api.userManagement.users.list();
                                    setUsers(usersResponse.results || []);
                                    
                                    setEditUserDialogOpen(false);
                                    setEditUserForm({});
                                    setSelectedUser(null);
                                  } else {
                                    toast({
                                      title: "Info",
                                      description: "No changes to save",
                                    });
                                  }
                                } catch (error: any) {
                                  console.error('Failed to update user:', error);
                                  
                                  // Check if it's a throttling error
                                  if (error?.message?.includes('throttle') || error?.message?.includes('No default throttle rate')) {
                                    toast({
                                      title: "Warning",
                                      description: "Some updates may have been rate limited. Please try again in a moment.",
                                      variant: "destructive",
                                    });
                                  } else {
                                    toast({
                                      title: "Error",
                                      description: error?.message || "Failed to update user. Please try again.",
                                      variant: "destructive",
                                    });
                                  }
                                } finally {
                                  setIsUpdatingUser(false);
                                }
                              }}
                              disabled={isUpdatingUser}
                            >
                              {isUpdatingUser ? "Saving..." : "Save Changes"}
                            </Button>
                            <Button 
                              variant="outline" 
                              onClick={() => {
                                setEditUserDialogOpen(false);
                                setEditUserForm({});
                                setSelectedUser(null);
                              }}
                              disabled={isUpdatingUser}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      )}
                    </DialogContent>
                  </Dialog>

                  {/* Delete User Confirmation Dialog */}
                  <AlertDialog open={deleteUserDialogOpen} onOpenChange={setDeleteUserDialogOpen}>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                          <Trash2 className="w-5 h-5 text-destructive" />
                          Delete User
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to permanently delete <strong>{userToDelete?.email}</strong>?
                          <br />
                          <br />
                          This action cannot be undone. The user will lose access to all their data and will need to be re-invited to regain access.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel disabled={isDeletingUser}>
                          Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={handleDeleteUser}
                          disabled={isDeletingUser}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          {isDeletingUser ? "Deleting..." : "Delete User"}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>

                  {/* Resend Invite Dialog */}
                  <Dialog open={resendInviteDialogOpen} onOpenChange={(open) => {
                    setResendInviteDialogOpen(open);
                    if (!open) {
                      setSelectedUserForInvite(null);
                    }
                  }}>
                    <DialogContent className="bg-background border shadow-md z-50">
                      <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                          <Mail className="w-5 h-5 text-primary" />
                          Resend Invite
                        </DialogTitle>
                      </DialogHeader>
                      {selectedUserForInvite && (
                        <div className="space-y-4">
                          <div className="text-sm text-muted-foreground">
                            Resending invite to <strong>{selectedUserForInvite.email}</strong>
                          </div>
                          <div className="flex gap-2">
                            <Button 
                              onClick={handleResendInvite}
                              disabled={isResendingInvite}
                              className="flex-1"
                            >
                              <Mail className="h-4 w-4 mr-2" />
                              {isResendingInvite ? "Sending..." : "Resend Invite"}
                            </Button>
                            <Button 
                              variant="outline"
                              onClick={() => {
                                setResendInviteDialogOpen(false);
                                setSelectedUserForInvite(null);
                              }}
                              disabled={isResendingInvite}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      )}
                    </DialogContent>
                  </Dialog>
                </TabsContent>

                <TabsContent value="roles" className="space-y-6">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        <Shield className="h-5 w-5" />
                        Roles (Groups)
                      </CardTitle>
                      <Button onClick={() => {
                        setSelectedRole({
                          id: null,
                          name: '',
                          description: '',
                          permissions: {},  // Initialize as empty object for UI format
                          locale_scope_ids: []
                        });
                        setRoleDialogOpen(true);
                      }}>
                        <Plus className="h-4 w-4 mr-2" />
                        Create Role
                      </Button>
                    </CardHeader>
                  </Card>
                  <div className="grid gap-6">
                    {isLoading ? (
                      <Card>
                        <CardContent className="py-8">
                          <div className="flex items-center justify-center">
                            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent mr-2" />
                            Loading roles...
                          </div>
                        </CardContent>
                      </Card>
                    ) : roles.length === 0 ? (
                      <Card>
                        <CardContent className="py-8 text-center text-muted-foreground">
                          No roles found. Create your first role to manage permissions.
                        </CardContent>
                      </Card>
                    ) : (
                      roles.map(role => (
                        <Card key={role.id}>
                          <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                              <CardTitle className="flex items-center gap-2">
                                {role.name}
                                <Badge variant="outline">{role.user_count || 0} users</Badge>
                              </CardTitle>
                              <p className="text-sm text-muted-foreground mt-1">{role.description || "No description"}</p>
                            </div>
                            <div className="flex gap-2">
                              <Button 
                                variant="outline" 
                                onClick={() => {
                                  // Convert role permissions from backend format to UI format
                                  const uiPermissions: Record<string, Record<string, boolean>> = {};
                                  
                                  if (Array.isArray(role.permissions)) {
                                    role.permissions.forEach((perm: any) => {
                                      const contentType = perm.content_type || 'unknown';
                                      if (!uiPermissions[contentType]) {
                                        uiPermissions[contentType] = {};
                                      }
                                      
                                      // Map backend action to UI action
                                      const actionMap: Record<string, string> = {
                                        'add': 'create',
                                        'view': 'read',
                                        'change': 'update',
                                        'delete': 'delete',
                                        'publish': 'publish'
                                      };
                                      
                                      const parts = perm.codename.split('_');
                                      const action = parts[0];
                                      const mappedAction = actionMap[action] || action;
                                      
                                      uiPermissions[contentType][mappedAction] = true;
                                    });
                                  }
                                  
                                  setSelectedRole({
                                    ...role,
                                    permissions: uiPermissions,
                                    locale_scope_ids: role.locale_scopes?.map((ls: any) => ls.id) || []
                                  });
                                  setRoleDialogOpen(true);
                                }}
                              >
                                Edit Role
                              </Button>
                              {/* Only show delete button if role has no users assigned */}
                              {(role.user_count === 0 || role.user_count === undefined) ? (
                                <Button 
                                  variant="outline" 
                                  size="sm"
                                  className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
                                  onClick={() => {
                                    setRoleToDelete(role);
                                    setDeleteRoleDialogOpen(true);
                                  }}
                                >
                                  <Trash2 className="h-4 w-4 mr-1" />
                                  Delete
                                </Button>
                              ) : (
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <div>
                                        <Button 
                                          variant="outline" 
                                          size="sm"
                                          disabled
                                          className="text-muted-foreground cursor-not-allowed"
                                        >
                                          <Trash2 className="h-4 w-4 mr-1" />
                                          Delete
                                        </Button>
                                      </div>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <p>Cannot delete role with assigned users ({role.user_count} users)</p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              )}
                            </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="p-3 bg-muted/50 rounded-lg">
                      <p className="text-sm text-muted-foreground">
                        {generateRolePreview(role)}
                      </p>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <h4 className="font-medium mb-2">Permissions</h4>
                        <div className="space-y-2">
                          {Array.isArray(role.permissions) ? (
                            // New API structure - permissions as array
                            <div className="flex flex-wrap gap-1">
                              {role.permissions.map((perm: any) => (
                                <Badge 
                                  key={perm.id || perm.codename}
                                  variant="default" 
                                  className="text-xs bg-green-100 text-green-800"
                                >
                                  {perm.name || perm.codename}
                                </Badge>
                              ))}
                              {role.permissions.length === 0 && (
                                <span className="text-sm text-muted-foreground">No permissions assigned</span>
                              )}
                            </div>
                          ) : role.permissions && typeof role.permissions === 'object' ? (
                            // Old structure fallback
                            Object.entries(role.permissions).map(([category, perms]: [string, any]) => (
                              <div key={category} className="flex items-center gap-2">
                                <span className="text-sm capitalize min-w-20">{category}:</span>
                                <div className="flex gap-1">
                                  {Object.entries(perms).map(([action, allowed]: [string, any]) => (
                                    <Badge 
                                      key={action}
                                      variant={allowed ? "default" : "secondary"} 
                                      className={`text-xs ${allowed ? "bg-green-100 text-green-800" : ""}`}
                                    >
                                      {action}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            ))
                          ) : (
                            <span className="text-sm text-muted-foreground">No permissions configured</span>
                          )}
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="font-medium mb-2">Scopes</h4>
                        <div className="space-y-2">
                          <div>
                            <span className="text-sm text-muted-foreground">Locales:</span>
                            <div className="flex gap-1 mt-1">
                              {(role.locale_scopes || []).map((locale: any) => (
                                <Badge key={locale.id || locale.code || locale} variant="outline" className="text-xs">
                                  {locale.code || locale.name || locale}
                                </Badge>
                              ))}
                              {(!role.locale_scopes || role.locale_scopes.length === 0) && (
                                <span className="text-xs text-muted-foreground">All locales</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
                    )}
                  </div>

                  <Dialog open={roleDialogOpen} onOpenChange={(open) => {
                    setRoleDialogOpen(open);
                    if (!open) {
                      setSelectedRole(null);
                    }
                  }}>
              <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>{selectedRole?.id ? `Edit Role: ${selectedRole?.name}` : 'Create New Role'}</DialogTitle>
                </DialogHeader>
                {selectedRole && (
                  <div className="space-y-6">
                    {!selectedRole.id && (
                      <div>
                        <Label htmlFor="roleName">Role Name</Label>
                        <Input 
                          id="roleName" 
                          value={selectedRole.name || ''}
                          onChange={(e) => setSelectedRole({...selectedRole, name: e.target.value})}
                          placeholder="e.g., Content Editor"
                          className="mt-1"
                          disabled={isSavingRole}
                        />
                      </div>
                    )}
                    <div>
                      <Label htmlFor="description">Description</Label>
                      <Textarea 
                        id="description" 
                        value={selectedRole.description || ''}
                        onChange={(e) => setSelectedRole({...selectedRole, description: e.target.value})}
                        placeholder="Describe the purpose and responsibilities of this role"
                        className="mt-1"
                        disabled={isSavingRole}
                      />
                    </div>

                    <div>
                      <h3 className="font-medium mb-3">Permissions</h3>
                      <div className="border rounded-lg p-4">
                        {permissions.length === 0 ? (
                          <p className="text-sm text-muted-foreground text-center py-4">
                            Loading permissions from backend...
                          </p>
                        ) : (
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead colSpan={2}>Content Type</TableHead>
                                {permissionActions.map(action => (
                                  <TableHead key={action} className="text-center">
                                    <div className="flex flex-col items-center gap-1">
                                      <Checkbox
                                        checked={
                                          permissionCategories.length > 0 &&
                                          permissionCategories.every(category => 
                                            selectedRole.permissions?.[category]?.[action] === true
                                          )
                                        }
                                        onCheckedChange={(checked) => {
                                          const updatedPerms = {...(selectedRole.permissions || {})};
                                          permissionCategories.forEach(category => {
                                            if (!updatedPerms[category]) updatedPerms[category] = {};
                                            // Only set if this action exists for this category
                                            if (permissionMatrix[category]?.has(action)) {
                                              updatedPerms[category][action] = !!checked;
                                            }
                                          });
                                          setSelectedRole({...selectedRole, permissions: updatedPerms});
                                        }}
                                        aria-label={`Select all ${action}`}
                                        disabled={isSavingRole}
                                      />
                                      <span className="capitalize text-xs">{action}</span>
                                    </div>
                                  </TableHead>
                                ))}
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {permissionCategories.length === 0 ? (
                                <TableRow>
                                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                                    No permission categories available. Permissions may need to be configured in the backend.
                                  </TableCell>
                                </TableRow>
                              ) : (
                                permissionCategories.map(category => {
                                  const availableActions = permissionMatrix[category] || new Set();
                                  return (
                                    <TableRow key={category}>
                                      <TableCell className="w-8">
                                        <Checkbox
                                          checked={
                                            permissionActions.filter(action => availableActions.has(action))
                                              .every(action => selectedRole.permissions?.[category]?.[action] === true)
                                          }
                                          onCheckedChange={(checked) => {
                                            const updatedPerms = {...(selectedRole.permissions || {})};
                                            if (!updatedPerms[category]) updatedPerms[category] = {};
                                            permissionActions.forEach(action => {
                                              if (availableActions.has(action)) {
                                                updatedPerms[category][action] = !!checked;
                                              }
                                            });
                                            setSelectedRole({...selectedRole, permissions: updatedPerms});
                                          }}
                                          aria-label={`Select all ${category} permissions`}
                                          disabled={isSavingRole}
                                        />
                                      </TableCell>
                                      <TableCell className="font-medium">
                                        {category.charAt(0).toUpperCase() + category.slice(1)}
                                      </TableCell>
                                      {permissionActions.map(action => {
                                        const isAvailable = availableActions.has(action);
                                        return (
                                          <TableCell key={action} className="text-center">
                                            {isAvailable ? (
                                              <Checkbox 
                                                checked={selectedRole.permissions?.[category]?.[action] || false}
                                                onCheckedChange={(checked) => {
                                                  const updatedPerms = {...(selectedRole.permissions || {})};
                                                  if (!updatedPerms[category]) updatedPerms[category] = {};
                                                  updatedPerms[category][action] = checked;
                                                  setSelectedRole({...selectedRole, permissions: updatedPerms});
                                                }}
                                                disabled={isSavingRole || (category === "page" && action === "publish" && !selectedRole.permissions?.[category]?.update)}
                                              />
                                            ) : (
                                              <span className="text-muted-foreground">-</span>
                                            )}
                                          </TableCell>
                                        );
                                      })}
                                    </TableRow>
                                  );
                                })
                              )}
                            </TableBody>
                          </Table>
                        )}
                      </div>
                    </div>

                    <div>
                      <h3 className="font-medium mb-3">Locale Scopes</h3>
                      <div className="border rounded-lg p-4 space-y-2">
                        {locales
                          .sort((a, b) => {
                            // Sort active locales first, then by sort_order, then by name
                            if (a.is_active !== b.is_active) {
                              return b.is_active ? 1 : -1;
                            }
                            if (a.sort_order !== b.sort_order) {
                              return a.sort_order - b.sort_order;
                            }
                            return a.name.localeCompare(b.name);
                          })
                          .map(locale => (
                          <div key={locale.id} className="flex items-center space-x-2">
                            <Checkbox 
                              id={`locale-${locale.id}`}
                              checked={selectedRole.locale_scope_ids?.includes(locale.id) || false}
                              onCheckedChange={(checked) => {
                                const currentScopes = selectedRole.locale_scope_ids || [];
                                const updatedScopes = checked 
                                  ? [...currentScopes, locale.id]
                                  : currentScopes.filter((id: number) => id !== locale.id);
                                setSelectedRole({...selectedRole, locale_scope_ids: updatedScopes});
                              }}
                            />
                            <Label htmlFor={`locale-${locale.id}`} className={`text-sm font-medium ${!locale.is_active ? 'text-muted-foreground' : ''}`}>
                              {locale.name} ({locale.code.toUpperCase()})
                              {!locale.is_active && <span className="text-xs ml-1">(inactive)</span>}
                            </Label>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="p-4 bg-muted/50 rounded-lg">
                      <h4 className="font-medium mb-2">Role Preview</h4>
                      <p className="text-sm text-muted-foreground">
                        {generateRolePreview(selectedRole)}
                      </p>
                    </div>

                    <div className="flex gap-2">
                      <Button 
                        type="button"
                        onClick={async () => {
                        setIsSavingRole(true);
                        try {
                          // Validate role name for new roles
                          if (!selectedRole.id && !selectedRole.name?.trim()) {
                            toast({
                              title: "Error",
                              description: "Role name is required",
                              variant: "destructive",
                            });
                            return;
                          }
                          
                          // Convert permissions format for API
                          // Map permission structure to permission IDs based on available permissions
                          const permissionIds: number[] = [];
                          
                          console.log('Converting permissions for role save:', selectedRole.permissions);
                          console.log('Available permissions:', permissions);
                          
                          // Get permission IDs from the permissions state
                          // This maps our UI permission structure to actual permission IDs
                          if (selectedRole.permissions && typeof selectedRole.permissions === 'object') {
                            // For each category and action that is checked, find the corresponding permission
                            Object.entries(selectedRole.permissions).forEach(([category, actions]: [string, any]) => {
                              if (actions && typeof actions === 'object') {
                                Object.entries(actions).forEach(([action, enabled]) => {
                                  if (enabled) {
                                    console.log(`Looking for permission: ${category}.${action}`);
                                    
                                    // Find the permission that matches this category and action
                                    const permission = permissions.find((p: any) => {
                                      // Match based on codename pattern (e.g., 'add_page', 'change_page', etc.)
                                      const actionMap: Record<string, string> = {
                                        'create': 'add',
                                        'read': 'view',
                                        'update': 'change',
                                        'delete': 'delete',
                                        'publish': 'publish'
                                      };
                                      const mappedAction = actionMap[action] || action;
                                      
                                      // Get the content type from the permission
                                      const contentType = p.content_type_display || p.content_type;
                                      const codename = p.codename;
                                      
                                      // The key insight: the category from UI should match the contentType from the permission
                                      // Since getPermissionMatrix() creates categories from p.content_type_display
                                      const isMatchingContentType = contentType === category;
                                      const expectedCodename = `${mappedAction}_${contentType}`;
                                      const isMatchingAction = codename === expectedCodename;
                                      
                                      console.log(`  Checking permission ${codename} (content_type: ${contentType})`);
                                      console.log(`    Category match (${category} === ${contentType}): ${isMatchingContentType}`);
                                      console.log(`    Expected codename: ${expectedCodename}`);
                                      console.log(`    Action match: ${isMatchingAction}`);
                                      console.log(`    Both match: ${isMatchingContentType && isMatchingAction}`);
                                      
                                      return isMatchingContentType && isMatchingAction;
                                    });
                                    
                                    if (permission) {
                                      console.log(`  Found matching permission: ${permission.codename} (ID: ${permission.id})`);
                                      permissionIds.push(permission.id);
                                    } else {
                                      console.log(`  No permission found for ${category}.${action}`);
                                    }
                                  }
                                });
                              }
                            });
                          }
                          
                          console.log('Final permission IDs to send:', permissionIds);
                          
                          if (selectedRole.id) {
                            // Update existing role
                            const updateData: any = {
                              name: selectedRole.name,
                              locale_scope_ids: selectedRole.locale_scope_ids || []
                            };
                            
                            await api.userManagement.roles.update(selectedRole.id, updateData);
                            
                            // Update permissions separately if we have permission IDs
                            if (permissionIds.length > 0 || selectedRole.permissions) {
                              await api.userManagement.roles.updatePermissions(selectedRole.id, permissionIds);
                            }
                            
                            toast({
                              title: "Success",
                              description: "Role updated successfully",
                            });
                          } else {
                            // Create new role
                            const createData: any = {
                              name: selectedRole.name,
                              locale_scope_ids: selectedRole.locale_scope_ids || []
                            };
                            
                            const response = await api.userManagement.roles.create(createData);
                            console.log('Role create response:', response);
                            
                            // Set permissions for the newly created role if we have any
                            if (permissionIds.length > 0) {
                              // The RoleSerializer returns the ID directly, not nested in data
                              const roleId = response.id;
                              console.log('Attempting to update permissions for role ID:', roleId);
                              console.log('Permission IDs to apply:', permissionIds);
                              
                              if (roleId) {
                                try {
                                  console.log('Making updatePermissions API call...');
                                  const permissionsResponse = await api.userManagement.roles.updatePermissions(roleId, permissionIds);
                                  console.log('Permissions updated successfully. Response:', permissionsResponse);
                                } catch (permissionError) {
                                  console.error('Failed to update permissions:', permissionError);
                                  // Still show success for role creation but warn about permissions
                                  toast({
                                    title: "Warning",
                                    description: "Role created but failed to set permissions. Please try editing the role to set permissions.",
                                    variant: "destructive",
                                  });
                                }
                              } else {
                                console.error('No role ID found in response:', response);
                                console.error('Full response structure:', JSON.stringify(response, null, 2));
                              }
                            } else {
                              console.log('No permissions to apply');
                            }
                            
                            toast({
                              title: "Success",
                              description: "Role created successfully",
                            });
                          }
                          
                          // Refresh roles list
                          const rolesResponse = await api.userManagement.roles.list();
                          setRoles(rolesResponse.results || []);
                          
                          setRoleDialogOpen(false);
                          setSelectedRole(null);
                        } catch (error: any) {
                          console.error('Failed to save role:', error);
                          toast({
                            title: "Error",
                            description: error?.message || `Failed to ${selectedRole.id ? 'update' : 'create'} role. Please try again.`,
                            variant: "destructive",
                          });
                        } finally {
                          setIsSavingRole(false);
                        }
                      }}
                      disabled={isSavingRole}
                      >
                        {isSavingRole ? 'Saving...' : (selectedRole.id ? 'Save Changes' : 'Create Role')}
                      </Button>
                      <Button 
                        type="button"
                        variant="outline" 
                        onClick={() => {
                          setRoleDialogOpen(false);
                          setSelectedRole(null);
                        }}
                        disabled={isSavingRole}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </DialogContent>
                  </Dialog>

                  {/* Delete Role Confirmation Dialog */}
                  <AlertDialog open={deleteRoleDialogOpen} onOpenChange={setDeleteRoleDialogOpen}>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                          <Trash2 className="w-5 h-5 text-destructive" />
                          Delete Role
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to permanently delete the role <strong>"{roleToDelete?.name}"</strong>?
                          <br />
                          <br />
                          This action cannot be undone. The role and all its permissions will be permanently removed from the system.
                          {roleToDelete?.user_count > 0 && (
                            <>
                              <br />
                              <br />
                              <span className="text-destructive font-medium">
                                Warning: This role is currently assigned to {roleToDelete.user_count} user(s). 
                                Please reassign these users to other roles before deleting this role.
                              </span>
                            </>
                          )}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel disabled={isDeletingRole}>
                          Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={handleDeleteRole}
                          disabled={isDeletingRole}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          {isDeletingRole ? "Deleting..." : "Delete Role"}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>

                </TabsContent>
              </Tabs>
            </div>
          </main>
        </div>
      </div>
      </div>
    </TooltipProvider>
  );
});

UsersRoles.displayName = 'UsersRoles';
export default UsersRoles;