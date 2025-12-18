import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Separator } from "../../components/ui/separator";
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
  DialogTrigger,
} from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { leadAPI, jobAPI, customerAPI, propertyAPI, conversationAPI } from "../../lib/api";
import { toast } from "sonner";
import { 
  Plus, Search, Phone, Mail, Clock, AlertTriangle, User, MapPin,
  Briefcase, MessageSquare, Edit, X, ChevronRight, Calendar, Trash2
} from "lucide-react";

const statusColors = {
  NEW: "bg-blue-100 text-blue-800 border-blue-200",
  CONTACTED: "bg-purple-100 text-purple-800 border-purple-200",
  QUALIFIED: "bg-cyan-100 text-cyan-800 border-cyan-200",
  JOB_BOOKED: "bg-green-100 text-green-800 border-green-200",
  NO_RESPONSE: "bg-gray-100 text-gray-800 border-gray-200",
  LOST: "bg-red-100 text-red-800 border-red-200",
};

const urgencyColors = {
  EMERGENCY: "bg-red-500 text-white",
  URGENT: "bg-orange-500 text-white",
  ROUTINE: "bg-blue-500 text-white",
};

export default function LeadsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [showLeadModal, setShowLeadModal] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchLeads();
    // Polling for real-time updates every 30 seconds
    const interval = setInterval(fetchLeads, 30000);
    return () => clearInterval(interval);
  }, [statusFilter, sourceFilter]);

  // Check URL param to open specific lead modal
  useEffect(() => {
    const openLeadId = searchParams.get('open');
    if (openLeadId && leads.length > 0) {
      const lead = leads.find(l => l.id === openLeadId);
      if (lead) {
        setSelectedLead(lead);
        setShowLeadModal(true);
        // Clear the URL param
        setSearchParams({});
      }
    }
  }, [leads, searchParams]);

  const fetchLeads = async () => {
    try {
      const filters = {};
      if (statusFilter !== "all") filters.status = statusFilter;
      if (sourceFilter !== "all") filters.source = sourceFilter;
      
      const response = await leadAPI.list(filters);
      setLeads(response.data);
    } catch (error) {
      toast.error("Failed to load leads");
    } finally {
      setLoading(false);
    }
  };

  const handleLeadClick = (lead) => {
    setSelectedLead(lead);
    setShowLeadModal(true);
  };

  const handleDeleteLead = async (leadId) => {
    if (!window.confirm("Are you sure you want to delete this lead?")) return;
    try {
      await leadAPI.delete(leadId);
      toast.success("Lead deleted");
      fetchLeads();
      setShowLeadModal(false);
    } catch (error) {
      toast.error("Failed to delete lead");
    }
  };

  const filteredLeads = leads.filter((lead) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      lead.issue_type?.toLowerCase().includes(searchLower) ||
      lead.description?.toLowerCase().includes(searchLower) ||
      lead.source?.toLowerCase().includes(searchLower) ||
      lead.customer?.first_name?.toLowerCase().includes(searchLower) ||
      lead.customer?.last_name?.toLowerCase().includes(searchLower) ||
      lead.customer?.phone?.includes(search)
    );
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Layout title="Leads" subtitle="Track and manage incoming leads">
      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search leads by issue, customer, phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="leads-search"
          />
        </div>
        
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]" data-testid="status-filter">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="NEW">New</SelectItem>
            <SelectItem value="CONTACTED">Contacted</SelectItem>
            <SelectItem value="QUALIFIED">Qualified</SelectItem>
            <SelectItem value="JOB_BOOKED">Job Booked</SelectItem>
            <SelectItem value="NO_RESPONSE">No Response</SelectItem>
            <SelectItem value="LOST">Lost</SelectItem>
          </SelectContent>
        </Select>

        <Select value={sourceFilter} onValueChange={setSourceFilter}>
          <SelectTrigger className="w-[180px]" data-testid="source-filter">
            <SelectValue placeholder="Source" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sources</SelectItem>
            <SelectItem value="VAPI_CALL">Vapi Call</SelectItem>
            <SelectItem value="MISSED_CALL_SMS">Missed Call SMS</SelectItem>
            <SelectItem value="WEB_FORM">Web Form</SelectItem>
            <SelectItem value="LANDING_PAGE">Landing Page</SelectItem>
            <SelectItem value="FB_LEAD">Facebook Lead</SelectItem>
            <SelectItem value="MANUAL">Manual</SelectItem>
          </SelectContent>
        </Select>

        <CreateLeadDialog 
          open={showCreateDialog} 
          onOpenChange={setShowCreateDialog}
          onSuccess={fetchLeads}
        />
      </div>

      {/* Leads Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filteredLeads.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No leads found</p>
            <Button 
              className="mt-4" 
              onClick={() => setShowCreateDialog(true)}
              data-testid="create-first-lead"
            >
              Create your first lead
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredLeads.map((lead) => (
            <LeadCard 
              key={lead.id} 
              lead={lead} 
              formatDate={formatDate}
              onClick={() => handleLeadClick(lead)}
            />
          ))}
        </div>
      )}

      {/* Lead Detail Modal */}
      <LeadDetailModal
        lead={selectedLead}
        open={showLeadModal}
        onOpenChange={setShowLeadModal}
        onUpdate={fetchLeads}
        onDelete={handleDeleteLead}
      />
    </Layout>
  );
}

