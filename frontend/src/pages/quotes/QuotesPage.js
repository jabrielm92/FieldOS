import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Separator } from "../../components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { quoteAPI, customerAPI, propertyAPI, jobAPI, leadAPI } from "../../lib/api";
import { toast } from "sonner";
import { 
  Plus, Search, DollarSign, User, FileText, Send, Check, X, 
  Clock, MapPin, Briefcase, Receipt, CreditCard, AlertTriangle,
  ChevronRight, Eye, Edit, Copy
} from "lucide-react";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const quoteStatusColors = {
  DRAFT: "bg-gray-100 text-gray-800",
  SENT: "bg-blue-100 text-blue-800",
  ACCEPTED: "bg-green-100 text-green-800",
  DECLINED: "bg-red-100 text-red-800",
  LOST: "bg-orange-100 text-orange-800",
};

const invoiceStatusColors = {
  DRAFT: "bg-gray-100 text-gray-800",
  SENT: "bg-blue-100 text-blue-800",
  PARTIALLY_PAID: "bg-yellow-100 text-yellow-800",
  PAID: "bg-green-100 text-green-800",
  OVERDUE: "bg-red-100 text-red-800",
};

export default function QuotesPage() {
  const [activeTab, setActiveTab] = useState("quotes");
  const [quotes, setQuotes] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreateQuoteDialog, setShowCreateQuoteDialog] = useState(false);
  const [showCreateInvoiceDialog, setShowCreateInvoiceDialog] = useState(false);
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [showQuoteDetail, setShowQuoteDetail] = useState(false);
  const [showInvoiceDetail, setShowInvoiceDetail] = useState(false);

  useEffect(() => {
    fetchQuotes();
    fetchInvoices();
    const interval = setInterval(() => {
      fetchQuotes();
      fetchInvoices();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchQuotes = async () => {
    try {
      const response = await quoteAPI.list();
      setQuotes(response.data);
    } catch (error) {
      toast.error("Failed to load quotes");
    } finally {
      setLoading(false);
    }
  };

  const fetchInvoices = async () => {
    try {
      const token = localStorage.getItem('fieldos_token');
      const response = await axios.get(`${API_URL}/api/v1/invoices`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setInvoices(response.data);
    } catch (error) {
      console.error("Failed to load invoices");
    }
  };

  const handleQuoteClick = (quote) => {
    setSelectedQuote(quote);
    setShowQuoteDetail(true);
  };

  const handleInvoiceClick = (invoice) => {
    setSelectedInvoice(invoice);
    setShowInvoiceDetail(true);
  };

  const filteredQuotes = quotes.filter((quote) => {
    if (statusFilter !== "all" && quote.status !== statusFilter) return false;
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      quote.customer?.first_name?.toLowerCase().includes(searchLower) ||
      quote.customer?.last_name?.toLowerCase().includes(searchLower) ||
      quote.description?.toLowerCase().includes(searchLower)
    );
  });

  const filteredInvoices = invoices.filter((invoice) => {
    if (statusFilter !== "all" && invoice.status !== statusFilter) return false;
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      invoice.customer?.first_name?.toLowerCase().includes(searchLower) ||
      invoice.customer?.last_name?.toLowerCase().includes(searchLower)
    );
  });

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  // Calculate stats
  const quoteStats = {
    total: quotes.length,
    draft: quotes.filter(q => q.status === "DRAFT").length,
    sent: quotes.filter(q => q.status === "SENT").length,
    accepted: quotes.filter(q => q.status === "ACCEPTED").length,
    totalValue: quotes.reduce((sum, q) => sum + (q.amount || 0), 0),
  };

  const invoiceStats = {
    total: invoices.length,
    unpaid: invoices.filter(i => ["DRAFT", "SENT", "OVERDUE"].includes(i.status)).length,
    paid: invoices.filter(i => i.status === "PAID").length,
    overdue: invoices.filter(i => i.status === "OVERDUE").length,
    totalOutstanding: invoices.filter(i => i.status !== "PAID").reduce((sum, i) => sum + (i.amount || 0), 0),
  };

  return (
    <Layout title="Quotes & Invoices" subtitle="Manage quotes, estimates and invoices">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <TabsList>
            <TabsTrigger value="quotes" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Quotes ({quotes.length})
            </TabsTrigger>
            <TabsTrigger value="invoices" className="flex items-center gap-2">
              <Receipt className="h-4 w-4" />
              Invoices ({invoices.length})
            </TabsTrigger>
          </TabsList>

          <div className="flex gap-2">
            {activeTab === "quotes" ? (
              <CreateQuoteDialog 
                open={showCreateQuoteDialog} 
                onOpenChange={setShowCreateQuoteDialog}
                onSuccess={fetchQuotes}
              />
            ) : (
              <CreateInvoiceDialog 
                open={showCreateInvoiceDialog} 
                onOpenChange={setShowCreateInvoiceDialog}
                onSuccess={fetchInvoices}
              />
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {activeTab === "quotes" ? (
            <>
              <Card className="p-4">
                <p className="text-sm text-muted-foreground">Total Quotes</p>
                <p className="text-2xl font-bold">{quoteStats.total}</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-2xl font-bold text-blue-600">{quoteStats.sent}</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-muted-foreground">Accepted</p>
                <p className="text-2xl font-bold text-green-600">{quoteStats.accepted}</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-muted-foreground">Total Value</p>
                <p className="text-2xl font-bold font-mono">{formatCurrency(quoteStats.totalValue)}</p>
              </Card>
            </>
          ) : (
            <>
              <Card className="p-4">
                <p className="text-sm text-muted-foreground">Total Invoices</p>
                <p className="text-2xl font-bold">{invoiceStats.total}</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-muted-foreground">Unpaid</p>
                <p className="text-2xl font-bold text-orange-600">{invoiceStats.unpaid}</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-muted-foreground">Overdue</p>
                <p className="text-2xl font-bold text-red-600">{invoiceStats.overdue}</p>
              </Card>
              <Card className="p-4">
                <p className="text-sm text-muted-foreground">Outstanding</p>
                <p className="text-2xl font-bold font-mono">{formatCurrency(invoiceStats.totalOutstanding)}</p>
              </Card>
            </>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={`Search ${activeTab}...`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              {activeTab === "quotes" ? (
                <>
                  <SelectItem value="DRAFT">Draft</SelectItem>
                  <SelectItem value="SENT">Sent</SelectItem>
                  <SelectItem value="ACCEPTED">Accepted</SelectItem>
                  <SelectItem value="DECLINED">Declined</SelectItem>
                </>
              ) : (
                <>
                  <SelectItem value="DRAFT">Draft</SelectItem>
                  <SelectItem value="SENT">Sent</SelectItem>
                  <SelectItem value="PAID">Paid</SelectItem>
                  <SelectItem value="OVERDUE">Overdue</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
        </div>

        <TabsContent value="quotes">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : filteredQuotes.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                <p className="text-muted-foreground">No quotes found</p>
                <Button className="mt-4" onClick={() => setShowCreateQuoteDialog(true)}>
                  Create your first quote
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow className="table-industrial">
                    <TableHead>Quote #</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Property</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredQuotes.map((quote) => (
                    <TableRow 
                      key={quote.id} 
                      className="table-industrial cursor-pointer hover:bg-muted/50"
                      onClick={() => handleQuoteClick(quote)}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 bg-primary/10 rounded flex items-center justify-center">
                            <FileText className="h-4 w-4 text-primary" />
                          </div>
                          <span className="font-mono text-sm">Q-{quote.id.slice(0, 6).toUpperCase()}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <p className="font-medium">{quote.customer?.first_name} {quote.customer?.last_name}</p>
                        <p className="text-xs text-muted-foreground">{quote.customer?.phone}</p>
                      </TableCell>
                      <TableCell>
                        {quote.property ? (
                          <div className="text-sm">
                            <p>{quote.property.address_line1}</p>
                            <p className="text-muted-foreground">{quote.property.city}</p>
                          </div>
                        ) : "-"}
                      </TableCell>
                      <TableCell>
                        <span className="font-mono font-semibold text-lg">{formatCurrency(quote.amount)}</span>
                      </TableCell>
                      <TableCell>
                        <Badge className={quoteStatusColors[quote.status]}>{quote.status}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">{formatDate(quote.created_at)}</span>
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => handleQuoteClick(quote)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="invoices">
          {filteredInvoices.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Receipt className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                <p className="text-muted-foreground">No invoices found</p>
                <Button className="mt-4" onClick={() => setShowCreateInvoiceDialog(true)}>
                  Create your first invoice
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow className="table-industrial">
                    <TableHead>Invoice #</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Job</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Due Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredInvoices.map((invoice) => (
                    <TableRow 
                      key={invoice.id} 
                      className="table-industrial cursor-pointer hover:bg-muted/50"
                      onClick={() => handleInvoiceClick(invoice)}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 bg-green-100 rounded flex items-center justify-center">
                            <Receipt className="h-4 w-4 text-green-600" />
                          </div>
                          <span className="font-mono text-sm">INV-{invoice.id.slice(0, 6).toUpperCase()}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <p className="font-medium">{invoice.customer?.first_name} {invoice.customer?.last_name}</p>
                      </TableCell>
                      <TableCell>
                        {invoice.job ? (
                          <span className="text-sm">{invoice.job.job_type}</span>
                        ) : "-"}
                      </TableCell>
                      <TableCell>
                        <span className="font-mono font-semibold text-lg">{formatCurrency(invoice.amount)}</span>
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm ${invoice.status === "OVERDUE" ? "text-red-600 font-medium" : "text-muted-foreground"}`}>
                          {formatDate(invoice.due_date)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge className={invoiceStatusColors[invoice.status]}>{invoice.status}</Badge>
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Button size="sm" variant="ghost" onClick={() => handleInvoiceClick(invoice)}>
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Quote Detail Modal */}
      <QuoteDetailModal
        quote={selectedQuote}
        open={showQuoteDetail}
        onOpenChange={setShowQuoteDetail}
        onUpdate={fetchQuotes}
        formatCurrency={formatCurrency}
        formatDate={formatDate}
      />

      {/* Invoice Detail Modal */}
      <InvoiceDetailModal
        invoice={selectedInvoice}
        open={showInvoiceDetail}
        onOpenChange={setShowInvoiceDetail}
        onUpdate={fetchInvoices}
        formatCurrency={formatCurrency}
        formatDate={formatDate}
      />
    </Layout>
  );
}

function QuoteDetailModal({ quote, open, onOpenChange, onUpdate, formatCurrency, formatDate }) {
  const [updating, setUpdating] = useState(false);

  const handleStatusUpdate = async (newStatus) => {
    if (!quote) return;
    setUpdating(true);
    try {
      await quoteAPI.update(quote.id, { ...quote, status: newStatus });
      toast.success(`Quote marked as ${newStatus}`);
      onUpdate();
      if (newStatus === "ACCEPTED") {
        toast.info("You can now create a job from this quote");
      }
    } catch (error) {
      toast.error("Failed to update quote");
    } finally {
      setUpdating(false);
    }
  };

  const handleSendQuote = async () => {
    await handleStatusUpdate("SENT");
    toast.success("Quote sent to customer!");
  };

  if (!quote) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Quote Q-{quote.id.slice(0, 6).toUpperCase()}
          </DialogTitle>
          <DialogDescription>
            <Badge className={quoteStatusColors[quote.status]}>{quote.status}</Badge>
            <span className="ml-2 text-muted-foreground">Created {formatDate(quote.created_at)}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Amount */}
          <div className="text-center py-6 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground mb-1">Quote Amount</p>
            <p className="text-4xl font-bold font-mono">{formatCurrency(quote.amount)}</p>
          </div>

          {/* Customer & Property */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-muted/30 rounded-lg p-4">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <User className="h-4 w-4" /> Customer
              </h4>
              <p className="font-medium">{quote.customer?.first_name} {quote.customer?.last_name}</p>
              <p className="text-sm text-muted-foreground">{quote.customer?.phone}</p>
              {quote.customer?.email && <p className="text-sm text-muted-foreground">{quote.customer?.email}</p>}
            </div>
            {quote.property && (
              <div className="bg-muted/30 rounded-lg p-4">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <MapPin className="h-4 w-4" /> Property
                </h4>
                <p>{quote.property.address_line1}</p>
                <p className="text-sm text-muted-foreground">{quote.property.city}, {quote.property.state}</p>
              </div>
            )}
          </div>

          {/* Description */}
          {quote.description && (
            <div>
              <h4 className="font-medium mb-2">Description</h4>
              <p className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-4">{quote.description}</p>
            </div>
          )}

          <Separator />

          {/* Actions */}
          <div>
            <h4 className="font-medium mb-3">Actions</h4>
            <div className="flex flex-wrap gap-2">
              {quote.status === "DRAFT" && (
                <Button onClick={handleSendQuote} disabled={updating}>
                  <Send className="h-4 w-4 mr-2" />
                  Send to Customer
                </Button>
              )}
              {quote.status === "SENT" && (
                <>
                  <Button onClick={() => handleStatusUpdate("ACCEPTED")} disabled={updating} className="bg-green-600 hover:bg-green-700">
                    <Check className="h-4 w-4 mr-2" />
                    Mark Accepted
                  </Button>
                  <Button variant="outline" onClick={() => handleStatusUpdate("DECLINED")} disabled={updating}>
                    <X className="h-4 w-4 mr-2" />
                    Mark Declined
                  </Button>
                </>
              )}
              {quote.status === "ACCEPTED" && (
                <Button variant="outline">
                  <Briefcase className="h-4 w-4 mr-2" />
                  Create Job
                </Button>
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function InvoiceDetailModal({ invoice, open, onOpenChange, onUpdate, formatCurrency, formatDate }) {
  const [updating, setUpdating] = useState(false);

  const handleMarkPaid = async () => {
    if (!invoice) return;
    setUpdating(true);
    try {
      const token = localStorage.getItem('fieldos_token');
      await axios.post(`${API_URL}/api/v1/invoices/${invoice.id}/mark-paid`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("Invoice marked as paid!");
      onUpdate();
      onOpenChange(false);
    } catch (error) {
      toast.error("Failed to update invoice");
    } finally {
      setUpdating(false);
    }
  };

  if (!invoice) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Receipt className="h-5 w-5" />
            Invoice INV-{invoice.id.slice(0, 6).toUpperCase()}
          </DialogTitle>
          <DialogDescription>
            <Badge className={invoiceStatusColors[invoice.status]}>{invoice.status}</Badge>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="text-center py-6 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground mb-1">Amount Due</p>
            <p className="text-4xl font-bold font-mono">{formatCurrency(invoice.amount)}</p>
            <p className="text-sm text-muted-foreground mt-2">Due: {formatDate(invoice.due_date)}</p>
          </div>

          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="font-medium mb-2">Customer</h4>
            <p className="font-medium">{invoice.customer?.first_name} {invoice.customer?.last_name}</p>
          </div>

          {invoice.job && (
            <div className="bg-muted/30 rounded-lg p-4">
              <h4 className="font-medium mb-2">Related Job</h4>
              <p>{invoice.job.job_type}</p>
            </div>
          )}

          {invoice.status !== "PAID" && (
            <Button className="w-full" onClick={handleMarkPaid} disabled={updating}>
              <CreditCard className="h-4 w-4 mr-2" />
              Mark as Paid
            </Button>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CreateQuoteDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    customer_id: "",
    property_id: "",
    job_id: "",
    amount: "",
    description: "",
    status: "DRAFT",
  });
  const [customers, setCustomers] = useState([]);
  const [properties, setProperties] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      fetchCustomers();
      fetchJobs();
    }
  }, [open]);

  useEffect(() => {
    if (formData.customer_id) {
      fetchProperties(formData.customer_id);
    }
  }, [formData.customer_id]);

  const fetchCustomers = async () => {
    try {
      const response = await customerAPI.list();
      setCustomers(response.data);
    } catch (error) {
      console.error("Failed to load customers");
    }
  };

  const fetchProperties = async (customerId) => {
    try {
      const response = await propertyAPI.list(customerId);
      setProperties(response.data);
    } catch (error) {
      console.error("Failed to load properties");
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await jobAPI.list();
      setJobs(response.data);
    } catch (error) {
      console.error("Failed to load jobs");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await quoteAPI.create({
        ...formData,
        amount: parseFloat(formData.amount),
      });
      toast.success("Quote created successfully");
      onOpenChange(false);
      setFormData({ customer_id: "", property_id: "", job_id: "", amount: "", description: "", status: "DRAFT" });
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create quote");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="btn-industrial">
          <Plus className="h-4 w-4 mr-2" />
          NEW QUOTE
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="font-heading">Create Quote</DialogTitle>
          <DialogDescription>Create a new service quote for a customer</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Customer *</Label>
              <Select value={formData.customer_id} onValueChange={(v) => setFormData({...formData, customer_id: v, property_id: ""})}>
                <SelectTrigger><SelectValue placeholder="Select customer" /></SelectTrigger>
                <SelectContent>
                  {customers.map((c) => (
                    <SelectItem key={c.id} value={c.id}>{c.first_name} {c.last_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {formData.customer_id && properties.length > 0 && (
              <div className="space-y-2">
                <Label>Property</Label>
                <Select value={formData.property_id} onValueChange={(v) => setFormData({...formData, property_id: v})}>
                  <SelectTrigger><SelectValue placeholder="Select property" /></SelectTrigger>
                  <SelectContent>
                    {properties.map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.address_line1}, {p.city}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label>Link to Job (optional)</Label>
              <Select value={formData.job_id || "none"} onValueChange={(v) => setFormData({...formData, job_id: v === "none" ? "" : v})}>
                <SelectTrigger><SelectValue placeholder="Select job" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No job</SelectItem>
                  {jobs.map((j) => (
                    <SelectItem key={j.id} value={j.id}>{j.job_type} - {j.customer?.first_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Amount ($) *</Label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input type="number" step="0.01" min="0" className="pl-9" value={formData.amount} onChange={(e) => setFormData({...formData, amount: e.target.value})} required />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea placeholder="Quote details..." value={formData.description} onChange={(e) => setFormData({...formData, description: e.target.value})} rows={3} />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={loading || !formData.customer_id}>{loading ? "Creating..." : "Create Quote"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CreateInvoiceDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    customer_id: "",
    job_id: "",
    amount: "",
    due_date: "",
  });
  const [customers, setCustomers] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      fetchCustomers();
      fetchJobs();
      // Default due date to 30 days from now
      const dueDate = new Date();
      dueDate.setDate(dueDate.getDate() + 30);
      setFormData(prev => ({...prev, due_date: dueDate.toISOString().split('T')[0]}));
    }
  }, [open]);

  const fetchCustomers = async () => {
    try {
      const response = await customerAPI.list();
      setCustomers(response.data);
    } catch (error) {
      console.error("Failed to load customers");
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await jobAPI.list();
      setJobs(response.data.filter(j => j.status === "COMPLETED"));
    } catch (error) {
      console.error("Failed to load jobs");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const token = localStorage.getItem('fieldos_token');
      await axios.post(`${API_URL}/api/v1/invoices`, {
        ...formData,
        amount: parseFloat(formData.amount),
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("Invoice created successfully");
      onOpenChange(false);
      setFormData({ customer_id: "", job_id: "", amount: "", due_date: "" });
      onSuccess();
    } catch (error) {
      toast.error("Failed to create invoice");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="btn-industrial">
          <Plus className="h-4 w-4 mr-2" />
          NEW INVOICE
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="font-heading">Create Invoice</DialogTitle>
          <DialogDescription>Create a new invoice for a completed job</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Customer *</Label>
              <Select value={formData.customer_id} onValueChange={(v) => setFormData({...formData, customer_id: v})}>
                <SelectTrigger><SelectValue placeholder="Select customer" /></SelectTrigger>
                <SelectContent>
                  {customers.map((c) => (
                    <SelectItem key={c.id} value={c.id}>{c.first_name} {c.last_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Completed Job *</Label>
              <Select value={formData.job_id} onValueChange={(v) => setFormData({...formData, job_id: v})}>
                <SelectTrigger><SelectValue placeholder="Select completed job" /></SelectTrigger>
                <SelectContent>
                  {jobs.map((j) => (
                    <SelectItem key={j.id} value={j.id}>{j.job_type} - {j.customer?.first_name} {j.customer?.last_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Amount ($) *</Label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input type="number" step="0.01" min="0" className="pl-9" value={formData.amount} onChange={(e) => setFormData({...formData, amount: e.target.value})} required />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Due Date *</Label>
              <Input type="date" value={formData.due_date} onChange={(e) => setFormData({...formData, due_date: e.target.value})} required />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={loading || !formData.customer_id || !formData.job_id}>{loading ? "Creating..." : "Create Invoice"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
