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
  BOOKED: "bg-yellow-500",
  EN_ROUTE: "bg-purple-500",
  ON_SITE: "bg-orange-500",
  COMPLETED: "bg-green-500",
  NO_SHOW: "bg-gray-500",
  CANCELLED: "bg-red-500",
};

const statusBadgeColors = {
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
  const [selectedDate, setSelectedDate] = useState(null);
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
    setSelectedDate(new Date(year, month, day));
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
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => navigateMonth(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <h2 className="text-xl font-heading font-bold min-w-[200px] text-center">
            {formatMonthYear(currentDate)}
          </h2>
          <Button variant="outline" size="icon" onClick={() => navigateMonth(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={goToToday} className="ml-2">
            Today
          </Button>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div> Booked
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-purple-500"></div> En Route
            </span>
            <span className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-green-500"></div> Completed
            </span>
          </div>
          <Button onClick={() => navigate('/dispatch')}>
            <Briefcase className="h-4 w-4 mr-2" />
            Dispatch Board
          </Button>
        </div>
      </div>

      {/* Calendar Grid */}
      <Card>
        <CardContent className="p-0">
          {/* Week day headers */}
          <div className="grid grid-cols-7 border-b">
            {weekDays.map(day => (
              <div key={day} className="p-3 text-center text-sm font-medium text-muted-foreground bg-muted/50">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar days */}
          <div className="grid grid-cols-7">
            {/* Empty cells for days before month starts */}
            {Array.from({ length: startingDay }, (_, i) => (
              <div key={`empty-${i}`} className="min-h-[120px] p-2 border-b border-r bg-muted/20" />
            ))}

            {/* Days of the month */}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const dayJobs = getJobsForDay(day);
              const isToday = isCurrentMonth && today.getDate() === day;

              return (
                <div
                  key={day}
                  className={`min-h-[120px] p-2 border-b border-r transition-colors hover:bg-muted/30
                    ${isToday ? 'bg-primary/5 ring-2 ring-primary ring-inset' : ''}`}
                >
                  <div className={`text-sm font-medium mb-1 ${isToday ? 'text-primary' : ''}`}>
                    {day}
                  </div>
                  <div className="space-y-1">
                    {dayJobs.slice(0, 3).map(job => (
                      <div
                        key={job.id}
                        className={`text-xs p-1.5 rounded cursor-pointer hover:opacity-80 transition-opacity
                          ${statusColors[job.status]} text-white`}
                        onClick={() => {
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
                        onClick={() => {
                          // Could open a modal showing all jobs for this day
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
            <Button onClick={() => navigate('/jobs')}>
              View in Jobs
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
