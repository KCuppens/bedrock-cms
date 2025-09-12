import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

export default function PasswordResetConfirm() {
  const { uid, token, fulltoken } = useParams<{ uid?: string; token?: string; fulltoken?: string }>();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isValidating, setIsValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [uidb36, setUidb36] = useState('');
  const [resetToken, setResetToken] = useState('');

  useEffect(() => {
    let extractedUid = '';
    let extractedToken = '';

    // Handle Allauth format: /accounts/password/reset/key/4-cvtepe-token/
    if (fulltoken) {
      const parts = fulltoken.split('-');
      if (parts.length >= 2) {
        extractedUid = parts[0]; // The base36 user ID
        extractedToken = parts.slice(1).join('-'); // The rest is the token
      }
    }
    // Handle regular format: /password-reset/uid/token
    else if (uid && token) {
      extractedUid = uid;
      extractedToken = token;
    }

    if (!extractedUid || !extractedToken) {
      setError('Invalid password reset link. Please request a new password reset.');
      setIsValidating(false);
      return;
    }

    setUidb36(extractedUid);
    setResetToken(extractedToken);

    // Validate the UID (convert base36 to base64 for our API)
    try {
      const userId = parseInt(extractedUid, 36);
      if (isNaN(userId)) {
        throw new Error('Invalid user ID');
      }
      setTokenValid(true);
      setIsValidating(false);
    } catch (err) {
      setError('Invalid password reset link. Please request a new password reset.');
      setTokenValid(false);
      setIsValidating(false);
    }
  }, [uid, token, fulltoken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!password) {
      setError('Please enter a password');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!uidb36 || !resetToken) {
      setError('Invalid password reset link');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // Convert base36 to base64 for the API
      const userId = parseInt(uidb36, 36);
      const uidBase64 = btoa(String(userId));

      await api.auth.resetPasswordConfirm(uidBase64, resetToken, password, confirmPassword);
      setSuccess(true);

      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/sign-in', {
          state: { message: 'Password reset successful. Please login with your new password.' }
        });
      }, 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to reset password. The link may be expired or invalid.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isValidating) {
    return (
      <div className="min-h-screen bg-gradient-unified flex items-center justify-center p-4">
        <Card className="shadow-lg border-0 bg-card/80 backdrop-blur-sm w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="mt-4 text-sm text-muted-foreground">Validating reset link...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!tokenValid) {
    return (
      <div className="min-h-screen bg-gradient-unified flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <Card className="shadow-lg border-0 bg-card/80 backdrop-blur-sm">
            <CardHeader className="space-y-1 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <CardTitle className="text-2xl font-bold">Invalid Reset Link</CardTitle>
              <p className="text-muted-foreground">
                This password reset link is invalid or has expired
              </p>
            </CardHeader>
            <CardContent className="space-y-4 text-center">
              <p className="text-sm text-muted-foreground">
                Password reset links are only valid for a limited time. Please request a new password reset.
              </p>
              <div className="pt-4 space-y-2">
                <Button asChild className="w-full">
                  <Link to="/forgot-password">
                    Request New Password Reset
                  </Link>
                </Button>
                <Button asChild variant="ghost" className="w-full">
                  <Link to="/sign-in">
                    Back to Sign In
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-unified flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <Card className="shadow-lg border-0 bg-card/80 backdrop-blur-sm">
            <CardHeader className="space-y-1 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <CardTitle className="text-2xl font-bold">Password Reset Successful!</CardTitle>
              <p className="text-muted-foreground">
                Your password has been successfully reset
              </p>
            </CardHeader>
            <CardContent className="space-y-4 text-center">
              <p className="text-sm text-muted-foreground">
                Redirecting you to the sign in page...
              </p>
              <div className="pt-4">
                <Button asChild className="w-full">
                  <Link to="/sign-in">
                    Go to Sign In
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-unified flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Card className="shadow-lg border-0 bg-card/80 backdrop-blur-sm">
          <CardHeader className="space-y-1 text-center">
            <CardTitle className="text-2xl font-bold">Set New Password</CardTitle>
            <p className="text-muted-foreground">
              Please enter your new password below
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="password">New Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter new password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  className="transition-all duration-200"
                />
                <p className="text-xs text-muted-foreground">
                  Password must be at least 8 characters long
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isLoading}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  className="transition-all duration-200"
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading || !password || !confirmPassword}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Resetting Password...
                  </>
                ) : (
                  "Reset Password"
                )}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-muted-foreground">
                Remember your password?{" "}
                <Link to="/sign-in" className="text-primary hover:underline">
                  Sign in
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}