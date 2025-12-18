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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { jobAPI, customerAPI, propertyAPI, technicianAPI, dispatchAPI } from "../../lib/api";
import { toast } from "sonner";
import { Plus, Search, Clock, MapPin, User, Truck, Calendar, UserPlus, Edit, Trash2 } from "lucide-react";

const statusColors = {
  BOOKED: "bg-yellow-100 text-yellow-800",
  EN_ROUTE: "bg-purple-100 text-purple-800",
  ON_SITE: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
  NO_SHOW: "bg-gray-100 text-gray-800",
  CANCELLED: "bg-red-100 text-red-800",
};

const priorityColors = {
  EMERGENCY: "bg-red-500 text-white",
  HIGH: "bg-orange-500 text-white",
  NORMAL: "bg-blue-500 text-white",
};

export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [showJobDetailDialog, setShowJobDetailDialog] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);

  useEffect(() => {
    fetchJobs();
    fetchTechnicians();
    // Polling for real-time updates
    const interval = setInterval(fetchJobs, 30000);
    return () => clearInterval(interval);
  }, [statusFilter]);

  const fetchJobs = async () => {
    try {
      const filters = {};
      if (statusFilter !== "all") filters.status = statusFilter;
      
      const response = await jobAPI.list(filters);
      setJobs(response.data);
    } catch (error) {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  const fetchTechnicians = async () => {
    try {
      const response = await technicianAPI.list();
      setTechnicians(response.data);
    } catch (error) {
      console.error("Failed to load technicians");
    }
  };

  const handleMarkEnRoute = async (jobId) => {
    try {
      await jobAPI.markEnRoute(jobId);
      toast.success("Job marked as en-route, SMS sent!");
      fetchJobs();
    } catch (error) {
      toast.error("Failed to update job status");
    }
  };

  const handleUpdateStatus = async (jobId, newStatus) => {
    try {
      const job = jobs.find(j => j.id === jobId);
      await jobAPI.update(jobId, {
        ...job,
        status: newStatus,
        service_window_start: job.service_window_start,
        service_window_end: job.service_window_end,
      });
      toast.success("Job status updated");
      fetchJobs();
    } catch (error) {
      toast.error("Failed to update job");
    }
  };

  const handleAssignTech = async (techId) => {
    if (!selectedJob) return;
    try {
      await dispatchAPI.assignJob(selectedJob.id, techId);
      toast.success("Technician assigned!");
      setShowAssignDialog(false);
      setSelectedJob(null);
      fetchJobs();
    } catch (error) {
      toast.error("Failed to assign technician");
    }
  };

  const handleJobClick = (job) => {
    setSelectedJob(job);
    setShowJobDetailDialog(true);
  };

  const filteredJobs = jobs.filter((job) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      job.customer?.first_name?.toLowerCase().includes(searchLower) ||
      job.customer?.last_name?.toLowerCase().includes(searchLower) ||
      job.property?.city?.toLowerCase().includes(searchLower) ||
      job.job_type?.toLowerCase().includes(searchLower) ||
      job.technician?.name?.toLowerCase().includes(searchLower)
    );
  });

  const formatDateTime = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <Layout title="Jobs" subtitle="Manage service appointments">
      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search jobs by customer, location, tech..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="jobs-search"
          />
        </div>
        
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]" data-testid="jobs-status-filter">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="BOOKED">Booked</SelectItem>
            <SelectItem value="EN_ROUTE">En Route</SelectItem>
            <SelectItem value="ON_SITE">On Site</SelectItem>
            <SelectItem value="COMPLETED">Completed</SelectItem>
            <SelectItem value="NO_SHOW">No Show</SelectItem>
            <SelectItem value="CANCELLED">Cancelled</SelectItem>
          </SelectContent>
        </Select>

        <CreateJobDialog 
          open={showCreateDialog} 
          onOpenChange={setShowCreateDialog}
          onSuccess={fetchJobs}
        />
      </div>

      {/* Jobs Table */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filteredJobs.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No jobs found</p>
            <Button 
              className="mt-4" 
              onClick={() => setShowCreateDialog(true)}
              data-testid="create-first-job"
            >
              Schedule your first job
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table data-testid="jobs-table">
            <TableHeader>
              <TableRow className="table-industrial">
                <TableHead>Customer</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Schedule</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Tech</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredJobs.map((job) => (
                <TableRow 
                  key={job.id} 
                  className="table-industrial cursor-pointer hover:bg-muted/50" 
                  data-testid={`job-row-${job.id}`}
                  onClick={() => handleJobClick(job)}
                >
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                        <User className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">
                          {job.customer?.first_name} {job.customer?.last_name}
                        </p>
                        <Badge className={priorityColors[job.priority]} variant="outline">
                          {job.priority}
                        </Badge>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <p className="font-medium">{job.job_type}</p>
                    <p className="text-xs text-muted-foreground">
                      {job.created_by === "AI" ? "AI Booked" : "Staff Booked"}
                    </p>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-sm">
                      <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="data-mono">{formatDateTime(job.service_window_start)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      to {formatTime(job.service_window_end)}
                    </p>
                  </TableCell>
                  <TableCell>
                    {job.property ? (
                      <div className="flex items-start gap-1">
                        <MapPin className="h-3.5 w-3.5 text-muted-foreground mt-0.5" />
                        <div className="text-sm">
                          <p>{job.property.address_line1}</p>
                          <p className="text-muted-foreground">{job.property.city}, {job.property.state}</p>
                        </div>
                      </div>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    {job.technician ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="flex items-center gap-2 h-auto py-1"
                        onClick={() => {
                          setSelectedJob(job);
                          setShowAssignDialog(true);
                        }}
                      >
                        <div className="w-6 h-6 bg-accent/10 rounded-full flex items-center justify-center">
                          <User className="h-3 w-3 text-accent" />
                        </div>
                        <span className="text-sm">{job.technician.name}</span>
                        <Edit className="h-3 w-3 text-muted-foreground" />
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-amber-600 border-amber-200 hover:bg-amber-50"
                        onClick={() => {
                          setSelectedJob(job);
                          setShowAssignDialog(true);
                        }}
                      >
                        <UserPlus className="h-3 w-3 mr-1" />
                        Assign
                      </Button>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge className={statusColors[job.status]}>
                      {job.status?.replace('_', ' ')}
                    </Badge>
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center gap-2">
                      {job.status === "BOOKED" && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => handleMarkEnRoute(job.id)}
                          data-testid={`en-route-${job.id}`}
                        >
                          <Truck className="h-3 w-3 mr-1" />
                          En Route
                        </Button>
                      )}
                      {job.status === "EN_ROUTE" && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => handleUpdateStatus(job.id, "ON_SITE")}
                        >
                          On Site
                        </Button>
                      )}
                      {job.status === "ON_SITE" && (
                        <Button 
                          size="sm" 
                          variant="default"
                          onClick={() => handleUpdateStatus(job.id, "COMPLETED")}
                        >
                          Complete
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Assign Technician Dialog */}
      <Dialog open={showAssignDialog} onOpenChange={setShowAssignDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Technician</DialogTitle>
            <DialogDescription>
              {selectedJob && `${selectedJob.job_type} for ${selectedJob.customer?.first_name} ${selectedJob.customer?.last_name}`}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-2">
            {technicians.filter(t => t.active !== false).map((tech) => (
              <Button
                key={tech.id}
                variant={selectedJob?.assigned_technician_id === tech.id ? "default" : "outline"}
                className="w-full justify-start"
                onClick={() => handleAssignTech(tech.id)}
              >
                <User className="h-4 w-4 mr-2" />
                {tech.name}
                {tech.phone && <span className="ml-auto text-xs text-muted-foreground">{tech.phone}</span>}
              </Button>
            ))}
            {selectedJob?.assigned_technician_id && (
              <Button
                variant="ghost"
                className="w-full text-red-600"
                onClick={() => handleAssignTech(null)}
              >
                Remove Assignment
              </Button>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAssignDialog(false)}>Cancel</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Job Detail Dialog */}
      <Dialog open={showJobDetailDialog} onOpenChange={setShowJobDetailDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Job Details</DialogTitle>
          </DialogHeader>
          {selectedJob && (
            <div className="space-y-4 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{selectedJob.customer?.first_name} {selectedJob.customer?.last_name}</h3>
                  <p className="text-sm text-muted-foreground">{selectedJob.job_type}</p>
                </div>
                <div className="flex gap-2">
                  <Badge className={priorityColors[selectedJob.priority]}>{selectedJob.priority}</Badge>
                  <Badge className={statusColors[selectedJob.status]}>{selectedJob.status}</Badge>
                </div>
              </div>
              
              <div className="bg-muted/50 rounded-lg p-4 space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span>{formatDateTime(selectedJob.service_window_start)} - {formatTime(selectedJob.service_window_end)}</span>
                </div>
                {selectedJob.property && (
                  <div className="flex items-start gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                    <div>
                      <p>{selectedJob.property.address_line1}</p>
                      <p className="text-muted-foreground">{selectedJob.property.city}, {selectedJob.property.state} {selectedJob.property.postal_code}</p>
                    </div>
                  </div>
                )}
                {selectedJob.technician && (
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span>Tech: {selectedJob.technician.name}</span>
                  </div>
                )}
              </div>

              {selectedJob.notes && (
                <div>
                  <p className="text-sm font-medium mb-1">Notes:</p>
                  <p className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">{selectedJob.notes}</p>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                {!selectedJob.technician && (
                  <Button 
                    className="flex-1"
                    onClick={() => {
                      setShowJobDetailDialog(false);
                      setShowAssignDialog(true);
                    }}
                  >
                    <UserPlus className="h-4 w-4 mr-2" />
                    Assign Tech
                  </Button>
                )}
                {selectedJob.status === "BOOKED" && (
                  <Button 
                    variant="outline"
                    className="flex-1"
                    onClick={() => {
                      handleMarkEnRoute(selectedJob.id);
                      setShowJobDetailDialog(false);
                    }}
                  >
                    <Truck className="h-4 w-4 mr-2" />
                    Mark En Route
                  </Button>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowJobDetailDialog(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}

function CreateJobDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    customer_id: "",
    property_id: "",
    job_type: "DIAGNOSTIC",
    priority: "NORMAL",
    service_window_start: "",
    service_window_end: "",
    notes: "",
  });
  const [customers, setCustomers] = useState([]);
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      fetchCustomers();
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await jobAPI.create({
        ...formData,
        service_window_start: new Date(formData.service_window_start).toISOString(),
        service_window_end: new Date(formData.service_window_end).toISOString(),
      });
      toast.success("Job created successfully");
      onOpenChange(false);
      setFormData({
        customer_id: "",
        property_id: "",
        job_type: "DIAGNOSTIC",
        priority: "NORMAL",
        service_window_start: "",
        service_window_end: "",
        notes: "",
      });
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="btn-industrial" data-testid="create-job-button">
          <Plus className="h-4 w-4 mr-2" />
          NEW JOB
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg" data-testid="create-job-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Schedule New Job</DialogTitle>
          <DialogDescription>
            Create a new service appointment
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Customer *</Label>
              <Select 
                value={formData.customer_id} 
                onValueChange={(v) => setFormData({...formData, customer_id: v, property_id: ""})}
              >
                <SelectTrigger data-testid="job-customer-select">
                  <SelectValue placeholder="Select customer" />
                </SelectTrigger>
                <SelectContent>
                  {customers.map((c) => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.first_name} {c.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {formData.customer_id && (
              <div className="space-y-2">
                <Label>Property *</Label>
                <Select 
                  value={formData.property_id} 
                  onValueChange={(v) => setFormData({...formData, property_id: v})}
                >
                  <SelectTrigger data-testid="job-property-select">
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
                  data-testid="job-start-time"
                />
              </div>
              <div className="space-y-2">
                <Label>End Time *</Label>
                <Input
                  type="datetime-local"
                  value={formData.service_window_end}
                  onChange={(e) => setFormData({...formData, service_window_end: e.target.value})}
                  required
                  data-testid="job-end-time"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                placeholder="Any additional notes..."
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
              disabled={loading || !formData.customer_id || !formData.property_id}
              data-testid="submit-job"
            >
              {loading ? "Creating..." : "Schedule Job"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
