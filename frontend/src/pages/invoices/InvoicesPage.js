import { useState, useEffect, useCallback } from "react";
import { Layout } from "../../components/layout/Layout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Label } from "../../components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter
} from "../../components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "../../components/ui/select";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger
} from "../../components/ui/dropdown-menu";
import { toast } from "sonner";
import {
  Plus, Search, Receipt, DollarSign, AlertCircle,
  CheckCircle2, Clock, MoreVertical, CreditCard, Send,
  Link2, ExternalLink, Loader2, FileText, XCircle
} from "lucide-react";
import { invoiceAPI, customerAPI, jobAPI } from "../../lib/api";

// ─── Status config ────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
  DRAFT:           { label: "Draft",           className: "bg-gray-100 text-gray-700 border-gray-200" },
  SENT:            { label: "Sent",            className: "bg-blue-100 text-blue-700 border-blue-200" },
  VIEWED:          { label: "Viewed",          className: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  PARTIALLY_PAID:  { label: "Partial",         className: "bg-orange-100 text-orange-700 border-orange-200" },
  PAID:            { label: "Paid",            className: "bg-green-100 text-green-700 border-green-200" },
  OVERDUE:         { label: "Overdue",         className: "bg-red-100 text-red-700 border-red-200" },
  CANCELLED:       { label: "Cancelled",       className: "bg-gray-100 text-gray-500 border-gray-200 line-through" },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.DRAFT;
  return <Badge variant="outline" className={cfg.className}>{cfg.label}</Badge>;
}

