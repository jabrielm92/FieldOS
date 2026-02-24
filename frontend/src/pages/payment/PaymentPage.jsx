import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { publicInvoiceAPI } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import {
  CheckCircle2, AlertCircle, Receipt, ExternalLink,
  Loader2, Phone, CreditCard
} from "lucide-react";

function formatCurrency(v) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v || 0);
}

function formatDate(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

const STATUS_LABELS = {
  DRAFT: "Draft",
  SENT: "Invoice Sent",
  VIEWED: "Viewed",
  PARTIALLY_PAID: "Partially Paid",
  PAID: "Paid",
  OVERDUE: "Overdue",
  CANCELLED: "Cancelled",
};

export default function PaymentPage() {
  const { token } = useParams();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!token) return;
    publicInvoiceAPI.getByToken(token)
      .then(res => setInvoice(res.data))
      .catch(() => setError("This payment link is invalid or has expired."))
      .finally(() => setLoading(false));
  }, [token]);

  const primaryColor = invoice?.company?.primary_color || "#0066CC";

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="text-center max-w-sm">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Link Not Found</h2>
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  const isPaid = invoice.status === "PAID";
  const isOverdue = invoice.status === "OVERDUE";
  const hasPaymentLink = !!invoice.stripe_payment_link;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Company Header */}
        <div className="text-center mb-6">
          {invoice.company?.logo_url ? (
            <img
              src={invoice.company.logo_url}
              alt={invoice.company.name}
              className="h-12 mx-auto mb-2 object-contain"
            />
          ) : (
            <div
              className="w-12 h-12 rounded-xl mx-auto mb-2 flex items-center justify-center text-white font-bold text-lg"
              style={{ backgroundColor: primaryColor }}
            >
              {(invoice.company?.name || "F")[0]}
            </div>
          )}
          <h1 className="text-xl font-bold text-gray-800">{invoice.company?.name || "FieldOS"}</h1>
        </div>

        {/* Invoice Card */}
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
          {/* Status banner */}
          <div
            className="px-6 py-4 text-white"
            style={{ backgroundColor: isPaid ? "#16a34a" : isOverdue ? "#dc2626" : primaryColor }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-80 mb-0.5">Invoice</p>
                <p className="font-mono font-bold text-lg">{invoice.invoice_number}</p>
              </div>
              <div className="text-right">
                <p className="text-sm opacity-80 mb-0.5">Status</p>
                <span className="text-sm font-medium">
                  {STATUS_LABELS[invoice.status] || invoice.status}
                </span>
              </div>
            </div>
          </div>

          <div className="p-6 space-y-6">
            {/* Customer greeting */}
            {invoice.customer?.name && (
              <p className="text-gray-600 text-sm">
                Hello, <strong>{invoice.customer.name}</strong>
              </p>
            )}

            {/* Amount hero */}
            {!isPaid ? (
              <div className="text-center py-6 bg-gray-50 rounded-xl border border-gray-100">
                <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">Amount Due</p>
                <p className="text-5xl font-bold text-gray-900 font-mono">
                  {formatCurrency(invoice.amount)}
                </p>
                {invoice.due_date && (
                  <p className={`text-sm mt-3 font-medium ${isOverdue ? "text-red-600" : "text-gray-500"}`}>
                    {isOverdue ? "⚠ Was due " : "Due "}
                    {formatDate(invoice.due_date)}
                  </p>
                )}
              </div>
            ) : (
              <div className="text-center py-6 bg-green-50 rounded-xl border border-green-200">
                <CheckCircle2 className="h-10 w-10 text-green-500 mx-auto mb-2" />
                <p className="text-xl font-bold text-green-700">Payment Received</p>
                <p className="text-3xl font-bold font-mono text-green-800 mt-1">
                  {formatCurrency(invoice.amount)}
                </p>
                {invoice.paid_at && (
                  <p className="text-sm text-green-600 mt-2">Paid on {formatDate(invoice.paid_at)}</p>
                )}
              </div>
            )}

            {/* Notes */}
            {invoice.notes && (
              <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 border border-gray-100">
                {invoice.notes}
              </div>
            )}

            {/* Pay button */}
            {!isPaid && hasPaymentLink && (
              <a
                href={invoice.stripe_payment_link}
                target="_blank"
                rel="noreferrer"
                className="block"
              >
                <button
                  className="w-full py-4 rounded-xl font-bold text-white text-lg flex items-center justify-center gap-3 transition-opacity hover:opacity-90"
                  style={{ backgroundColor: primaryColor }}
                >
                  <CreditCard className="h-5 w-5" />
                  Pay {formatCurrency(invoice.amount)} Securely
                  <ExternalLink className="h-4 w-4 opacity-70" />
                </button>
              </a>
            )}

            {!isPaid && !hasPaymentLink && (
              <div className="text-center py-4 text-sm text-gray-500 border border-dashed rounded-xl">
                <p className="mb-1">Online payment not yet available for this invoice.</p>
                {invoice.company?.phone && (
                  <a href={`tel:${invoice.company.phone}`} className="flex items-center justify-center gap-1 font-medium text-blue-600 hover:underline mt-1">
                    <Phone className="h-4 w-4" />
                    {invoice.company.phone}
                  </a>
                )}
              </div>
            )}

            {/* Thank you */}
            {isPaid && (
              <p className="text-center text-gray-500 text-sm">
                Thank you for your business! If you have any questions, please contact {invoice.company?.name || "us"}.
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-3 bg-gray-50 border-t text-center">
            <p className="text-xs text-gray-400 flex items-center justify-center gap-1">
              <Receipt className="h-3 w-3" />
              Secure invoice powered by FieldOS
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
