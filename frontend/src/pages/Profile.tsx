import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import {
  Shield,
  Loader2,
  Save,
  AlertCircle,
  CheckCircle
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api.ts";
import { format } from "date-fns";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";

const Profile = () => {
  const navigate = useNavigate();
  const { user, isLoading: authLoading } = useAuth();
  const { toast } = useToast();

  // Profile form state
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState(false);

  // Password form state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  // Load user data
  useEffect(() => {
    if (user) {
      setFirstName(user.first_name || "");
      setLastName(user.last_name || "");
      setEmail(user.email || "");
    }
  }, [user]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError("");
    setProfileSuccess(false);
    setProfileLoading(true);

    try {
      const response = await api.accounts.updateProfile({
        first_name: firstName,
        last_name: lastName,
        email: email,
        name: `${firstName} ${lastName}`.trim(),
      });

      if (response) {
        setProfileSuccess(true);
        toast({
          title: "Profile Updated",
          description: "Your profile has been updated successfully.",
        });

        // Refresh user data after successful update
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.email?.[0] ||
                          error.response?.data?.detail ||
                          error.message ||
                          "Failed to update profile";
      setProfileError(errorMessage);
      toast({
        title: "Update Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setProfileLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");
    setPasswordSuccess(false);

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("All fields are required");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters long");
      return;
    }

    // Check for common password patterns
    if (newPassword === currentPassword) {
      setPasswordError("New password must be different from current password");
      return;
    }

    setPasswordLoading(true);

    try {
      const response = await api.accounts.changePassword({
        old_password: currentPassword,
        new_password1: newPassword,
        new_password2: confirmPassword,
      });

      if (response) {
        setPasswordSuccess(true);
        toast({
          title: "Password Changed",
          description: "Your password has been changed successfully. Please sign in again.",
        });

        // Clear form
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");

        // Redirect to sign in after password change
        setTimeout(() => {
          navigate("/sign-in");
        }, 2000);
      }
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.old_password?.[0] ||
        error.response?.data?.new_password2?.[0] ||
        error.response?.data?.non_field_errors?.[0] ||
        error.response?.data?.detail ||
        error.message ||
        "Failed to change password";

      setPasswordError(errorMessage);
      toast({
        title: "Password Change Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setPasswordLoading(false);
    }
  };

  const getInitials = () => {
    const first = firstName || user?.first_name || "";
    const last = lastName || user?.last_name || "";
    if (first && last) {
      return `${first[0]}${last[0]}`.toUpperCase();
    }
    return user?.email?.[0]?.toUpperCase() || "U";
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    navigate("/sign-in");
    return null;
  }

  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />

        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />

          <main className="flex-1 p-8">
            <div className="max-w-5xl mx-auto">
              {/* Header */}
              <div className="mb-8">
                <div className="flex items-center gap-4">
                  <Avatar className="w-20 h-20">
                    <AvatarImage src={user.avatar} />
                    <AvatarFallback className="text-lg font-medium">{getInitials()}</AvatarFallback>
                  </Avatar>
                  <div>
                    <h1 className="text-3xl font-bold text-foreground">Profile Settings</h1>
                    <p className="text-muted-foreground">
                      Manage your account settings and preferences
                    </p>
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile">
            <Card>
              <CardHeader>
                <CardTitle>Profile Information</CardTitle>
                <CardDescription>
                  Update your personal information and email address
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleProfileSubmit} className="space-y-4">
                  {profileError && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{profileError}</AlertDescription>
                    </Alert>
                  )}

                  {profileSuccess && (
                    <Alert className="border-green-200 bg-green-50 text-green-800">
                      <CheckCircle className="h-4 w-4" />
                      <AlertDescription>
                        Profile updated successfully
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="firstName">First Name</Label>
                      <Input
                        id="firstName"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        placeholder="John"
                        disabled={profileLoading}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="lastName">Last Name</Label>
                      <Input
                        id="lastName"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        placeholder="Doe"
                        disabled={profileLoading}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      disabled={profileLoading}
                    />
                  </div>

                  <Button type="submit" disabled={profileLoading}>
                    {profileLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Updating...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        Save Changes
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security">
            <Card>
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
                <CardDescription>
                  Update your password to keep your account secure
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handlePasswordSubmit} className="space-y-4">
                  {passwordError && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{passwordError}</AlertDescription>
                    </Alert>
                  )}

                  {passwordSuccess && (
                    <Alert className="border-green-200 bg-green-50 text-green-800">
                      <CheckCircle className="h-4 w-4" />
                      <AlertDescription>
                        Password changed successfully
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="currentPassword">Current Password</Label>
                    <Input
                      id="currentPassword"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      disabled={passwordLoading}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="newPassword">New Password</Label>
                    <Input
                      id="newPassword"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      disabled={passwordLoading}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm New Password</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      disabled={passwordLoading}
                    />
                  </div>

                  <Button type="submit" disabled={passwordLoading}>
                    {passwordLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Changing Password...
                      </>
                    ) : (
                      <>
                        <Shield className="w-4 h-4 mr-2" />
                        Change Password
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default Profile;