function LeadCard({ lead, formatDate, onClick }) {
  return (
    <Card 
      className="card-industrial cursor-pointer hover:shadow-md transition-shadow relative overflow-hidden group"
      onClick={onClick}
      data-testid={`lead-card-${lead.id}`}
    >
      {/* Urgency indicator */}
      {lead.urgency === "EMERGENCY" && (
        <div className="absolute top-0 right-0 w-0 h-0 border-t-[40px] border-t-red-500 border-l-[40px] border-l-transparent">
          <AlertTriangle className="absolute -top-[35px] right-[5px] h-4 w-4 text-white" />
        </div>
      )}
      
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-medium">{lead.issue_type || "New Lead"}</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {lead.source?.replace('_', ' ')}
            </p>
          </div>
          <Badge className={urgencyColors[lead.urgency]}>
            {lead.urgency}
          </Badge>
        </div>
        
        {/* Customer Info */}
        <div className="space-y-1 mb-2">
          {(lead.caller_name || lead.customer) && (
            <div className="flex items-center gap-2 text-sm">
              <User className="h-3.5 w-3.5 text-muted-foreground" />
              <span>{lead.caller_name || (lead.customer ? `${lead.customer.first_name} ${lead.customer.last_name}` : "Unknown")}</span>
            </div>
          )}
          {(lead.caller_phone || lead.customer?.phone) && (
            <div className="flex items-center gap-2 text-sm">
              <Phone className="h-3.5 w-3.5 text-muted-foreground" />
              <span>{lead.caller_phone || lead.customer?.phone}</span>
            </div>
          )}
        </div>
        
        <p className="text-sm text-muted-foreground line-clamp-2 mb-4 min-h-[2.5rem]">
          {lead.description || "No description provided"}
        </p>
        
        <div className="flex items-center justify-between">
          <Badge className={statusColors[lead.status]} variant="outline">
            {lead.status?.replace('_', ' ')}
          </Badge>
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDate(lead.created_at)}
          </span>
        </div>

        {/* Hover indicator */}
        <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardContent>
    </Card>
  );
}

