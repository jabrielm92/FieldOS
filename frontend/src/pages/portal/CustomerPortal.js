import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Textarea } from "../../components/ui/textarea";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Separator } from "../../components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { toast } from "sonner";
import { 
  Calendar, 
  Clock, 
  MapPin, 
  Phone, 
  Mail,
  User,
  Wrench,
  CheckCircle,
  XCircle,
  FileText,
  MessageSquare,
  Building2,
  DollarSign,
  CalendarCheck,
  Loader2,
  Star,
  Receipt,
  CreditCard,
  Send,
  History,
  PlusCircle,
  Home,
  AlertTriangle
} from "lucide-react";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const statusColors = {
  BOOKED: "bg-yellow-100 text-yellow-800",
  EN_ROUTE: "bg-purple-100 text-purple-800",
  ON_SITE: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-gray-100 text-gray-800",
};

const quoteStatusColors = {
  DRAFT: "bg-gray-100 text-gray-800",
  SENT: "bg-blue-100 text-blue-800",
  ACCEPTED: "bg-green-100 text-green-800",
  DECLINED: "bg-red-100 text-red-800",
};

const invoiceStatusColors = {
  DRAFT: "bg-gray-100 text-gray-800",
  SENT: "bg-blue-100 text-blue-800",
  PARTIALLY_PAID: "bg-yellow-100 text-yellow-800",
  PAID: "bg-green-100 text-green-800",
  OVERDUE: "bg-red-100 text-red-800",
};

const urgencyColors = {
  EMERGENCY: "bg-red-500 text-white",
  URGENT: "bg-orange-500 text-white",
  ROUTINE: "bg-blue-500 text-white",
};

