import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { jobAPI, customerAPI, propertyAPI, technicianAPI, dispatchAPI } from "../../lib/api";
import { toast } from "sonner";
import { 
  ChevronLeft, 
  ChevronRight, 
  Clock,
  MapPin,
  User,
  Briefcase,
  Calendar as CalendarIcon,
  Plus,
  Edit,
  Truck
} from "lucide-react";

const statusColors = {
  SCHEDULED: "bg-indigo-500",
  BOOKED: "bg-yellow-500",
  EN_ROUTE: "bg-purple-500",
  ON_SITE: "bg-orange-500",
  COMPLETED: "bg-green-500",
  NO_SHOW: "bg-gray-500",
  CANCELLED: "bg-red-500",
};

const statusBadgeColors = {
  SCHEDULED: "bg-indigo-100 text-indigo-800",
  BOOKED: "bg-yellow-100 text-yellow-800",
  EN_ROUTE: "bg-purple-100 text-purple-800",
  ON_SITE: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
  NO_SHOW: "bg-gray-100 text-gray-800",
  CANCELLED: "bg-red-100 text-red-800",
};

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showJobModal, setShowJobModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showJobListModal, setShowJobListModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedDayJobs, setSelectedDayJobs] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCustomers();
    fetchTechnicians();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await customerAPI.list();
      setCustomers(response.data);
    } catch (error) {
      console.error("Failed to load customers");
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

  const handleDayClick = (day) => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const clickedDate = new Date(year, month, day);
    setSelectedDate(clickedDate);
    
    // Get jobs for this day
    const dayJobs = getJobsForDay(day);
    
    if (dayJobs.length > 0) {
      // Show job list modal if there are jobs
      setSelectedDayJobs(dayJobs);
      setShowJobListModal(true);
    } else {
      // Show create modal if no jobs
      setShowCreateModal(true);
    }
  };
  
  const handleCreateFromJobList = () => {
    setShowJobListModal(false);
    setShowCreateModal(true);
  };

  const handleEditJob = (job) => {
    setSelectedJob(job);
    setShowJobModal(false);
    setShowEditModal(true);
  };

  useEffect(() => {
    fetchJobs();
    // Polling for real-time updates
    const interval = setInterval(fetchJobs, 30000);
    return () => clearInterval(interval);
  }, [currentDate]);

  const fetchJobs = async () => {
    try {
      const response = await jobAPI.list();
      setJobs(response.data);
    } catch (error) {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  // Calendar helpers
  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDay = firstDay.getDay();
    return { daysInMonth, startingDay };
  };

  const getJobsForDay = (day) => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const dayDate = new Date(year, month, day);
    
    return jobs.filter(job => {
      if (!job.service_window_start) return false;
      const jobDate = new Date(job.service_window_start);
      return jobDate.getFullYear() === year && 
             jobDate.getMonth() === month && 
             jobDate.getDate() === day;
    });
  };

  const navigateMonth = (direction) => {
    const newDate = new Date(currentDate);
    newDate.setMonth(newDate.getMonth() + direction);
    setCurrentDate(newDate);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const formatMonthYear = (date) => {
    return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const { daysInMonth, startingDay } = getDaysInMonth(currentDate);
  const today = new Date();
  const isCurrentMonth = today.getMonth() === currentDate.getMonth() && 
                         today.getFullYear() === currentDate.getFullYear();

  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <Layout title="Calendar" subtitle="View and manage your job schedule">
      {/* Navigation */}
      {/* Header with navigation */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => navigateMonth(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <h2 className="text-lg sm:text-xl font-heading font-bold min-w-[150px] sm:min-w-[200px] text-center">
            {formatMonthYear(currentDate)}
          </h2>
          <Button variant="outline" size="icon" onClick={() => navigateMonth(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={goToToday} className="ml-2">
            Today
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Legend - hidden on mobile */}
          <div className="hidden md:flex items-center gap-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div> Booked
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-purple-500"></div> En Route
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-green-500"></div> Done
            </span>
          </div>
          <Button variant="outline" size="sm" className="hidden sm:flex" onClick={() => navigate('/dispatch')}>
            <Briefcase className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">Dispatch</span>
          </Button>
          <Button size="sm" onClick={() => { setSelectedDate(new Date()); setShowCreateModal(true); }}>
            <Plus className="h-4 w-4 sm:mr-2" />
            <span className="hidden sm:inline">New Job</span>
          </Button>
        </div>
      </div>

      {/* Calendar Grid */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {/* Week day headers */}
          <div className="grid grid-cols-7 border-b">
            {weekDays.map((day, i) => (
              <div key={day} className="p-1 sm:p-3 text-center text-xs sm:text-sm font-medium text-muted-foreground bg-muted/50">
                <span className="sm:hidden">{day.charAt(0)}</span>
                <span className="hidden sm:inline">{day}</span>
              </div>
            ))}
          </div>

          {/* Calendar days */}
          <div className="grid grid-cols-7">
            {/* Empty cells for days before month starts */}
            {Array.from({ length: startingDay }, (_, i) => (
              <div key={`empty-${i}`} className="min-h-[60px] sm:min-h-[120px] p-1 sm:p-2 border-b border-r bg-muted/20" />
            ))}

            {/* Days of the month */}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const dayJobs = getJobsForDay(day);
              const isToday = isCurrentMonth && today.getDate() === day;

              return (
                <div
                  key={day}
                  className={`min-h-[60px] sm:min-h-[120px] p-1 sm:p-2 border-b border-r transition-colors hover:bg-muted/30 cursor-pointer group
                    ${isToday ? 'bg-primary/5 ring-2 ring-primary ring-inset' : ''}`}
                  onClick={() => handleDayClick(day)}
                >
                  <div className={`text-xs sm:text-sm font-medium mb-1 flex items-center justify-between ${isToday ? 'text-primary' : ''}`}>
                    <span>{day}</span>
                    {dayJobs.length > 0 && (
                      <span className="sm:hidden w-2 h-2 rounded-full bg-primary"></span>
                    )}
                    <Plus className="h-3 w-3 opacity-0 group-hover:opacity-50 transition-opacity hidden sm:block" />
                  </div>
                  {/* Jobs - hidden on mobile, show dot indicator instead */}
                  <div className="hidden sm:block space-y-1">
                    {dayJobs.slice(0, 3).map(job => (
                      <div
                        key={job.id}
                        className={`text-xs p-1.5 rounded cursor-pointer hover:opacity-80 transition-opacity
                          ${statusColors[job.status] || 'bg-gray-500'} text-white`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedJob(job);
                          setShowJobModal(true);
                        }}
                      >
                        <div className="font-medium truncate">
                          {formatTime(job.service_window_start)}
                        </div>
                        <div className="truncate opacity-90">
                          {job.customer?.first_name} {job.customer?.last_name?.charAt(0)}.
                        </div>
                      </div>
                    ))}
                    {dayJobs.length > 3 && (
                      <div 
                        className="text-xs text-muted-foreground text-center cursor-pointer hover:text-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedDayJobs(dayJobs);
                          setSelectedDate(new Date(currentDate.getFullYear(), currentDate.getMonth(), day));
                          setShowJobListModal(true);
                        }}
                      >
                        +{dayJobs.length - 3} more
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Empty cells to complete the grid */}
            {Array.from({ length: (7 - ((startingDay + daysInMonth) % 7)) % 7 }, (_, i) => (
              <div key={`empty-end-${i}`} className="min-h-[120px] p-2 border-b border-r bg-muted/20" />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Job Detail Modal */}
      <Dialog open={showJobModal} onOpenChange={setShowJobModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              Job Details
            </DialogTitle>
          </DialogHeader>
          {selectedJob && (
            <div className="space-y-4 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-lg">
                    {selectedJob.customer?.first_name} {selectedJob.customer?.last_name}
                  </h3>
                  <p className="text-muted-foreground">{selectedJob.job_type}</p>
                </div>
                <Badge className={statusBadgeColors[selectedJob.status]}>
                  {selectedJob.status}
                </Badge>
              </div>

              <div className="bg-muted/50 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span>
                    {formatTime(selectedJob.service_window_start)} - {formatTime(selectedJob.service_window_end)}
                  </span>
                </div>
                {selectedJob.property && (
                  <div className="flex items-start gap-2 text-sm">
                    <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                    <div>
                      <p>{selectedJob.property.address_line1}</p>
                      <p className="text-muted-foreground">
                        {selectedJob.property.city}, {selectedJob.property.state}
                      </p>
                    </div>
                  </div>
                )}
                {selectedJob.technician && (
                  <div className="flex items-center gap-2 text-sm">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span>Tech: {selectedJob.technician.name}</span>
                  </div>
                )}
              </div>

              {selectedJob.notes && (
                <div>
                  <p className="text-sm font-medium mb-1">Notes:</p>
                  <p className="text-sm text-muted-foreground">{selectedJob.notes}</p>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowJobModal(false)}>
              Close
            </Button>
            <Button variant="outline" onClick={() => handleEditJob(selectedJob)}>
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button onClick={() => navigate('/jobs')}>
              View in Jobs
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Job List Modal - shows jobs for a specific day */}
      <Dialog open={showJobListModal} onOpenChange={setShowJobListModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              {selectedDate?.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
            </DialogTitle>
            <DialogDescription>
              {selectedDayJobs.length} job{selectedDayJobs.length !== 1 ? 's' : ''} scheduled
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 max-h-96 overflow-y-auto py-4">
            {selectedDayJobs.map((job) => (
              <Card 
                key={job.id} 
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => {
                  setSelectedJob(job);
                  setShowJobListModal(false);
                  setShowJobModal(true);
                }}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge className={statusBadgeColors[job.status] || "bg-gray-100"}>
                          {job.status}
                        </Badge>
                        <Badge variant="outline">{job.job_type}</Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground mt-2">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatTime(job.service_window_start)} - {formatTime(job.service_window_end)}
                        </span>
                        {job.customer_name && (
                          <span className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {job.customer_name}
                          </span>
                        )}
                      </div>
                      {job.property_address && (
                        <p className="text-sm text-muted-foreground mt-1 flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {job.property_address}
                        </p>
                      )}
                    </div>
                    <ChevronRight className="h-5 w-5 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={() => setShowJobListModal(false)}>
              Close
            </Button>
            <Button onClick={handleCreateFromJobList}>
              <Plus className="h-4 w-4 mr-1" />
              Add New Job
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Job Modal */}
      <CreateJobModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        selectedDate={selectedDate}
        customers={customers}
        technicians={technicians}
        onSuccess={fetchJobs}
      />

      {/* Edit Job Modal */}
      <EditJobModal
        open={showEditModal}
        onOpenChange={setShowEditModal}
        job={selectedJob}
        technicians={technicians}
        onSuccess={fetchJobs}
      />
    </Layout>
  );
}

function CreateJobModal({ open, onOpenChange, selectedDate, customers, technicians, onSuccess }) {
  const [formData, setFormData] = useState({
    customer_id: "",
    property_id: "",
    job_type: "DIAGNOSTIC",
    priority: "NORMAL",
    notes: "",
    service_window_start: "",
    service_window_end: "",
    assigned_technician_id: "",
  });
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedDate && open) {
      const dateStr = selectedDate.toISOString().split('T')[0];
      setFormData(prev => ({
        ...prev,
        service_window_start: `${dateStr}T09:00`,
        service_window_end: `${dateStr}T11:00`,
      }));
    }
  }, [selectedDate, open]);

  useEffect(() => {
    if (formData.customer_id) {
      fetchProperties(formData.customer_id);
    }
  }, [formData.customer_id]);

  const fetchProperties = async (customerId) => {
    try {
      const response = await propertyAPI.list(customerId);
      setProperties(response.data);
      if (response.data.length > 0) {
        setFormData(prev => ({ ...prev, property_id: response.data[0].id }));
      }
    } catch (error) {
      console.error("Failed to load properties");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.customer_id || !formData.property_id) {
      toast.error("Please select a customer and property");
      return;
    }
    
    setLoading(true);
    try {
      await jobAPI.create({
        ...formData,
        service_window_start: new Date(formData.service_window_start).toISOString(),
        service_window_end: new Date(formData.service_window_end).toISOString(),
        assigned_technician_id: formData.assigned_technician_id || null,
      });
      toast.success("Job scheduled successfully!");
      onOpenChange(false);
      onSuccess();
      setFormData({
        customer_id: "",
        property_id: "",
        job_type: "DIAGNOSTIC",
        priority: "NORMAL",
        notes: "",
        service_window_start: "",
        service_window_end: "",
        assigned_technician_id: "",
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Schedule New Job
          </DialogTitle>
          <DialogDescription>
            {selectedDate && `Scheduling for ${selectedDate.toLocaleDateString()}`}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Customer *</Label>
            <Select value={formData.customer_id} onValueChange={(v) => setFormData({...formData, customer_id: v, property_id: ""})}>
              <SelectTrigger>
                <SelectValue placeholder="Select customer" />
              </SelectTrigger>
              <SelectContent>
                {customers.map(c => (
                  <SelectItem key={c.id} value={c.id}>{c.first_name} {c.last_name} - {c.phone}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {properties.length > 0 && (
            <div className="space-y-2">
              <Label>Property *</Label>
              <Select value={formData.property_id} onValueChange={(v) => setFormData({...formData, property_id: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Select property" />
                </SelectTrigger>
                <SelectContent>
                  {properties.map(p => (
                    <SelectItem key={p.id} value={p.id}>{p.address_line1}, {p.city}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Job Type</Label>
              <Select value={formData.job_type} onValueChange={(v) => setFormData({...formData, job_type: v})}>
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
              <Select value={formData.priority} onValueChange={(v) => setFormData({...formData, priority: v})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="EMERGENCY">Emergency</SelectItem>
                  <SelectItem value="HIGH">High</SelectItem>
                  <SelectItem value="NORMAL">Normal</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Start Time</Label>
              <Input
                type="datetime-local"
                value={formData.service_window_start}
                onChange={(e) => setFormData({...formData, service_window_start: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label>End Time</Label>
              <Input
                type="datetime-local"
                value={formData.service_window_end}
                onChange={(e) => setFormData({...formData, service_window_end: e.target.value})}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Assign Technician</Label>
            <Select value={formData.assigned_technician_id || "unassigned"} onValueChange={(v) => setFormData({...formData, assigned_technician_id: v === "unassigned" ? "" : v})}>
              <SelectTrigger>
                <SelectValue placeholder="Unassigned" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unassigned">Unassigned</SelectItem>
                {technicians.filter(t => t.active !== false).map(t => (
                  <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              placeholder="Job notes..."
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              rows={2}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Scheduling..." : "Schedule Job"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditJobModal({ open, onOpenChange, job, technicians, onSuccess }) {
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (job) {
      setFormData({
        job_type: job.job_type || "DIAGNOSTIC",
        priority: job.priority || "NORMAL",
        status: job.status || "BOOKED",
        notes: job.notes || "",
        service_window_start: job.service_window_start ? job.service_window_start.slice(0, 16) : "",
        service_window_end: job.service_window_end ? job.service_window_end.slice(0, 16) : "",
        assigned_technician_id: job.assigned_technician_id || "",
      });
    }
  }, [job]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!job) return;
    
    setLoading(true);
    try {
      await jobAPI.update(job.id, {
        customer_id: job.customer_id,
        property_id: job.property_id,
        ...formData,
        service_window_start: new Date(formData.service_window_start).toISOString(),
        service_window_end: new Date(formData.service_window_end).toISOString(),
        assigned_technician_id: formData.assigned_technician_id || null,
      });
      toast.success("Job updated successfully!");
      onOpenChange(false);
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update job");
    } finally {
      setLoading(false);
    }
  };

  const handleMarkEnRoute = async () => {
    if (!job) return;
    try {
      await jobAPI.markEnRoute(job.id);
      toast.success("Job marked as en-route, SMS sent!");
      onOpenChange(false);
      onSuccess();
    } catch (error) {
      toast.error("Failed to update status");
    }
  };

  if (!job) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Edit className="h-5 w-5" />
            Edit Job
          </DialogTitle>
          <DialogDescription>
            {job.customer?.first_name} {job.customer?.last_name} - {job.property?.address_line1}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Job Type</Label>
              <Select value={formData.job_type} onValueChange={(v) => setFormData({...formData, job_type: v})}>
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
              <Select value={formData.priority} onValueChange={(v) => setFormData({...formData, priority: v})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="EMERGENCY">Emergency</SelectItem>
                  <SelectItem value="HIGH">High</SelectItem>
                  <SelectItem value="NORMAL">Normal</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Status</Label>
            <Select value={formData.status} onValueChange={(v) => setFormData({...formData, status: v})}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BOOKED">Booked</SelectItem>
                <SelectItem value="EN_ROUTE">En Route</SelectItem>
                <SelectItem value="ON_SITE">On Site</SelectItem>
                <SelectItem value="COMPLETED">Completed</SelectItem>
                <SelectItem value="NO_SHOW">No Show</SelectItem>
                <SelectItem value="CANCELLED">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Start Time</Label>
              <Input
                type="datetime-local"
                value={formData.service_window_start}
                onChange={(e) => setFormData({...formData, service_window_start: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label>End Time</Label>
              <Input
                type="datetime-local"
                value={formData.service_window_end}
                onChange={(e) => setFormData({...formData, service_window_end: e.target.value})}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Assign Technician</Label>
            <Select value={formData.assigned_technician_id || "unassigned"} onValueChange={(v) => setFormData({...formData, assigned_technician_id: v === "unassigned" ? "" : v})}>
              <SelectTrigger>
                <SelectValue placeholder="Unassigned" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unassigned">Unassigned</SelectItem>
                {technicians.filter(t => t.active !== false).map(t => (
                  <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              placeholder="Job notes..."
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              rows={2}
            />
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2">
            {formData.status === "BOOKED" && (
              <Button type="button" variant="outline" onClick={handleMarkEnRoute} className="w-full sm:w-auto">
                <Truck className="h-4 w-4 mr-2" />
                Mark En Route & Send SMS
              </Button>
            )}
            <div className="flex gap-2 w-full sm:w-auto">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button type="submit" disabled={loading}>
                {loading ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
