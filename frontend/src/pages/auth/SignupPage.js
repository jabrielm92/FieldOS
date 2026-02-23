import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { toast } from "sonner";
import { Zap, Loader2, ArrowLeft } from "lucide-react";
import axios from "axios";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

export default function SignupPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    business_name: "",
    owner_name: "",
    email: "",
    password: "",
    phone: "",
  });

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.business_name || !form.owner_name || !form.email || !form.password || !form.phone) {
      toast.error("Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${BACKEND_URL}/api/v1/auth/register`, form);
      const { access_token, user } = res.data;
      localStorage.setItem("fieldos_token", access_token);
      localStorage.setItem("fieldos_user", JSON.stringify(user));
      toast.success(`Welcome to FieldOS, ${user.name}!`);
      // Go to pricing to pick a plan
      navigate("/pricing");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-transparent to-purple-600/5" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(59,130,246,0.1),transparent_50%)]" />

      <Link to="/" className="absolute top-6 left-6 flex items-center gap-2 text-gray-400 hover:text-white transition-colors z-20">
        <ArrowLeft className="h-4 w-4" />
        <span className="text-sm">Back to Home</span>
      </Link>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3 mb-4">
            <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
              <Zap className="h-8 w-8 text-white" />
            </div>
            <span className="text-3xl font-black text-white tracking-tight">FieldOS</span>
          </Link>
          <p className="text-gray-400">Start your 14-day free trial</p>
          <p className="text-xs text-gray-500 mt-1">No credit card required to start</p>
        </div>

        <div className="bg-[#0d1424] border border-white/10 rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Business Name</label>
              <input
                type="text"
                value={form.business_name}
                onChange={set("business_name")}
                placeholder="Acme HVAC Services"
                required
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 h-12 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Your Name</label>
              <input
                type="text"
                value={form.owner_name}
                onChange={set("owner_name")}
                placeholder="John Smith"
                required
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 h-12 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={set("email")}
                placeholder="john@acmehvac.com"
                required
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 h-12 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Phone</label>
              <input
                type="tel"
                value={form.phone}
                onChange={set("phone")}
                placeholder="(555) 000-0000"
                required
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 h-12 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
              <input
                type="password"
                value={form.password}
                onChange={set("password")}
                placeholder="••••••••"
                required
                minLength={8}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 h-12 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white h-12 text-base font-semibold rounded-xl transition-colors flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Creating account...
                </>
              ) : (
                "Start Free Trial"
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              Already have an account?{" "}
              <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-gray-500">
          By signing up you agree to our{" "}
          <Link to="/terms" className="hover:text-gray-300">Terms</Link>
          {" & "}
          <Link to="/privacy" className="hover:text-gray-300">Privacy Policy</Link>
        </div>
      </div>
    </div>
  );
}
