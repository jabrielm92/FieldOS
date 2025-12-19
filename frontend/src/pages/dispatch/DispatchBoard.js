import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
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
} from "../../components/ui/dialog";
import { dispatchAPI, technicianAPI, jobAPI } from "../../lib/api";
import { toast } from "sonner";
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar,
  User,
  Clock,
  MapPin,
  AlertTriangle,
  Truck,
  CheckCircle,
  Users
} from "lucide-react";

const priorityColors = {
  EMERGENCY: "border-l-red-500 bg-red-50",
  HIGH: "border-l-orange-500 bg-orange-50",
  NORMAL: "border-l-blue-500 bg-blue-50",
};

const statusColors = {
  BOOKED: "bg-yellow-100 text-yellow-800",
  EN_ROUTE: "bg-purple-100 text-purple-800",
  ON_SITE: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
};

export default function DispatchBoard() {
  // Use local date, not UTC
  const getLocalDateString = () => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  };
  
  const [selectedDate, setSelectedDate] = useState(getLocalDateString());
  const [boardData, setBoardData] = useState({ technicians: [], unassigned_jobs: [] });
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    fetchDispatchBoard();
    fetchTechnicians();
    // Polling for real-time updates
    const interval = setInterval(fetchDispatchBoard, 30000);
    return () => clearInterval(interval);
  }, [selectedDate]);

  const fetchDispatchBoard = async () => {
    try {
      const response = await dispatchAPI.getBoard(selectedDate);
      setBoardData(response.data);
    } catch (error) {
      toast.error("Failed to load dispatch board");
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

  const handleAssignJob = async (technicianId) => {
    if (!selectedJob) return;
    
    setAssigning(true);
    try {
      await dispatchAPI.assignJob(selectedJob.id, technicianId);
      toast.success("Job assigned successfully!");
      setShowAssignDialog(false);
      setSelectedJob(null);
      fetchDispatchBoard();
    } catch (error) {
      toast.error("Failed to assign job");
    } finally {
      setAssigning(false);
    }
  };

  const handleUnassignJob = async (jobId) => {
    try {
      await dispatchAPI.assignJob(jobId, null);
      toast.success("Job unassigned");
      fetchDispatchBoard();
    } catch (error) {
      toast.error("Failed to unassign job");
    }
  };

  const navigateDate = (direction) => {
    const date = new Date(selectedDate + 'T12:00:00'); // Use noon to avoid timezone issues
    date.setDate(date.getDate() + direction);
    const newDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    setSelectedDate(newDate);
  };

  const formatDate = (dateStr) => {
    // Parse as local date
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString(undefined, {
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

  // Calculate stats
  const totalJobs = boardData.unassigned_jobs.length + 
    boardData.technicians.reduce((acc, tech) => acc + (tech.jobs?.length || 0), 0);
  const assignedJobs = boardData.technicians.reduce((acc, tech) => acc + (tech.jobs?.length || 0), 0);
  const unassignedJobs = boardData.unassigned_jobs.length;

  return (
    <Layout title="Dispatch Board" subtitle="Assign and manage technician schedules">
      {/* Date Navigation & Stats */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => navigateDate(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 border border-primary/20 rounded-md">
            <Calendar className="h-4 w-4 text-primary" />
            <span className="font-semibold text-primary">{formatDate(selectedDate)}</span>
          </div>
          <Button variant="outline" size="icon" onClick={() => navigateDate(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setSelectedDate(getLocalDateString())}
          >
            Today
          </Button>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm text-foreground bg-background"
          />
        </div>

        {/* Stats Summary */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-muted rounded-md">
            <Truck className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">{totalJobs} Total Jobs</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 rounded-md">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium text-green-700">{assignedJobs} Assigned</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-100 rounded-md">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span className="text-sm font-medium text-amber-700">{unassignedJobs} Unassigned</span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Unassigned Jobs Column */}
          <Card className="lg:col-span-1 border-amber-200 bg-amber-50/30">
            <CardHeader className="pb-3 bg-amber-100/50 rounded-t-lg">
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                Unassigned Jobs
              </CardTitle>
              <p className="text-sm text-amber-700 font-medium">
                {unassignedJobs} job{unassignedJobs !== 1 ? 's' : ''} need assignment
              </p>
            </CardHeader>
            <CardContent className="pt-4">
              {boardData.unassigned_jobs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                  <p className="text-sm">All jobs assigned!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {boardData.unassigned_jobs.map((job) => (
                    <JobCard 
                      key={job.id} 
                      job={job} 
                      formatTime={formatTime}
                      onAssign={() => {
                        setSelectedJob(job);
                        setShowAssignDialog(true);
                      }}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Technician Columns */}
          <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {boardData.technicians.map((tech) => (
              <Card key={tech.id} className="border-primary/20">
                <CardHeader className="pb-3 bg-primary/5 rounded-t-lg">
                  <CardTitle className="font-heading text-base flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                    {tech.name}
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {tech.jobs?.length || 0} job{(tech.jobs?.length || 0) !== 1 ? 's' : ''} scheduled
                  </p>
                </CardHeader>
                <CardContent className="pt-4 min-h-[200px]">
                  {(tech.jobs?.length || 0) === 0 ? (
                    <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                      <Users className="h-6 w-6 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No jobs assigned</p>
                      <p className="text-xs">Drag a job here or click assign</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {tech.jobs.map((job) => (
                        <JobCard 
                          key={job.id} 
                          job={job} 
                          formatTime={formatTime}
                          assigned
                          onUnassign={() => handleUnassignJob(job.id)}
                          onReassign={() => {
                            setSelectedJob(job);
                            setShowAssignDialog(true);
                          }}
                        />
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}

            {boardData.technicians.length === 0 && (
              <Card className="col-span-full">
                <CardContent className="py-12 text-center">
                  <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-muted-foreground">No technicians found</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Add technicians in the Technicians page
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Assign Job Dialog */}
      <Dialog open={showAssignDialog} onOpenChange={setShowAssignDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Job to Technician</DialogTitle>
            <DialogDescription>
              {selectedJob && (
                <span>
                  {selectedJob.job_type} - {selectedJob.customer?.first_name} {selectedJob.customer?.last_name}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm font-medium mb-3">Select Technician:</p>
            <div className="space-y-2">
              {technicians.filter(t => t.active !== false).map((tech) => (
                <Button
                  key={tech.id}
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => handleAssignJob(tech.id)}
                  disabled={assigning}
                >
                  <User className="h-4 w-4 mr-2" />
                  {tech.name}
                  {tech.skills && (
                    <span className="ml-auto text-xs text-muted-foreground">
                      {Array.isArray(tech.skills) ? tech.skills.join(', ') : tech.skills}
                    </span>
                  )}
                </Button>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAssignDialog(false)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}

function JobCard({ job, formatTime, assigned, onAssign, onUnassign, onReassign }) {
  return (
    <div 
      className={`p-3 rounded-lg border-l-4 ${priorityColors[job.priority] || priorityColors.NORMAL} 
        shadow-sm hover:shadow-md transition-shadow cursor-pointer`}
      data-testid={`dispatch-job-${job.id}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="font-medium text-sm">
            {job.customer?.first_name} {job.customer?.last_name}
          </p>
          <p className="text-xs text-muted-foreground">{job.job_type}</p>
        </div>
        <Badge className={statusColors[job.status] || "bg-gray-100"} variant="outline">
          {job.status}
        </Badge>
      </div>

      <div className="space-y-1 text-xs text-muted-foreground mb-3">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>{formatTime(job.service_window_start)} - {formatTime(job.service_window_end)}</span>
        </div>
        {job.property && (
          <div className="flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            <span className="truncate">{job.property.address_line1}, {job.property.city}</span>
          </div>
        )}
      </div>

      {job.priority === "EMERGENCY" && (
        <div className="flex items-center gap-1 text-xs text-red-600 mb-2">
          <AlertTriangle className="h-3 w-3" />
          <span className="font-medium">EMERGENCY</span>
        </div>
      )}

      <div className="flex gap-2">
        {!assigned && onAssign && (
          <Button size="sm" className="w-full text-xs" onClick={onAssign}>
            Assign Tech
          </Button>
        )}
        {assigned && (
          <>
            <Button size="sm" variant="outline" className="flex-1 text-xs" onClick={onReassign}>
              Reassign
            </Button>
            <Button size="sm" variant="ghost" className="text-xs text-red-600 hover:text-red-700" onClick={onUnassign}>
              Remove
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