function formatCurrency(v) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(v || 0);
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function customerName(inv) {
  if (!inv.customer) return "Unknown";
  return `${inv.customer.first_name || ""} ${inv.customer.last_name || ""}`.trim() || inv.customer.name || "Unknown";
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function InvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showRecordPayment, setShowRecordPayment] = useState(false);
  const [paymentInvoice, setPaymentInvoice] = useState(null);

  const fetchInvoices = useCallback(async () => {
    try {
      const res = await invoiceAPI.list();
      setInvoices(res.data || []);
    } catch {
      toast.error("Failed to load invoices");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  // ── Derived stats ────────────────────────────────────────────────────────
  const stats = {
    outstanding: invoices.filter(i => ["DRAFT","SENT","VIEWED","PARTIALLY_PAID"].includes(i.status))
      .reduce((s, i) => s + (i.amount || 0), 0),
    overdue: invoices.filter(i => i.status === "OVERDUE").reduce((s, i) => s + (i.amount || 0), 0),
    paid: invoices.filter(i => i.status === "PAID").reduce((s, i) => s + (i.amount || 0), 0),
    draftCount: invoices.filter(i => i.status === "DRAFT").length,
    overdueCount: invoices.filter(i => i.status === "OVERDUE").length,
  };

  // ── Filtering ─────────────────────────────────────────────────────────────
  const filtered = invoices.filter(inv => {
    if (statusFilter !== "all" && inv.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        customerName(inv).toLowerCase().includes(q) ||
        (inv.id || "").toLowerCase().includes(q) ||
        (inv.invoice_number || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const openDetail = (inv) => {
    setSelectedInvoice(inv);
    setShowDetail(true);
  };

  return (
    <Layout title="Invoices" subtitle="Track and manage customer invoices">
      {/* ── Stats Bar ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard icon={<Clock className="h-5 w-5 text-blue-500" />}
          label="Outstanding" value={formatCurrency(stats.outstanding)} color="blue" />
        <StatCard icon={<AlertCircle className="h-5 w-5 text-red-500" />}
          label={`Overdue (${stats.overdueCount})`} value={formatCurrency(stats.overdue)} color="red" />
        <StatCard icon={<CheckCircle2 className="h-5 w-5 text-green-500" />}
          label="Collected" value={formatCurrency(stats.paid)} color="green" />
        <StatCard icon={<FileText className="h-5 w-5 text-gray-500" />}
          label="Drafts" value={stats.draftCount} color="gray" />
      </div>

      {/* ── Toolbar ─────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Search invoices..."
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {Object.entries(STATUS_CONFIG).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button className="btn-industrial" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />NEW INVOICE
        </Button>
      </div>

      {/* ── Table ───────────────────────────────────────────────────── */}
      <div className="border rounded-lg overflow-hidden bg-card">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Receipt className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="font-medium mb-1">No invoices found</p>
            <p className="text-sm text-muted-foreground mb-4">
              {search || statusFilter !== "all" ? "Try adjusting your filters" : "Create your first invoice to get started"}
            </p>
            {!search && statusFilter === "all" && (
              <Button className="btn-industrial" onClick={() => setShowCreate(true)}>
                <Plus className="h-4 w-4 mr-2" />Create Invoice
              </Button>
            )}
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted/40 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Invoice #</th>
                <th className="text-left px-4 py-3 font-medium">Customer</th>
                <th className="text-left px-4 py-3 font-medium">Amount</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Due Date</th>
                <th className="text-right px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(inv => (
                <InvoiceRow key={inv.id} inv={inv} onOpen={openDetail} onRefresh={fetchInvoices}
                  onRecordPayment={(inv) => { setPaymentInvoice(inv); setShowRecordPayment(true); }} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Modals ──────────────────────────────────────────────────── */}
      <CreateInvoiceModal open={showCreate} onOpenChange={setShowCreate} onSuccess={fetchInvoices} />
      {selectedInvoice && (
        <InvoiceDetailModal
          invoice={selectedInvoice}
          open={showDetail}
          onOpenChange={setShowDetail}
          onRefresh={fetchInvoices}
        />
      )}
      {paymentInvoice && (
        <RecordPaymentModal
          open={showRecordPayment}
          onOpenChange={setShowRecordPayment}
          invoice={paymentInvoice}
          onSuccess={() => { setShowRecordPayment(false); fetchInvoices(); }}
        />
      )}
    </Layout>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({ icon, label, value, color }) {
  const bg = {
    blue: "bg-blue-50 dark:bg-blue-950/30",
    red: "bg-red-50 dark:bg-red-950/30",
    green: "bg-green-50 dark:bg-green-950/30",
    gray: "bg-gray-50 dark:bg-gray-900/30",
  }[color];

  return (
    <div className={`rounded-lg border p-4 ${bg}`}>
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-bold font-mono">{value}</p>
    </div>
  );
}

// ─── Invoice Table Row ────────────────────────────────────────────────────────
function InvoiceRow({ inv, onOpen, onRefresh, onRecordPayment }) {
  const [acting, setActing] = useState(false);

  const markPaid = async (e) => {
    e.stopPropagation();
    setActing(true);
    try {
      await invoiceAPI.markPaid(inv.id);
      toast.success("Invoice marked as paid");
      onRefresh();
    } catch {
      toast.error("Failed to mark as paid");
    } finally {
      setActing(false);
    }
  };

  const createPaymentLink = async (e) => {
    e.stopPropagation();
    setActing(true);
    try {
      const res = await invoiceAPI.createPaymentLink(inv.id);
      await navigator.clipboard.writeText(res.data.payment_link || "");
      toast.success("Payment link copied to clipboard!");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create payment link");
    } finally {
      setActing(false);
    }
  };

  const sendPaymentLink = async (e) => {
    e.stopPropagation();
    setActing(true);
    try {
      await invoiceAPI.sendPaymentLink(inv.id);
      toast.success("Payment link sent via SMS");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send payment link");
    } finally {
      setActing(false);
    }
  };

  const sendInvoice = async (e) => {
    e.stopPropagation();
    setActing(true);
    try {
      await invoiceAPI.send(inv.id);
      toast.success("Invoice sent via SMS");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send invoice");
    } finally {
      setActing(false);
    }
  };

  const sendReminder = async (e) => {
    e.stopPropagation();
    setActing(true);
    try {
      await invoiceAPI.remind(inv.id);
      toast.success("Reminder sent via SMS");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send reminder");
    } finally {
      setActing(false);
    }
  };

  const voidInvoice = async (e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to void this invoice? This cannot be undone.")) return;
    setActing(true);
    try {
      await invoiceAPI.voidInvoice(inv.id);
      toast.success("Invoice voided");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to void invoice");
    } finally {
      setActing(false);
    }
  };

  const deleteInvoice = async (e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to permanently delete this draft invoice?")) return;
    setActing(true);
    try {
      await invoiceAPI.deleteInvoice(inv.id);
      toast.success("Invoice deleted");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete invoice");
    } finally {
      setActing(false);
    }
  };

  const isOverdue = inv.status === "OVERDUE";
  const isDue = inv.due_date && new Date(inv.due_date) < new Date() && !["PAID","CANCELLED","DRAFT"].includes(inv.status);

  return (
    <tr
      className="border-t hover:bg-muted/20 cursor-pointer transition-colors"
      onClick={() => onOpen(inv)}
    >
      <td className="px-4 py-3 font-mono font-medium text-primary">
        {inv.invoice_number || `INV-${inv.id.slice(0, 6).toUpperCase()}`}
      </td>
      <td className="px-4 py-3">{customerName(inv)}</td>
      <td className="px-4 py-3 font-mono font-semibold">{formatCurrency(inv.amount)}</td>
      <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
      <td className={`px-4 py-3 ${isDue || isOverdue ? "text-red-600 font-medium" : "text-muted-foreground"}`}>
        {formatDate(inv.due_date)}
        {(isDue || isOverdue) && <AlertCircle className="inline h-3 w-3 ml-1 text-red-500" />}
      </td>
      <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
        {acting ? (
          <Loader2 className="h-4 w-4 animate-spin ml-auto mr-2" />
        ) : (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onOpen(inv)}>
                <Receipt className="h-4 w-4 mr-2" /> View Details
              </DropdownMenuItem>
              {inv.status !== "PAID" && inv.status !== "CANCELLED" && (
                <DropdownMenuItem onClick={markPaid}>
                  <CheckCircle2 className="h-4 w-4 mr-2" /> Mark as Paid
                </DropdownMenuItem>
              )}
              {inv.status !== "PAID" && inv.status !== "CANCELLED" && (
                <DropdownMenuItem onClick={createPaymentLink}>
                  <Link2 className="h-4 w-4 mr-2" /> Copy Payment Link
                </DropdownMenuItem>
              )}
              {inv.stripe_payment_link && inv.status !== "PAID" && (
                <DropdownMenuItem onClick={sendPaymentLink}>
                  <Send className="h-4 w-4 mr-2" /> Send via SMS
                </DropdownMenuItem>
              )}
              {inv.status === "DRAFT" && (
                <DropdownMenuItem onClick={sendInvoice}>
                  <Send className="h-4 w-4 mr-2" /> Send Invoice
                </DropdownMenuItem>
              )}
              {["SENT", "OVERDUE", "PARTIALLY_PAID"].includes(inv.status) && (
                <DropdownMenuItem onClick={sendReminder}>
                  <Send className="h-4 w-4 mr-2" /> Send Reminder
                </DropdownMenuItem>
              )}
              {inv.status !== "PAID" && inv.status !== "CANCELLED" && (
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onRecordPayment(inv); }}>
                  <DollarSign className="h-4 w-4 mr-2" /> Record Payment
                </DropdownMenuItem>
              )}
              {inv.status !== "PAID" && inv.status !== "CANCELLED" && (
                <DropdownMenuItem onClick={voidInvoice} className="text-orange-600">
                  <XCircle className="h-4 w-4 mr-2" /> Void Invoice
                </DropdownMenuItem>
              )}
              {inv.status === "DRAFT" && (
                <DropdownMenuItem onClick={deleteInvoice} className="text-red-600">
                  <XCircle className="h-4 w-4 mr-2" /> Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </td>
    </tr>
  );
}

// ─── Invoice Detail Modal ─────────────────────────────────────────────────────
function InvoiceDetailModal({ invoice, open, onOpenChange, onRefresh }) {
  const [acting, setActing] = useState(null); // null | 'paid' | 'link' | 'send'

  const run = async (action, fn) => {
    setActing(action);
    try { await fn(); } finally { setActing(null); }
  };

  const markPaid = () => run("paid", async () => {
    await invoiceAPI.markPaid(invoice.id);
    toast.success("Invoice marked as paid");
    onRefresh();
    onOpenChange(false);
  });

  const copyPaymentLink = () => run("link", async () => {
    try {
      const res = await invoiceAPI.createPaymentLink(invoice.id);
      await navigator.clipboard.writeText(res.data.payment_link || "");
      toast.success("Payment link copied to clipboard!");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Stripe not configured — add your Stripe key in Settings");
    }
  });

  const sendPaymentLink = () => run("send", async () => {
    try {
      await invoiceAPI.sendPaymentLink(invoice.id);
      toast.success("Payment link sent via SMS");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send SMS");
    }
  });

  const isPaid = invoice.status === "PAID";
  const isCancelled = invoice.status === "CANCELLED";
  const hasPaymentLink = !!invoice.stripe_payment_link;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Receipt className="h-5 w-5" />
            {invoice.invoice_number || `INV-${invoice.id.slice(0, 6).toUpperCase()}`}
          </DialogTitle>
          <DialogDescription asChild>
            <div><StatusBadge status={invoice.status} /></div>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Amount hero */}
          <div className="text-center py-6 bg-muted/40 rounded-lg border">
            <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Amount Due</p>
            <p className="text-4xl font-bold font-mono">{formatCurrency(invoice.amount)}</p>
            {invoice.due_date && (
              <p className="text-sm text-muted-foreground mt-2">Due {formatDate(invoice.due_date)}</p>
            )}
          </div>

          {/* Customer */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Customer</p>
              <p className="font-medium">{customerName(invoice)}</p>
              {invoice.customer?.phone && (
                <p className="text-muted-foreground">{invoice.customer.phone}</p>
              )}
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Dates</p>
              <p>Created: {formatDate(invoice.created_at)}</p>
              {invoice.paid_at && <p className="text-green-600">Paid: {formatDate(invoice.paid_at)}</p>}
              {invoice.payment_link_sent_at && (
                <p className="text-muted-foreground text-xs">Link sent: {formatDate(invoice.payment_link_sent_at)}</p>
              )}
            </div>
          </div>

          {/* Job */}
          {invoice.job && (
            <div className="border rounded p-3 text-sm bg-muted/20">
              <p className="text-xs text-muted-foreground mb-1">Related Job</p>
              <p className="font-medium">{invoice.job.job_type}</p>
              {invoice.job.scheduled_date && (
                <p className="text-muted-foreground">Scheduled: {formatDate(invoice.job.scheduled_date)}</p>
              )}
            </div>
          )}

          {/* Existing payment link */}
          {hasPaymentLink && (
            <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded text-sm">
              <Link2 className="h-4 w-4 text-blue-600 flex-shrink-0" />
              <span className="flex-1 text-blue-700 dark:text-blue-300 truncate">{invoice.stripe_payment_link}</span>
              <a href={invoice.stripe_payment_link} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}>
                <ExternalLink className="h-4 w-4 text-blue-600" />
              </a>
            </div>
          )}

          {/* Actions */}
          {!isPaid && !isCancelled && (
            <div className="flex gap-2 flex-wrap">
              <Button className="btn-industrial flex-1" onClick={markPaid} disabled={!!acting}>
                {acting === "paid" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
                Mark Paid
              </Button>
              <Button variant="outline" className="flex-1" onClick={copyPaymentLink} disabled={!!acting}>
                {acting === "link" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Link2 className="h-4 w-4 mr-2" />}
                {hasPaymentLink ? "Copy Link" : "Get Payment Link"}
              </Button>
              {hasPaymentLink && (
                <Button variant="outline" className="flex-1" onClick={sendPaymentLink} disabled={!!acting}>
                  {acting === "send" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                  Send SMS
                </Button>
              )}
              {invoice.status === "DRAFT" && (
                <Button variant="outline" className="flex-1" onClick={() => run("sendInv", async () => {
                  try {
                    await invoiceAPI.send(invoice.id);
                    toast.success("Invoice sent via SMS");
                    onRefresh();
                  } catch (err) {
                    toast.error(err.response?.data?.detail || "Failed to send invoice");
                  }
                })} disabled={!!acting}>
                  {acting === "sendInv" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                  Send Invoice
                </Button>
              )}
              {["SENT", "OVERDUE"].includes(invoice.status) && (
                <Button variant="outline" className="flex-1" onClick={() => run("remind", async () => {
                  try {
                    await invoiceAPI.remind(invoice.id);
                    toast.success("Reminder sent via SMS");
                    onRefresh();
                  } catch (err) {
                    toast.error(err.response?.data?.detail || "Failed to send reminder");
                  }
                })} disabled={!!acting}>
                  {acting === "remind" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Send className="h-4 w-4 mr-2" />}
                  Send Reminder
                </Button>
              )}
            </div>
          )}

          {isPaid && (
            <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <span className="text-sm text-green-700 dark:text-green-300 font-medium">
                Payment received {invoice.paid_at ? `on ${formatDate(invoice.paid_at)}` : ""}
              </span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Create Invoice Modal ─────────────────────────────────────────────────────
function CreateInvoiceModal({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    customer_id: "", job_id: "", amount: "", due_date: "", notes: ""
  });
  const [customers, setCustomers] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  const defaultDue = () => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split("T")[0];
  };

  useEffect(() => {
    if (open) {
      setFormData({ customer_id: "", job_id: "", amount: "", due_date: defaultDue(), notes: "" });
      fetchCustomers();
      fetchJobs();
    }
  }, [open]);

  const fetchCustomers = async () => {
    try { setCustomers((await customerAPI.list()).data || []); } catch {}
  };

  const fetchJobs = async () => {
    try {
      const all = (await jobAPI.list()).data || [];
      setJobs(all.filter(j => j.status === "COMPLETED" || j.status === "IN_PROGRESS"));
    } catch {}
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.customer_id || !formData.amount || !formData.job_id) {
      toast.error("Customer, job and amount are required");
      return;
    }
    setLoading(true);
    try {
      await invoiceAPI.create({ ...formData, amount: parseFloat(formData.amount) });
      toast.success("Invoice created");
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create invoice");
    } finally {
      setLoading(false);
    }
  };

  const field = (key, v) => setFormData(prev => ({ ...prev, [key]: v }));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Receipt className="h-5 w-5" />Create Invoice
          </DialogTitle>
          <DialogDescription>Create a new invoice for a customer</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {/* Customer */}
            <div className="space-y-2">
              <Label>Customer *</Label>
              <Select value={formData.customer_id} onValueChange={v => field("customer_id", v)}>
                <SelectTrigger><SelectValue placeholder="Select customer" /></SelectTrigger>
                <SelectContent>
                  {customers.map(c => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.first_name} {c.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Job */}
            <div className="space-y-2">
              <Label>Job *</Label>
              <Select value={formData.job_id} onValueChange={v => {
                field("job_id", v);
                const j = jobs.find(x => x.id === v);
                if (j?.quote_amount) field("amount", j.quote_amount.toString());
              }}>
                <SelectTrigger><SelectValue placeholder="Select completed job" /></SelectTrigger>
                <SelectContent>
                  {jobs.map(j => (
                    <SelectItem key={j.id} value={j.id}>
                      {j.job_type} – {j.customer?.first_name} {j.customer?.last_name}
                      {j.quote_amount ? ` ($${j.quote_amount})` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Amount */}
            <div className="space-y-2">
              <Label>Amount ($) *</Label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input type="number" step="0.01" min="0" className="pl-9"
                  value={formData.amount}
                  onChange={e => field("amount", e.target.value)}
                  required placeholder="0.00" />
              </div>
            </div>

            {/* Due Date */}
            <div className="space-y-2">
              <Label>Due Date *</Label>
              <Input type="date" value={formData.due_date}
                onChange={e => field("due_date", e.target.value)} required />
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label>Notes (optional)</Label>
              <Input value={formData.notes}
                onChange={e => field("notes", e.target.value)}
                placeholder="Any notes for the customer..." />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" className="btn-industrial" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Receipt className="h-4 w-4 mr-2" />}
              Create Invoice
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Record Payment Modal ─────────────────────────────────────────────────────
function RecordPaymentModal({ open, onOpenChange, invoice, onSuccess }) {
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("CASH");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && invoice) {
      const amountDue = invoice.amount_due != null ? invoice.amount_due : invoice.amount;
      setAmount(amountDue?.toString() || "");
      setMethod("CASH");
      setNotes("");
    }
  }, [open, invoice]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) {
      toast.error("Please enter a valid payment amount");
      return;
    }
    setLoading(true);
    try {
      await invoiceAPI.recordPayment(invoice.id, {
        amount: parseFloat(amount),
        method,
        notes,
      });
      toast.success("Payment recorded successfully");
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to record payment");
    } finally {
      setLoading(false);
    }
  };

  if (!invoice) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Record Payment
          </DialogTitle>
          <DialogDescription>
            Record a payment for invoice {invoice.invoice_number || `INV-${invoice.id?.slice(0, 6).toUpperCase()}`}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Amount ($) *</Label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  className="pl-9"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                  placeholder="0.00"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Payment Method</Label>
              <Select value={method} onValueChange={setMethod}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="CASH">Cash</SelectItem>
                  <SelectItem value="CHECK">Check</SelectItem>
                  <SelectItem value="CREDIT_CARD">Credit Card</SelectItem>
                  <SelectItem value="BANK_TRANSFER">Bank Transfer</SelectItem>
                  <SelectItem value="OTHER">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Notes (optional)</Label>
              <Input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any notes about this payment..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" className="btn-industrial" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <DollarSign className="h-4 w-4 mr-2" />}
              Record Payment
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
