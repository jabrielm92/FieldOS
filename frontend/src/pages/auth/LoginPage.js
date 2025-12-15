import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { toast } from "sonner";
import { Wrench, Loader2 } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const user = await login(email, password);
      toast.success(`Welcome back, ${user.name}!`);
      
      if (user.role === "SUPERADMIN") {
        navigate("/admin");
      } else {
        navigate("/dashboard");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px]" />
      
      <Card className="w-full max-w-md relative z-10 animate-fade-in" data-testid="login-card">
        <CardHeader className="text-center pb-2">
          <div className="w-16 h-16 bg-primary rounded-xl flex items-center justify-center mx-auto mb-4">
            <Wrench className="h-8 w-8 text-primary-foreground" />
          </div>
          <CardTitle className="font-heading text-3xl font-black tracking-tight">
            FieldOS
          </CardTitle>
          <CardDescription className="text-base">
            Revenue & Operations OS for Field Service
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@fieldos.app"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="login-password"
              />
            </div>
            
            <Button 
              type="submit" 
              className="w-full btn-industrial"
              disabled={loading}
              data-testid="login-submit"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "SIGN IN"
              )}
            </Button>
          </form>
          
          <div className="mt-6 p-4 bg-muted rounded-md space-y-2">
            <p className="text-xs text-muted-foreground font-semibold uppercase tracking-wide">Demo Credentials:</p>
            <div className="space-y-1">
              <p className="text-sm">
                <span className="text-muted-foreground">Superadmin:</span>{" "}
                <span className="font-mono">admin@fieldos.app / admin123</span>
              </p>
              <p className="text-sm">
                <span className="text-muted-foreground">Tenant Owner:</span>{" "}
                <span className="font-mono">owner@radiancehvac.com / owner123</span>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