function LeadDetailModal({ lead, open, onOpenChange, onUpdate, onDelete }) {
  const [showCreateJob, setShowCreateJob] = useState(false);
  const [showEditLead, setShowEditLead] = useState(false);
  const [properties, setProperties] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (lead?.customer_id) {
      fetchProperties();
      fetchConversations();
    }
  }, [lead]);

  const fetchProperties = async () => {
    if (!lead?.customer_id) return;
    try {
      const response = await propertyAPI.list(lead.customer_id);
      setProperties(response.data);
    } catch (error) {
      console.error("Failed to fetch properties");
    }
  };

  const fetchConversations = async () => {
    try {
      const response = await conversationAPI.list();
      const customerConvs = response.data.filter(c => c.customer_id === lead?.customer_id);
      setConversations(customerConvs);
    } catch (error) {
      console.error("Failed to fetch conversations");
    }
  };

  const handleStatusUpdate = async (newStatus) => {
    if (!lead) return;
    setUpdating(true);
    try {
      await leadAPI.update(lead.id, { ...lead, status: newStatus });
      toast.success(`Lead marked as ${newStatus.replace('_', ' ')}`);
      onUpdate();
      onOpenChange(false);
    } catch (error) {
      toast.error("Failed to update lead status");
    } finally {
      setUpdating(false);
    }
  };

  if (!lead) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div>
              <DialogTitle className="font-heading text-xl">
                {lead.issue_type || "New Lead"}
              </DialogTitle>
              <DialogDescription className="flex items-center gap-2 mt-1">
                <Badge className={statusColors[lead.status]} variant="outline">
                  {lead.status?.replace('_', ' ')}
                </Badge>
                <Badge className={urgencyColors[lead.urgency]}>
                  {lead.urgency}
                </Badge>
                <span className="text-muted-foreground">
                  via {lead.source?.replace('_', ' ')}
                </span>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Customer Info */}
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <User className="h-4 w-4" />
              Customer Information
            </h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Name:</span>
                <p className="font-medium">
                  {lead.caller_name || (lead.customer ? `${lead.customer.first_name} ${lead.customer.last_name}` : "Unknown")}
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Phone:</span>
                <p className="font-medium flex items-center gap-1">
                  <Phone className="h-3 w-3" />
                  {lead.caller_phone || lead.customer?.phone || "Not provided"}
                </p>
              </div>
              {(lead.customer?.email) && (
                <div>
                  <span className="text-muted-foreground">Email:</span>
                  <p className="font-medium flex items-center gap-1">
                    <Mail className="h-3 w-3" />
                    {lead.customer.email}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Property Info */}
          {properties.length > 0 && (
            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Property
              </h4>
              {properties.map(prop => (
                <div key={prop.id} className="text-sm">
                  <p className="font-medium">{prop.address_line1}</p>
                  <p className="text-muted-foreground">{prop.city}, {prop.state} {prop.postal_code}</p>
                  {prop.system_type && (
                    <Badge variant="outline" className="mt-2">{prop.system_type}</Badge>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Issue Description */}
          <div>
            <h4 className="font-medium mb-2">Issue Description</h4>
            <p className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-4">
              {lead.description || "No description provided"}
            </p>
          </div>

          {/* Recent Messages */}
          {conversations.length > 0 && (
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Recent Messages
              </h4>
              <div className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-4">
                <p>{conversations.length} conversation(s) with this customer</p>
              </div>
            </div>
          )}

          <Separator />

          {/* Quick Actions */}
          <div>
            <h4 className="font-medium mb-3">Quick Actions</h4>
            <div className="flex flex-wrap gap-2">
              {lead.status !== "JOB_BOOKED" && (
                <Button 
                  onClick={() => setShowCreateJob(true)}
                  className="btn-industrial"
                >
                  <Briefcase className="h-4 w-4 mr-2" />
                  Create Job
                </Button>
              )}
              <Button variant="outline" onClick={() => setShowEditLead(true)}>
                <Edit className="h-4 w-4 mr-2" />
                Edit Lead
              </Button>
            </div>
          </div>

          {/* Status Update */}
          <div>
            <h4 className="font-medium mb-3">Update Status</h4>
            <div className="flex flex-wrap gap-2">
              {["NEW", "CONTACTED", "QUALIFIED", "NO_RESPONSE", "LOST"].map(status => (
                <Button
                  key={status}
                  variant={lead.status === status ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleStatusUpdate(status)}
                  disabled={updating || lead.status === status}
                >
                  {status.replace('_', ' ')}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>

        {/* Create Job Sub-Dialog */}
        <CreateJobFromLeadDialog
          lead={lead}
          properties={properties}
          open={showCreateJob}
          onOpenChange={setShowCreateJob}
          onSuccess={() => {
            handleStatusUpdate("JOB_BOOKED");
            setShowCreateJob(false);
          }}
        />

        {/* Edit Lead Sub-Dialog */}
        <EditLeadDialog
          lead={lead}
          open={showEditLead}
          onOpenChange={setShowEditLead}
          onSuccess={() => {
            onUpdate();
            setShowEditLead(false);
          }}
        />
      </DialogContent>
    </Dialog>
  );
}

function CreateJobFromLeadDialog({ lead, properties, open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    property_id: "",
    job_type: "DIAGNOSTIC",
    priority: lead?.urgency === "EMERGENCY" ? "EMERGENCY" : lead?.urgency === "URGENT" ? "HIGH" : "NORMAL",
    service_window_start: "",
    service_window_end: "",
    notes: lead?.description || "",
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (properties.length === 1) {
      setFormData(prev => ({ ...prev, property_id: properties[0].id }));
    }
  }, [properties]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!lead?.customer_id) return;
    
    setLoading(true);
    try {
      await jobAPI.create({
        customer_id: lead.customer_id,
        lead_id: lead.id,
        ...formData,
        service_window_start: new Date(formData.service_window_start).toISOString(),
        service_window_end: new Date(formData.service_window_end).toISOString(),
      });
      toast.success("Job created from lead!");
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Job from Lead</DialogTitle>
          <DialogDescription>
            Schedule a service appointment for this lead
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {properties.length > 1 && (
              <div className="space-y-2">
                <Label>Property</Label>
                <Select 
                  value={formData.property_id} 
                  onValueChange={(v) => setFormData({...formData, property_id: v})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select property" />
                  </SelectTrigger>
                  <SelectContent>
                    {properties.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.address_line1}, {p.city}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Job Type</Label>
                <Select 
                  value={formData.job_type} 
                  onValueChange={(v) => setFormData({...formData, job_type: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="DIAGNOSTIC">Diagnostic</SelectItem>
                    <SelectItem value="REPAIR">Repair</SelectItem>
                    <SelectItem value="INSTALL">Install</SelectItem>
                    <SelectItem value="MAINTENANCE">Maintenance</SelectItem>
                    <SelectItem value="INSPECTION">Inspection</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Priority</Label>
                <Select 
                  value={formData.priority} 
                  onValueChange={(v) => setFormData({...formData, priority: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NORMAL">Normal</SelectItem>
                    <SelectItem value="HIGH">High</SelectItem>
                    <SelectItem value="EMERGENCY">Emergency</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Start Time *</Label>
                <Input
                  type="datetime-local"
                  value={formData.service_window_start}
                  onChange={(e) => setFormData({...formData, service_window_start: e.target.value})}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>End Time *</Label>
                <Input
                  type="datetime-local"
                  value={formData.service_window_end}
                  onChange={(e) => setFormData({...formData, service_window_end: e.target.value})}
                  required
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={loading || (!formData.property_id && properties.length > 0)}
            >
              {loading ? "Creating..." : "Create Job"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditLeadDialog({ lead, open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    issue_type: lead?.issue_type || "",
    urgency: lead?.urgency || "ROUTINE",
    description: lead?.description || "",
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (lead) {
      setFormData({
        issue_type: lead.issue_type || "",
        urgency: lead.urgency || "ROUTINE",
        description: lead.description || "",
      });
    }
  }, [lead]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!lead) return;
    
    setLoading(true);
    try {
      await leadAPI.update(lead.id, { ...lead, ...formData });
      toast.success("Lead updated!");
      onSuccess();
    } catch (error) {
      toast.error("Failed to update lead");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Lead</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Issue Type</Label>
              <Input
                value={formData.issue_type}
                onChange={(e) => setFormData({...formData, issue_type: e.target.value})}
                placeholder="e.g., AC Not Cooling"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Urgency</Label>
              <Select 
                value={formData.urgency} 
                onValueChange={(v) => setFormData({...formData, urgency: v})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ROUTINE">Routine</SelectItem>
                  <SelectItem value="URGENT">Urgent</SelectItem>
                  <SelectItem value="EMERGENCY">Emergency</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function CreateLeadDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    source: "MANUAL",
    channel: "FORM",
    issue_type: "",
    urgency: "ROUTINE",
    description: "",
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await leadAPI.create(formData);
      toast.success("Lead created successfully");
      onOpenChange(false);
      setFormData({
        source: "MANUAL",
        channel: "FORM",
        issue_type: "",
        urgency: "ROUTINE",
        description: "",
      });
      onSuccess();
    } catch (error) {
      toast.error("Failed to create lead");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="btn-industrial" data-testid="create-lead-button">
          <Plus className="h-4 w-4 mr-2" />
          NEW LEAD
        </Button>
      </DialogTrigger>
      <DialogContent data-testid="create-lead-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Create New Lead</DialogTitle>
          <DialogDescription>
            Add a new lead to track and follow up
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Source</Label>
                <Select 
                  value={formData.source} 
                  onValueChange={(v) => setFormData({...formData, source: v})}
                >
                  <SelectTrigger data-testid="lead-source-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MANUAL">Manual</SelectItem>
                    <SelectItem value="WEB_FORM">Web Form</SelectItem>
                    <SelectItem value="VAPI_CALL">Vapi Call</SelectItem>
                    <SelectItem value="MISSED_CALL_SMS">Missed Call SMS</SelectItem>
                    <SelectItem value="FB_LEAD">Facebook Lead</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Urgency</Label>
                <Select 
                  value={formData.urgency} 
                  onValueChange={(v) => setFormData({...formData, urgency: v})}
                >
                  <SelectTrigger data-testid="lead-urgency-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ROUTINE">Routine</SelectItem>
                    <SelectItem value="URGENT">Urgent</SelectItem>
                    <SelectItem value="EMERGENCY">Emergency</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="issue_type">Issue Type</Label>
              <Input
                id="issue_type"
                placeholder="e.g., AC Not Cooling, Furnace Issue"
                value={formData.issue_type}
                onChange={(e) => setFormData({...formData, issue_type: e.target.value})}
                data-testid="lead-issue-type"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe the issue..."
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                rows={3}
                data-testid="lead-description"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading} data-testid="submit-lead">
              {loading ? "Creating..." : "Create Lead"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
