import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Role } from '@/types/api';
import { useToast } from '@/hooks/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, UserPlus, Shield } from 'lucide-react';

interface InviteUserModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const InviteUserModal: React.FC<InviteUserModalProps> = ({ 
  open, 
  onOpenChange,
  onSuccess 
}) => {
  const { toast } = useToast();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRoles, setSelectedRoles] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [errors, setErrors] = useState<{ email?: string }>({});

  // Fetch roles when modal opens
  useEffect(() => {
    if (open) {
      fetchRoles();
      // Reset form when modal opens
      resetForm();
    }
  }, [open]);

  const fetchRoles = async () => {
    try {
      setLoading(true);
      const response = await api.userManagement.roles.list();
      
      // Handle paginated response
      const roleList = response.results || [];
      setRoles(roleList);
    } catch (error) {
      console.error('Failed to fetch roles:', error);
      toast({
        title: 'Error',
        description: 'Failed to load roles. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setEmail('');
    setMessage('');
    setSelectedRoles([]);
    setErrors({});
  };

  const validateForm = (): boolean => {
    const newErrors: { email?: string } = {};
    
    if (!email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleRoleToggle = (roleId: number) => {
    setSelectedRoles(prev => 
      prev.includes(roleId) 
        ? prev.filter(id => id !== roleId)
        : [...prev, roleId]
    );
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      setSending(true);
      
      // Send invitation with multiple roles support
      const response = await api.userManagement.users.invite({
        email: email.trim(),
        roles: selectedRoles,  // Send array of role IDs
        message: message.trim() || undefined,
      });

      toast({
        title: 'Success',
        description: `Invitation sent to ${email}`,
      });

      // Close modal and trigger success callback
      onOpenChange(false);
      if (onSuccess) {
        onSuccess();
      }
    } catch (error: any) {
      console.error('Failed to invite user:', error);
      
      // Handle specific error cases
      if (error.message?.includes('already exists')) {
        setErrors({ email: 'A user with this email already exists' });
      } else {
        toast({
          title: 'Error',
          description: error.message || 'Failed to send invitation. Please try again.',
          variant: 'destructive',
        });
      }
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="w-5 h-5" />
            Invite New User
          </DialogTitle>
          <DialogDescription>
            Send an invitation email to add a new user to the system.
            They will receive a link to set up their account.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Email Field */}
          <div className="space-y-2">
            <Label htmlFor="email">
              Email Address <span className="text-red-500">*</span>
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (errors.email) {
                  setErrors({ ...errors, email: undefined });
                }
              }}
              className={errors.email ? 'border-red-500' : ''}
              disabled={sending}
            />
            {errors.email && (
              <p className="text-sm text-red-500">{errors.email}</p>
            )}
          </div>

          {/* Roles Selection */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Assign Roles (Optional)
            </Label>
            {loading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : roles.length === 0 ? (
              <p className="text-sm text-muted-foreground py-2">
                No roles available. Users can be assigned roles later.
              </p>
            ) : (
              <ScrollArea className="h-[150px] w-full rounded-md border p-3">
                <div className="space-y-2">
                  {roles.map((role) => (
                    <div key={role.id} className="flex items-start space-x-2">
                      <Checkbox
                        id={`role-${role.id}`}
                        checked={selectedRoles.includes(role.id)}
                        onCheckedChange={() => handleRoleToggle(role.id)}
                        disabled={sending}
                      />
                      <div className="flex-1">
                        <label
                          htmlFor={`role-${role.id}`}
                          className="text-sm font-medium leading-none cursor-pointer"
                        >
                          {role.name}
                        </label>
                        {role.user_count !== undefined && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {role.user_count} {role.user_count === 1 ? 'user' : 'users'}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
            {selectedRoles.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {selectedRoles.length} role{selectedRoles.length !== 1 ? 's' : ''} selected
              </p>
            )}
          </div>

          {/* Custom Message */}
          <div className="space-y-2">
            <Label htmlFor="message">
              Custom Message (Optional)
            </Label>
            <Textarea
              id="message"
              placeholder="Add a personal welcome message to the invitation email..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              disabled={sending}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground">
              This message will be included in the invitation email
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={sending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={sending || !email.trim()}
          >
            {sending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <UserPlus className="w-4 h-4 mr-2" />
                Send Invitation
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default InviteUserModal;