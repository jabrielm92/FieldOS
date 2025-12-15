import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Textarea } from "../../components/ui/textarea";
import { Separator } from "../../components/ui/separator";
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
  Send
} from "lucide-react";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const statusColors = {
  BOOKED: "bg-yellow-100 text-yellow-800",
  EN_ROUTE: "bg-purple-100 text-purple-800",
  ON_SITE: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
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

export default function CustomerPortal() {
  const { token } = useParams();
  const [portalData, setPortalData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showRescheduleDialog, setShowRescheduleDialog] = useState(false);
  const [showReviewDialog, setShowReviewDialog] = useState(false);
  const [showNoteDialog, setShowNoteDialog] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [rescheduleMessage, setRescheduleMessage] = useState("");
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchPortalData();
  }, [token]);

  const fetchPortalData = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/portal/${token}`);
      setPortalData(response.data);
    } catch (err) {
      setError("Invalid or expired portal link");
    } finally {
      setLoading(false);
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
      toast.success('Note sent successfully');
      setShowNoteDialog(false);
      setNoteContent("");
      setSelectedJob(null);
    } catch (err) {
      toast.error('Failed to send note');
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

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-primary text-primary-foreground py-6 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <Building2 className="h-8 w-8" />
            <h1 className="text-2xl font-bold font-heading">{company?.name}</h1>
          </div>
          <p className="opacity-90">Customer Portal</p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-4 py-8 space-y-8">
        {/* Welcome */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 bg-primary/10 rounded-full flex items-center justify-center">
                <User className="h-7 w-7 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-bold font-heading">
                  Welcome, {customer?.first_name}!
                </h2>
                <p className="text-muted-foreground">
                  View appointments, pay invoices, approve quotes, and leave reviews.
                </p>
                <div className="flex flex-wrap gap-4 mt-3 text-sm">
                  <span className="flex items-center gap-1">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    {customer?.phone}
                  </span>
                  {customer?.email && (
                    <span className="flex items-center gap-1">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      {customer?.email}
                    </span>
                  )}
                </div>
                <div className="mt-4">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => {
                      setSelectedJob(null);
                      setShowNoteDialog(true);
                    }}
                  >
                    <Send className="h-4 w-4 mr-1" />
                    Send a Message
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Upcoming Appointments */}
        <section>
          <h3 className="text-lg font-bold font-heading mb-4 flex items-center gap-2">
            <CalendarCheck className="h-5 w-5 text-primary" />
            Upcoming Appointments
          </h3>
          
          {upcoming_appointments?.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No upcoming appointments scheduled.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {upcoming_appointments?.map((job) => (
                <Card key={job.id} className="overflow-hidden" data-testid={`appointment-${job.id}`}>
                  <div className="flex">
                    <div className="bg-primary/10 p-4 flex flex-col items-center justify-center min-w-[100px]">
                      <span className="text-2xl font-bold text-primary">
                        {new Date(job.service_window_start).getDate()}
                      </span>
                      <span className="text-sm text-primary uppercase">
                        {new Date(job.service_window_start).toLocaleDateString(undefined, { month: 'short' })}
                      </span>
                    </div>
                    <CardContent className="flex-1 p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-semibold">{job.job_type} Service</h4>
                          <Badge className={statusColors[job.status]} variant="outline">
                            {job.status}
                          </Badge>
                        </div>
                      </div>
                      
                      <div className="mt-3 space-y-2 text-sm">
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Clock className="h-4 w-4" />
                          <span>
                            {formatTime(job.service_window_start)} - {formatTime(job.service_window_end)}
                          </span>
                        </div>
                        {job.property && (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <MapPin className="h-4 w-4" />
                            <span>{job.property.address_line1}, {job.property.city}</span>
                          </div>
                        )}
                        {job.technician && (
                          <div className="flex items-center gap-2 text-muted-foreground">
                            <Wrench className="h-4 w-4" />
                            <span>Technician: {job.technician.name}</span>
                          </div>
                        )}
                      </div>
                      
                      <div className="mt-4">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            setSelectedJob(job);
                            setShowRescheduleDialog(true);
                          }}
                        >
                          <MessageSquare className="h-4 w-4 mr-1" />
                          Request Reschedule
                        </Button>
                      </div>
                    </CardContent>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>

        {/* Pending Invoices */}
        {pending_invoices?.length > 0 && (
          <section>
            <h3 className="text-lg font-bold font-heading mb-4 flex items-center gap-2">
              <Receipt className="h-5 w-5 text-red-500" />
              Pending Invoices
            </h3>
            
            <div className="space-y-4">
              {pending_invoices.map((invoice) => (
                <Card key={invoice.id} data-testid={`invoice-${invoice.id}`}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <DollarSign className="h-5 w-5 text-red-600" />
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
                    </div>
                    
                    <div className="mt-4">
                      <Button className="w-full" disabled>
                        <CreditCard className="h-4 w-4 mr-2" />
                        Pay Invoice (Coming Soon)
                      </Button>
                      <p className="text-xs text-muted-foreground text-center mt-2">
                        Please contact us to arrange payment
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* Pending Quotes */}
        {pending_quotes?.length > 0 && (
          <section>
            <h3 className="text-lg font-bold font-heading mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              Pending Quotes
            </h3>
            
            <div className="space-y-4">
              {pending_quotes.map((quote) => (
                <Card key={quote.id} data-testid={`quote-${quote.id}`}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <DollarSign className="h-5 w-5 text-green-600" />
                          <span className="text-2xl font-bold font-mono">
                            ${quote.amount?.toFixed(2)}
                          </span>
                          <Badge className={quoteStatusColors[quote.status]}>
                            {quote.status}
                          </Badge>
                        </div>
                        <p className="text-muted-foreground text-sm">
                          {quote.description || "Service quote"}
                        </p>
                        {quote.property && (
                          <p className="text-xs text-muted-foreground mt-1">
                            For: {quote.property.address_line1}, {quote.property.city}
                          </p>
                        )}
                      </div>
                    </div>
                    
                    {quote.status === "SENT" && (
                      <div className="flex gap-2 mt-4">
                        <Button 
                          className="flex-1"
                          onClick={() => handleQuoteResponse(quote.id, 'accept')}
                          disabled={submitting}
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Accept Quote
                        </Button>
                        <Button 
                          variant="outline"
                          className="flex-1"
                          onClick={() => handleQuoteResponse(quote.id, 'decline')}
                          disabled={submitting}
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          Decline
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* Properties */}
        {properties?.length > 0 && (
          <section>
            <h3 className="text-lg font-bold font-heading mb-4 flex items-center gap-2">
              <MapPin className="h-5 w-5 text-primary" />
              Your Properties
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {properties.map((property) => (
                <Card key={property.id}>
                  <CardContent className="p-4">
                    <p className="font-medium">{property.address_line1}</p>
                    {property.address_line2 && (
                      <p className="text-sm text-muted-foreground">{property.address_line2}</p>
                    )}
                    <p className="text-sm text-muted-foreground">
                      {property.city}, {property.state} {property.postal_code}
                    </p>
                    {property.system_type && (
                      <Badge variant="outline" className="mt-2">
                        {property.system_type}
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* Past Appointments with Reviews */}
        {past_appointments?.length > 0 && (
          <section>
            <h3 className="text-lg font-bold font-heading mb-4 flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Past Appointments
            </h3>
            
            <Card>
              <CardContent className="p-0">
                <div className="divide-y">
                  {past_appointments.map((job) => (
                    <div key={job.id} className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{job.job_type}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatDate(job.service_window_start)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
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
                              Leave Review
                            </Button>
                          )}
                        </div>
                      </div>
                      {job.review?.comment && (
                        <p className="text-sm text-muted-foreground mt-2 italic">
                          "{job.review.comment}"
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </section>
        )}

        {/* Contact */}
        <Card className="bg-muted">
          <CardContent className="p-6 text-center">
            <h3 className="font-bold mb-2">Need Help?</h3>
            <p className="text-muted-foreground mb-4">
              Contact {company?.name} directly:
            </p>
            <Button variant="outline" asChild>
              <a href={`tel:${company?.primary_phone}`}>
                <Phone className="h-4 w-4 mr-2" />
                {company?.primary_phone}
              </a>
            </Button>
          </CardContent>
        </Card>
      </main>

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
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                'Submit Request'
              )}
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
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                'Submit Review'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Note Dialog */}
      <Dialog open={showNoteDialog} onOpenChange={setShowNoteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send a Message</DialogTitle>
            <DialogDescription>
              Send a message or note to {company?.name}.
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
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Message
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