export default function CustomerPortal() {
  const { token } = useParams();
  const [portalData, setPortalData] = useState(null);
  const [branding, setBranding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("home");
  
  // Dialog states
  const [showRescheduleDialog, setShowRescheduleDialog] = useState(false);
  const [showReviewDialog, setShowReviewDialog] = useState(false);
  const [showNoteDialog, setShowNoteDialog] = useState(false);
  const [showServiceRequestDialog, setShowServiceRequestDialog] = useState(false);
  const [showProfileDialog, setShowProfileDialog] = useState(false);
  
  // Form states
  const [selectedJob, setSelectedJob] = useState(null);
  const [rescheduleMessage, setRescheduleMessage] = useState("");
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  
  // Service request form
  const [serviceRequest, setServiceRequest] = useState({
    issue_description: "",
    urgency: "ROUTINE",
    property_id: "",
    preferred_date: "",
    preferred_time_slot: "morning"
  });
  
  // Profile form
  const [profileData, setProfileData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: ""
  });
  
  // Messages
  const [messages, setMessages] = useState([]);
  const [serviceHistory, setServiceHistory] = useState([]);

  useEffect(() => {
    fetchPortalData();
    fetchBranding();
  }, [token]);

  const fetchPortalData = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/portal/${token}`);
      setPortalData(response.data);
      setProfileData({
        first_name: response.data.customer?.first_name || "",
        last_name: response.data.customer?.last_name || "",
        email: response.data.customer?.email || "",
        phone: response.data.customer?.phone || ""
      });
    } catch (err) {
      setError("Invalid or expired portal link");
    } finally {
      setLoading(false);
    }
  };

  const fetchBranding = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/portal/${token}/branding`);
      setBranding(response.data);
      
      // Apply branding to CSS variables
      if (response.data.primary_color) {
        document.documentElement.style.setProperty('--portal-primary', response.data.primary_color);
      }
    } catch (err) {
      console.error("Error fetching branding:", err);
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/portal/${token}/messages`);
      setMessages(response.data.messages || []);
    } catch (err) {
      console.error("Error fetching messages:", err);
    }
  };

  const fetchServiceHistory = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/portal/${token}/service-history`);
      setServiceHistory(response.data.service_history || []);
    } catch (err) {
      console.error("Error fetching service history:", err);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === "messages" && messages.length === 0) {
      fetchMessages();
    }
    if (tab === "history" && serviceHistory.length === 0) {
      fetchServiceHistory();
    }
  };

  const handleQuoteResponse = async (quoteId, action) => {
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/api/v1/portal/${token}/quote/${quoteId}/respond?action=${action}`);
      toast.success(action === 'accept' ? 'Quote accepted!' : 'Quote declined');
      fetchPortalData();
    } catch (err) {
      toast.error('Failed to submit response');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRescheduleRequest = async () => {
    if (!selectedJob || !rescheduleMessage.trim()) return;
    
    setSubmitting(true);
    try {
      await axios.post(
        `${API_URL}/api/v1/portal/${token}/reschedule-request?job_id=${selectedJob.id}&message=${encodeURIComponent(rescheduleMessage)}`
      );
      toast.success('Reschedule request submitted');
      setShowRescheduleDialog(false);
      setRescheduleMessage("");
      setSelectedJob(null);
    } catch (err) {
      toast.error('Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitReview = async () => {
    if (!selectedJob) return;
    
    setSubmitting(true);
    try {
      await axios.post(
        `${API_URL}/api/v1/portal/${token}/review?job_id=${selectedJob.id}&rating=${reviewRating}&comment=${encodeURIComponent(reviewComment || '')}`
      );
      toast.success('Thank you for your review!');
      setShowReviewDialog(false);
      setReviewRating(5);
      setReviewComment("");
      setSelectedJob(null);
      fetchPortalData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitNote = async () => {
    if (!noteContent.trim()) return;
    
    setSubmitting(true);
    try {
      await axios.post(
        `${API_URL}/api/v1/portal/${token}/add-note?note=${encodeURIComponent(noteContent)}${selectedJob ? `&job_id=${selectedJob.id}` : ''}`
      );
      toast.success('Message sent successfully');
      setShowNoteDialog(false);
      setNoteContent("");
      setSelectedJob(null);
    } catch (err) {
      toast.error('Failed to send message');
    } finally {
      setSubmitting(false);
    }
  };

  const handleServiceRequest = async () => {
    if (!serviceRequest.issue_description.trim()) {
      toast.error('Please describe the issue');
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/api/v1/portal/${token}/request-service`, null, {
        params: {
          issue_description: serviceRequest.issue_description,
          urgency: serviceRequest.urgency,
          property_id: serviceRequest.property_id || undefined,
          preferred_date: serviceRequest.preferred_date || undefined,
          preferred_time_slot: serviceRequest.preferred_time_slot || undefined
        }
      });
      toast.success('Service request submitted! We will contact you shortly.');
      setShowServiceRequestDialog(false);
      setServiceRequest({
        issue_description: "",
        urgency: "ROUTINE",
        property_id: "",
        preferred_date: "",
        preferred_time_slot: "morning"
      });
    } catch (err) {
      toast.error('Failed to submit service request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateProfile = async () => {
    setSubmitting(true);
    try {
      await axios.put(`${API_URL}/api/v1/portal/${token}/profile`, null, {
        params: profileData
      });
      toast.success('Profile updated successfully');
      setShowProfileDialog(false);
      fetchPortalData();
    } catch (err) {
      toast.error('Failed to update profile');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString(undefined, {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="max-w-md w-full text-center">
          <CardContent className="pt-6">
            <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">Link Expired or Invalid</h2>
            <p className="text-muted-foreground">
              This portal link is no longer valid. Please contact us to get a new link.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { customer, company, upcoming_appointments, past_appointments, pending_quotes, pending_invoices, properties } = portalData;
  const companyName = branding?.company_name || company?.name;
  const primaryColor = branding?.primary_color || "#0066CC";

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header 
        className="py-6 px-4 text-white"
        style={{ backgroundColor: primaryColor }}
      >
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {branding?.logo_url ? (
                <img src={branding.logo_url} alt={companyName} className="h-10 object-contain" />
              ) : (
                <Building2 className="h-8 w-8" />
              )}
              <div>
                <h1 className="text-xl font-bold font-heading">{companyName}</h1>
                <p className="text-sm opacity-90">{branding?.portal_title || "Customer Portal"}</p>
              </div>
            </div>
            <Button 
              variant="secondary" 
              size="sm"
              onClick={() => setShowProfileDialog(true)}
              data-testid="edit-profile-btn"
            >
              <User className="h-4 w-4 mr-1" />
              Profile
            </Button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="border-b bg-white sticky top-0 z-10">
        <div className="max-w-4xl mx-auto">
          <Tabs value={activeTab} onValueChange={handleTabChange}>
            <TabsList className="w-full justify-start h-12 bg-transparent border-none rounded-none">
              <TabsTrigger value="home" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none">
                <Home className="h-4 w-4 mr-1" />
                Home
              </TabsTrigger>
              <TabsTrigger value="appointments" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none">
                <CalendarCheck className="h-4 w-4 mr-1" />
                Appointments
              </TabsTrigger>
              <TabsTrigger value="invoices" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none">
                <Receipt className="h-4 w-4 mr-1" />
                Invoices
              </TabsTrigger>
              <TabsTrigger value="history" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none">
                <History className="h-4 w-4 mr-1" />
                History
              </TabsTrigger>
              <TabsTrigger value="messages" className="data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none">
                <MessageSquare className="h-4 w-4 mr-1" />
                Messages
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      <main className="max-w-4xl mx-auto p-4 py-6 space-y-6">
        {/* Home Tab */}
        {activeTab === "home" && (
          <>
            {/* Welcome Card */}
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div 
                    className="w-14 h-14 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: `${primaryColor}20` }}
                  >
                    <User className="h-7 w-7" style={{ color: primaryColor }} />
                  </div>
                  <div className="flex-1">
                    <h2 className="text-xl font-bold font-heading">
                      Welcome, {customer?.first_name}!
                    </h2>
                    <p className="text-muted-foreground">
                      {branding?.portal_welcome_message || "View appointments, pay invoices, request service, and more."}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Button 
                variant="outline" 
                className="h-auto py-4 flex flex-col items-center gap-2"
                onClick={() => setShowServiceRequestDialog(true)}
                data-testid="request-service-btn"
              >
                <PlusCircle className="h-6 w-6" style={{ color: primaryColor }} />
                <span className="text-sm">Request Service</span>
              </Button>
              <Button 
                variant="outline" 
                className="h-auto py-4 flex flex-col items-center gap-2"
                onClick={() => handleTabChange("invoices")}
              >
                <CreditCard className="h-6 w-6 text-green-600" />
                <span className="text-sm">Pay Invoice</span>
              </Button>
              <Button 
                variant="outline" 
                className="h-auto py-4 flex flex-col items-center gap-2"
                onClick={() => {
                  setSelectedJob(null);
                  setShowNoteDialog(true);
                }}
              >
                <Send className="h-6 w-6 text-blue-600" />
                <span className="text-sm">Send Message</span>
              </Button>
              <Button 
                variant="outline" 
                className="h-auto py-4 flex flex-col items-center gap-2"
                asChild
              >
                <a href={`tel:${branding?.portal_support_phone || company?.primary_phone}`}>
                  <Phone className="h-6 w-6 text-orange-600" />
                  <span className="text-sm">Call Us</span>
                </a>
              </Button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-4">
              <Card className="text-center">
                <CardContent className="pt-4">
                  <div className="text-3xl font-bold" style={{ color: primaryColor }}>
                    {upcoming_appointments?.length || 0}
                  </div>
                  <p className="text-sm text-muted-foreground">Upcoming</p>
                </CardContent>
              </Card>
              <Card className="text-center">
                <CardContent className="pt-4">
                  <div className="text-3xl font-bold text-red-600">
                    ${pending_invoices?.reduce((sum, inv) => sum + (inv.amount || 0), 0).toFixed(0) || 0}
                  </div>
                  <p className="text-sm text-muted-foreground">Due</p>
                </CardContent>
              </Card>
              <Card className="text-center">
                <CardContent className="pt-4">
                  <div className="text-3xl font-bold text-yellow-600">
                    {pending_quotes?.length || 0}
                  </div>
                  <p className="text-sm text-muted-foreground">Quotes</p>
                </CardContent>
              </Card>
            </div>

            {/* Urgent Items */}
            {(pending_invoices?.filter(i => i.status === "OVERDUE").length > 0) && (
              <Card className="border-red-200 bg-red-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-red-700 flex items-center gap-2 text-base">
                    <AlertTriangle className="h-5 w-5" />
                    Action Required
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-red-700">
                    You have {pending_invoices.filter(i => i.status === "OVERDUE").length} overdue invoice(s). 
                    Please make a payment to avoid service interruption.
                  </p>
                  <Button 
                    className="mt-3"
                    style={{ backgroundColor: primaryColor }}
                    onClick={() => handleTabChange("invoices")}
                  >
                    View Invoices
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Next Appointment */}
            {upcoming_appointments?.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <CalendarCheck className="h-5 w-5" style={{ color: primaryColor }} />
                    Next Appointment
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4">
                    <div 
                      className="text-center p-3 rounded-lg min-w-[80px]"
                      style={{ backgroundColor: `${primaryColor}15` }}
                    >
                      <span className="text-2xl font-bold" style={{ color: primaryColor }}>
                        {new Date(upcoming_appointments[0].service_window_start).getDate()}
                      </span>
                      <br />
                      <span className="text-xs uppercase" style={{ color: primaryColor }}>
                        {new Date(upcoming_appointments[0].service_window_start).toLocaleDateString(undefined, { month: 'short' })}
                      </span>
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold">{upcoming_appointments[0].job_type} Service</p>
                      <p className="text-sm text-muted-foreground">
                        {formatTime(upcoming_appointments[0].service_window_start)} - {formatTime(upcoming_appointments[0].service_window_end)}
                      </p>
                      {upcoming_appointments[0].property && (
                        <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                          <MapPin className="h-3 w-3" />
                          {upcoming_appointments[0].property.address_line1}
                        </p>
                      )}
                    </div>
                    <Badge className={statusColors[upcoming_appointments[0].status]}>
                      {upcoming_appointments[0].status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Pending Quotes */}
            {pending_quotes?.filter(q => q.status === "SENT").length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <FileText className="h-5 w-5" style={{ color: primaryColor }} />
                    Quotes Awaiting Response
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {pending_quotes.filter(q => q.status === "SENT").map((quote) => (
                    <div key={quote.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <p className="font-semibold">${quote.amount?.toFixed(2)}</p>
                        <p className="text-sm text-muted-foreground">{quote.description}</p>
                      </div>
                      <div className="flex gap-2">
                        <Button 
                          size="sm"
                          onClick={() => handleQuoteResponse(quote.id, 'accept')}
                          disabled={submitting}
                          style={{ backgroundColor: primaryColor }}
                        >
                          Accept
                        </Button>
                        <Button 
                          size="sm"
                          variant="outline"
                          onClick={() => handleQuoteResponse(quote.id, 'decline')}
                          disabled={submitting}
                        >
                          Decline
                        </Button>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Appointments Tab */}
        {activeTab === "appointments" && (
          <>
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-bold">Appointments</h2>
              <Button onClick={() => setShowServiceRequestDialog(true)} style={{ backgroundColor: primaryColor }}>
                <PlusCircle className="h-4 w-4 mr-2" />
                Request Service
              </Button>
            </div>

            {upcoming_appointments?.length === 0 && past_appointments?.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  No appointments scheduled yet.
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Upcoming */}
                {upcoming_appointments?.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-medium text-muted-foreground">Upcoming</h3>
                    {upcoming_appointments.map((job) => (
                      <Card key={job.id} data-testid={`appointment-${job.id}`}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex gap-3">
                              <div 
                                className="text-center p-2 rounded min-w-[60px]"
                                style={{ backgroundColor: `${primaryColor}15` }}
                              >
                                <span className="text-lg font-bold" style={{ color: primaryColor }}>
                                  {new Date(job.service_window_start).getDate()}
                                </span>
                                <br />
                                <span className="text-xs uppercase" style={{ color: primaryColor }}>
                                  {new Date(job.service_window_start).toLocaleDateString(undefined, { month: 'short' })}
                                </span>
                              </div>
                              <div>
                                <p className="font-semibold">{job.job_type} Service</p>
                                <p className="text-sm text-muted-foreground">
                                  {formatTime(job.service_window_start)} - {formatTime(job.service_window_end)}
                                </p>
                                {job.property && (
                                  <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                                    <MapPin className="h-3 w-3" />
                                    {job.property.address_line1}, {job.property.city}
                                  </p>
                                )}
                                {job.technician && (
                                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Wrench className="h-3 w-3" />
                                    Technician: {job.technician.name}
                                  </p>
                                )}
                              </div>
                            </div>
                            <div className="text-right">
                              <Badge className={statusColors[job.status]}>{job.status}</Badge>
                              <Button 
                                variant="ghost" 
                                size="sm"
                                className="mt-2"
                                onClick={() => {
                                  setSelectedJob(job);
                                  setShowRescheduleDialog(true);
                                }}
                              >
                                Reschedule
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}

                {/* Past */}
                {past_appointments?.length > 0 && (
                  <div className="space-y-3 mt-6">
                    <h3 className="text-sm font-medium text-muted-foreground">Past Appointments</h3>
                    {past_appointments.map((job) => (
                      <Card key={job.id} className="opacity-75">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium">{job.job_type}</p>
                              <p className="text-sm text-muted-foreground">
                                {formatDate(job.service_window_start)}
                              </p>
                            </div>
                            {job.review ? (
                              <div className="flex items-center gap-1">
                                {[...Array(5)].map((_, i) => (
                                  <Star 
                                    key={i} 
                                    className={`h-4 w-4 ${i < job.review.rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`} 
                                  />
                                ))}
                              </div>
                            ) : (
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={() => {
                                  setSelectedJob(job);
                                  setShowReviewDialog(true);
                                }}
                              >
                                <Star className="h-4 w-4 mr-1" />
                                Review
                              </Button>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* Invoices Tab */}
        {activeTab === "invoices" && (
          <>
            <h2 className="text-lg font-bold">Invoices</h2>
            
            {pending_invoices?.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  No invoices at this time.
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {pending_invoices?.map((invoice) => (
                  <Card key={invoice.id} data-testid={`invoice-${invoice.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-2xl font-bold font-mono">
                              ${invoice.amount?.toFixed(2)}
                            </span>
                            <Badge className={invoiceStatusColors[invoice.status]}>
                              {invoice.status}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            Due: {formatDate(invoice.due_date)}
                          </p>
                          {invoice.job && (
                            <p className="text-xs text-muted-foreground mt-1">
                              For: {invoice.job.job_type} service
                            </p>
                          )}
                        </div>
                        <Button 
                          disabled
                          style={{ backgroundColor: primaryColor }}
                        >
                          <CreditCard className="h-4 w-4 mr-2" />
                          Pay Now
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground text-center mt-3 pt-3 border-t">
                        Online payments coming soon. Please contact us to arrange payment.
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {/* History Tab */}
        {activeTab === "history" && (
          <>
            <h2 className="text-lg font-bold">Service History</h2>
            
            {serviceHistory.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  No service history yet.
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {serviceHistory.map((job) => (
                  <Card key={job.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-semibold">{job.job_type}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatDate(job.service_window_start)}
                          </p>
                          {job.property && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {job.property.address_line1}
                            </p>
                          )}
                          {job.quote_amount && (
                            <p className="text-sm font-medium mt-1">
                              ${job.quote_amount.toFixed(2)}
                            </p>
                          )}
                        </div>
                        <div className="text-right">
                          <Badge className={statusColors[job.status]}>{job.status}</Badge>
                          {job.invoice && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Invoice: {job.invoice.status}
                            </p>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {/* Messages Tab */}
        {activeTab === "messages" && (
          <>
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-bold">Messages</h2>
              <Button 
                onClick={() => {
                  setSelectedJob(null);
                  setShowNoteDialog(true);
                }}
                style={{ backgroundColor: primaryColor }}
              >
                <Send className="h-4 w-4 mr-2" />
                New Message
              </Button>
            </div>
            
            {messages.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  No messages yet.
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="p-4 space-y-3">
                  {messages.map((msg, idx) => (
                    <div 
                      key={idx}
                      className={`p-3 rounded-lg max-w-[80%] ${
                        msg.direction === "INBOUND" 
                          ? "bg-muted" 
                          : "bg-primary/10 ml-auto"
                      }`}
                    >
                      <p className="text-sm">{msg.content}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(msg.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Contact Footer */}
        <Card className="bg-muted">
          <CardContent className="p-6 text-center">
            <h3 className="font-bold mb-2">Need Help?</h3>
            <p className="text-muted-foreground mb-4">
              Contact {companyName} directly:
            </p>
            <div className="flex justify-center gap-4">
              <Button variant="outline" asChild>
                <a href={`tel:${branding?.portal_support_phone || company?.primary_phone}`}>
                  <Phone className="h-4 w-4 mr-2" />
                  Call
                </a>
              </Button>
              {branding?.portal_support_email && (
                <Button variant="outline" asChild>
                  <a href={`mailto:${branding.portal_support_email}`}>
                    <Mail className="h-4 w-4 mr-2" />
                    Email
                  </a>
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </main>

      {/* Dialogs */}
      
      {/* Service Request Dialog */}
      <Dialog open={showServiceRequestDialog} onOpenChange={setShowServiceRequestDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Request Service</DialogTitle>
            <DialogDescription>
              Tell us what you need and we'll get back to you.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Issue Description *</Label>
              <Textarea
                placeholder="Please describe the issue or service needed..."
                value={serviceRequest.issue_description}
                onChange={(e) => setServiceRequest(prev => ({ ...prev, issue_description: e.target.value }))}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label>Urgency</Label>
              <Select 
                value={serviceRequest.urgency} 
                onValueChange={(value) => setServiceRequest(prev => ({ ...prev, urgency: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ROUTINE">Routine - Can wait a few days</SelectItem>
                  <SelectItem value="URGENT">Urgent - Need service soon</SelectItem>
                  <SelectItem value="EMERGENCY">Emergency - Need immediate help</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {properties?.length > 0 && (
              <div className="space-y-2">
                <Label>Property</Label>
                <Select 
                  value={serviceRequest.property_id} 
                  onValueChange={(value) => setServiceRequest(prev => ({ ...prev, property_id: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select property" />
                  </SelectTrigger>
                  <SelectContent>
                    {properties.map(prop => (
                      <SelectItem key={prop.id} value={prop.id}>
                        {prop.address_line1}, {prop.city}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Preferred Date</Label>
                <Input 
                  type="date" 
                  value={serviceRequest.preferred_date}
                  onChange={(e) => setServiceRequest(prev => ({ ...prev, preferred_date: e.target.value }))}
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>
              <div className="space-y-2">
                <Label>Preferred Time</Label>
                <Select 
                  value={serviceRequest.preferred_time_slot} 
                  onValueChange={(value) => setServiceRequest(prev => ({ ...prev, preferred_time_slot: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="morning">Morning (8am-12pm)</SelectItem>
                    <SelectItem value="afternoon">Afternoon (12pm-4pm)</SelectItem>
                    <SelectItem value="evening">Evening (4pm-7pm)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowServiceRequestDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleServiceRequest} 
              disabled={submitting || !serviceRequest.issue_description.trim()}
              style={{ backgroundColor: primaryColor }}
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Submit Request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reschedule Dialog */}
      <Dialog open={showRescheduleDialog} onOpenChange={setShowRescheduleDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request Reschedule</DialogTitle>
            <DialogDescription>
              Let us know your preferred times and we'll get back to you.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Please let us know what times work better for you..."
              value={rescheduleMessage}
              onChange={(e) => setRescheduleMessage(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRescheduleDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleRescheduleRequest} 
              disabled={submitting || !rescheduleMessage.trim()}
              style={{ backgroundColor: primaryColor }}
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Submit Request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review Dialog */}
      <Dialog open={showReviewDialog} onOpenChange={setShowReviewDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Leave a Review</DialogTitle>
            <DialogDescription>
              Share your experience with the {selectedJob?.job_type?.toLowerCase()} service.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Rating</label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setReviewRating(star)}
                    className="focus:outline-none"
                  >
                    <Star 
                      className={`h-8 w-8 transition-colors ${
                        star <= reviewRating 
                          ? 'text-yellow-400 fill-yellow-400' 
                          : 'text-gray-300 hover:text-yellow-200'
                      }`} 
                    />
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Comment (optional)</label>
              <Textarea
                placeholder="Tell us about your experience..."
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setShowReviewDialog(false);
              setReviewRating(5);
              setReviewComment("");
            }}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmitReview} 
              disabled={submitting}
              style={{ backgroundColor: primaryColor }}
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Submit Review"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Message Dialog */}
      <Dialog open={showNoteDialog} onOpenChange={setShowNoteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send a Message</DialogTitle>
            <DialogDescription>
              Send a message or note to {companyName}.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Type your message here..."
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setShowNoteDialog(false);
              setNoteContent("");
            }}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmitNote} 
              disabled={submitting || !noteContent.trim()}
              style={{ backgroundColor: primaryColor }}
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send Message"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Profile Dialog */}
      <Dialog open={showProfileDialog} onOpenChange={setShowProfileDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Profile</DialogTitle>
            <DialogDescription>
              Update your contact information.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>First Name</Label>
                <Input 
                  value={profileData.first_name}
                  onChange={(e) => setProfileData(prev => ({ ...prev, first_name: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Last Name</Label>
                <Input 
                  value={profileData.last_name}
                  onChange={(e) => setProfileData(prev => ({ ...prev, last_name: e.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input 
                type="email"
                value={profileData.email}
                onChange={(e) => setProfileData(prev => ({ ...prev, email: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input 
                value={profileData.phone}
                onChange={(e) => setProfileData(prev => ({ ...prev, phone: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowProfileDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleUpdateProfile} 
              disabled={submitting}
              style={{ backgroundColor: primaryColor }}
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
