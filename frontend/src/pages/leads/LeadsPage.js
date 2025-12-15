import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
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
import { leadAPI } from "../../lib/api";
import { toast } from "sonner";
import { Plus, Search, Filter, Phone, Mail, Clock, AlertTriangle } from "lucide-react";
import { useNavigate } from "react-router-dom";

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
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchLeads();
  }, [statusFilter, sourceFilter]);

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

  const filteredLeads = leads.filter((lead) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      lead.issue_type?.toLowerCase().includes(searchLower) ||
      lead.description?.toLowerCase().includes(searchLower) ||
      lead.source?.toLowerCase().includes(searchLower)
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
            placeholder="Search leads..."
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
              onClick={() => navigate(`/leads/${lead.id}`)}
            />
          ))}
        </div>
      )}
    </Layout>
  );
}

function LeadCard({ lead, formatDate, onClick }) {
  return (
    <Card 
      className="card-industrial cursor-pointer hover:shadow-md transition-shadow relative overflow-hidden"
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
      </CardContent>
    </Card>
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
