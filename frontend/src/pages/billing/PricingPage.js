import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { toast } from "sonner";
import { Check, Zap, Loader2 } from "lucide-react";
import axios from "axios";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

const PLAN_ORDER = ["STARTER", "PRO", "ENTERPRISE"];
const PLAN_HIGHLIGHT = "PRO"; // badge "Most Popular"

export default function PricingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [plans, setPlans] = useState({});
  const [loading, setLoading] = useState(true);
  const [checkingOut, setCheckingOut] = useState(null);

  useEffect(() => {
    axios.get(`${BACKEND_URL}/api/v1/billing/plans`)
      .then((r) => setPlans(r.data.plans || {}))
      .catch(() => toast.error("Failed to load plans"))
      .finally(() => setLoading(false));
  }, []);

  const handleSelectPlan = async (planKey) => {
    const token = localStorage.getItem("fieldos_token");
    if (!token) {
      navigate("/signup");
      return;
    }
    setCheckingOut(planKey);
    try {
      const origin = window.location.origin;
      const res = await axios.post(
        `${BACKEND_URL}/api/v1/billing/checkout`,
        {
          plan: planKey,
          success_url: `${origin}/billing/success`,
          cancel_url: `${origin}/pricing`,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      window.location.href = res.data.checkout_url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to start checkout");
      setCheckingOut(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center">
        <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0f1a] py-16 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 mb-4">
            <Zap className="h-6 w-6 text-blue-400" />
            <span className="text-xl font-black text-white tracking-tight">FieldOS</span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">Choose your plan</h1>
          <p className="text-gray-400 text-lg">14-day free trial on all plans. No credit card required to start.</p>
        </div>

        {/* Plans */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {PLAN_ORDER.map((key) => {
            const plan = plans[key];
            if (!plan) return null;
            const isHighlight = key === PLAN_HIGHLIGHT;
            const isChecking = checkingOut === key;
            return (
              <div
                key={key}
                className={`relative rounded-2xl border p-8 flex flex-col ${
                  isHighlight
                    ? "border-blue-500 bg-blue-600/10 shadow-xl shadow-blue-900/30"
                    : "border-white/10 bg-white/5"
                }`}
              >
                {isHighlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-4 py-1 rounded-full">
                    Most Popular
                  </div>
                )}
                <div className="mb-6">
                  <h2 className="text-xl font-bold text-white mb-1">{plan.name}</h2>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-black text-white">${plan.price_monthly}</span>
                    <span className="text-gray-400">/mo</span>
                  </div>
                </div>

                <ul className="space-y-3 flex-1 mb-8">
                  {(plan.features || []).map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-300">{f}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleSelectPlan(key)}
                  disabled={!!checkingOut}
                  className={`w-full h-12 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2 ${
                    isHighlight
                      ? "bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50"
                      : "bg-white/10 hover:bg-white/20 text-white disabled:opacity-50"
                  }`}
                >
                  {isChecking ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Redirecting...
                    </>
                  ) : (
                    `Start with ${plan.name}`
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* Skip for now (trial) */}
        <div className="text-center">
          <button
            onClick={() => navigate("/onboarding")}
            className="text-sm text-gray-500 hover:text-gray-300 transition-colors underline underline-offset-2"
          >
            Continue with free trial →
          </button>
        </div>
      </div>
    </div>
  );
}
