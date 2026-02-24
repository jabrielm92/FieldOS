import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Loader2 } from "lucide-react";

export default function BillingSuccessPage() {
  const navigate = useNavigate();
  useEffect(() => {
    const t = setTimeout(() => navigate("/onboarding"), 3000);
    return () => clearTimeout(t);
  }, [navigate]);
  return (
    <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center">
      <div className="text-center">
        <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle2 className="h-10 w-10 text-green-400" />
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">Welcome to FieldOS!</h1>
        <p className="text-gray-400 mb-4">Payment confirmed. Setting up your account...</p>
        <Loader2 className="h-5 w-5 text-blue-400 animate-spin mx-auto" />
      </div>
    </div>
  );
}
