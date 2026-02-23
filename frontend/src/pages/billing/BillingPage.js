import { useState, useEffect } from "react";
import { toast } from "sonner";
import { CreditCard, CheckCircle2, AlertTriangle, Loader2, ExternalLink } from "lucide-react";
import axios from "axios";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

const STATUS_COLORS = {
  ACTIVE: "text-green-400",
  PAST_DUE: "text-yellow-400",
  CANCELED: "text-red-400",
  UNPAID: "text-red-400",
  PENDING_PAYMENT: "text-yellow-400",
  INACTIVE: "text-gray-400",
};

const STATUS_LABELS = {
  ACTIVE: "Active",
  PAST_DUE: "Past Due",
  CANCELED: "Canceled",
  UNPAID: "Unpaid",
  PENDING_PAYMENT: "Payment Pending",
  INACTIVE: "No Subscription",
};

export default function BillingPage() {
  const [sub, setSub] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openingPortal, setOpeningPortal] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("fieldos_token");
    axios
      .get(`${BACKEND_URL}/api/v1/billing/subscription`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((r) => setSub(r.data))
      .catch(() => toast.error("Failed to load billing info"))
      .finally(() => setLoading(false));
  }, []);

  const handleManageBilling = async () => {
    setOpeningPortal(true);
    try {
      const token = localStorage.getItem("fieldos_token");
      const res = await axios.post(
        `${BACKEND_URL}/api/v1/billing/portal`,
        { return_url: window.location.href },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      window.location.href = res.data.portal_url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to open billing portal");
      setOpeningPortal(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 text-blue-400 animate-spin" />
      </div>
    );
  }

  const status = sub?.status || "INACTIVE";
  const plan = sub?.plan;
  const statusColor = STATUS_COLORS[status] || "text-gray-400";
  const statusLabel = STATUS_LABELS[status] || status;
  const hasActiveSubscription = sub?.stripe_subscription_id;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white mb-1">Billing & Subscription</h2>
        <p className="text-gray-400 text-sm">Manage your FieldOS subscription and payment method.</p>
      </div>

      {/* Current plan card */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600/20 rounded-lg flex items-center justify-center">
              <CreditCard className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <p className="text-white font-semibold">{plan ? `${plan} Plan` : "No Active Plan"}</p>
              <p className={`text-sm font-medium ${statusColor}`}>{statusLabel}</p>
            </div>
          </div>
          {status === "ACTIVE" && (
            <CheckCircle2 className="h-5 w-5 text-green-400" />
          )}
          {status === "PAST_DUE" && (
            <AlertTriangle className="h-5 w-5 text-yellow-400" />
          )}
        </div>

        {sub?.current_period_end && status === "ACTIVE" && (
          <p className="text-sm text-gray-400 mb-4">
            Renews on{" "}
            {new Date(sub.current_period_end).toLocaleDateString("en-US", {
              year: "numeric", month: "long", day: "numeric",
            })}
          </p>
        )}

        <div className="flex gap-3 flex-wrap">
          {hasActiveSubscription ? (
            <button
              onClick={handleManageBilling}
              disabled={openingPortal}
              className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              {openingPortal ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ExternalLink className="h-4 w-4" />
              )}
              Manage Billing
            </button>
          ) : (
            <a
              href="/pricing"
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              <CreditCard className="h-4 w-4" />
              View Plans & Subscribe
            </a>
          )}
        </div>
      </div>

      {status === "PAST_DUE" && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-yellow-300 font-medium text-sm">Payment Past Due</p>
            <p className="text-yellow-400/70 text-xs mt-1">
              Please update your payment method to keep your account active.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
