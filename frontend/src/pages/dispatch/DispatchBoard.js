import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Calendar } from "../../components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../components/ui/popover";
import { ScrollArea } from "../../components/ui/scroll-area";
import { cn } from "../../lib/utils";
import { format } from "date-fns";
import { toast } from "sonner";
import { 
  CalendarIcon, 
  Clock, 
  MapPin, 
  User, 
  Wrench,
  GripVertical,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Phone,
  Truck
} from "lucide-react";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const priorityColors = {
  EMERGENCY: "bg-red-500 text-white border-red-600",
  HIGH: "bg-orange-500 text-white border-orange-600",
  NORMAL: "bg-blue-500 text-white border-blue-600",
};

const statusColors = {
  BOOKED: "bg-yellow-100 text-yellow-800",
  EN_ROUTE: "bg-purple-100 text-purple-800",
  ON_SITE: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
};

export default function DispatchBoard() {
  const [date, setDate] = useState(new Date());
  const [boardData, setBoardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [draggedJob, setDraggedJob] = useState(null);

  useEffect(() => {
    fetchBoardData();
  }, [date]);

  const fetchBoardData = async () => {
    try {
      const token = localStorage.getItem("fieldos_token");
      const dateStr = format(date, "yyyy-MM-dd");
      const response = await axios.get(`${API_URL}/api/v1/dispatch/board?date=${dateStr}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBoardData(response.data);
    } catch (error) {
      toast.error("Failed to load dispatch board");
    } finally {
      setLoading(false);
    }
  };

  const handleAssignJob = async (jobId, technicianId) => {
    try {
      const token = localStorage.getItem("fieldos_token");
      await axios.post(`${API_URL}/api/v1/dispatch/assign?job_id=${jobId}&technician_id=${technicianId || ''}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(technicianId ? "Job assigned" : "Job unassigned");
      fetchBoardData();
    } catch (error) {
      toast.error("Failed to assign job");
    }
  };

  const handleDragStart = (e, job) => {
    setDraggedJob(job);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = (e, technicianId) => {
    e.preventDefault();
    if (draggedJob) {
      handleAssignJob(draggedJob.id, technicianId);
      setDraggedJob(null);
    }
  };

  const navigateDay = (direction) => {
    const newDate = new Date(date);
    newDate.setDate(newDate.getDate() + direction);
    setDate(newDate);
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <Layout title="Dispatch Board">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </Layout>
    );
  }

  const technicians = boardData?.technicians || [];
  const unassignedJobs = boardData?.unassigned_jobs || [];
  const assignedJobs = boardData?.assigned_jobs || {};

  return (
    <Layout title="Dispatch Board" subtitle={`Manage technician assignments for ${format(date, "EEEE, MMMM d, yyyy")}`}>
      {/* Date Navigation */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => navigateDay(-1)} data-testid="prev-day">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className="min-w-[200px]" data-testid="date-picker">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {format(date, "MMM d, yyyy")}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={date}
                onSelect={(d) => d && setDate(d)}
                initialFocus
              />
            </PopoverContent>
          </Popover>
          
          <Button variant="outline" size="icon" onClick={() => navigateDay(1)} data-testid="next-day">
            <ChevronRight className="h-4 w-4" />
          </Button>
          
          <Button variant="ghost" onClick={() => setDate(new Date())}>
            Today
          </Button>
        </div>

        <div className="flex items-center gap-4 text-sm">
          <span className="text-muted-foreground">
            {boardData?.summary?.total_jobs || 0} total jobs
          </span>
          <Badge variant="outline" className="bg-yellow-50">
            {boardData?.summary?.unassigned || 0} unassigned
          </Badge>
          <Badge variant="outline" className="bg-green-50">
            {boardData?.summary?.assigned || 0} assigned
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Unassigned Jobs Column */}
        <Card 
          className="lg:col-span-1"
          onDragOver={handleDragOver}
          onDrop={(e) => handleDrop(e, null)}
        >
          <CardHeader className="pb-3 bg-yellow-50 rounded-t-lg">
            <CardTitle className="text-base font-heading flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              Unassigned ({unassignedJobs.length})
            </CardTitle>
          </CardHeader>
          <ScrollArea className="h-[calc(100vh-320px)]">
            <CardContent className="p-3 space-y-2">
              {unassignedJobs.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  All jobs assigned! 🎉
                </p>
              ) : (
                unassignedJobs.map((job) => (
                  <JobCard 
                    key={job.id} 
                    job={job} 
                    formatTime={formatTime}
                    onDragStart={handleDragStart}
                    draggable
                  />
                ))
              )}
            </CardContent>
          </ScrollArea>
        </Card>

        {/* Technician Columns */}
        <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {technicians.length === 0 ? (
            <Card className="col-span-full">
              <CardContent className="py-12 text-center">
                <Wrench className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                <p className="text-muted-foreground">No technicians available</p>
                <p className="text-sm text-muted-foreground mt-1">Add technicians in the Technicians page</p>
              </CardContent>
            </Card>
          ) : (
            technicians.map((tech) => (
              <TechnicianColumn
                key={tech.id}
                technician={tech}
                jobs={assignedJobs[tech.id] || []}
                formatTime={formatTime}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, tech.id)}
                onDragStart={handleDragStart}
              />
            ))
          )}
        </div>
      </div>
    </Layout>
  );
}

function TechnicianColumn({ technician, jobs, formatTime, onDragOver, onDrop, onDragStart }) {
  return (
    <Card 
      className="flex flex-col"
      onDragOver={onDragOver}
      onDrop={onDrop}
      data-testid={`tech-column-${technician.id}`}
    >
      <CardHeader className="pb-3 bg-primary/5 rounded-t-lg">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-accent/20 rounded-full flex items-center justify-center">
            <Wrench className="h-5 w-5 text-accent" />
          </div>
          <div className="flex-1">
            <CardTitle className="text-base font-heading">{technician.name}</CardTitle>
            <p className="text-xs text-muted-foreground font-mono">{technician.phone}</p>
          </div>
          <Badge variant="outline">{jobs.length} jobs</Badge>
        </div>
      </CardHeader>
      <ScrollArea className="flex-1 h-[calc(100vh-380px)]">
        <CardContent className="p-3 space-y-2">
          {jobs.length === 0 ? (
            <div className="border-2 border-dashed border-muted rounded-lg p-8 text-center">
              <p className="text-sm text-muted-foreground">
                Drag jobs here to assign
              </p>
            </div>
          ) : (
            jobs.map((job) => (
              <JobCard 
                key={job.id} 
                job={job} 
                formatTime={formatTime}
                onDragStart={onDragStart}
                draggable
                showTech={false}
              />
            ))
          )}
        </CardContent>
      </ScrollArea>
    </Card>
  );
}

function JobCard({ job, formatTime, onDragStart, draggable, showTech = true }) {
  return (
    <div
      className={cn(
        "p-3 bg-card border rounded-lg cursor-grab active:cursor-grabbing transition-all hover:shadow-md",
        "relative overflow-hidden"
      )}
      draggable={draggable}
      onDragStart={(e) => onDragStart && onDragStart(e, job)}
      data-testid={`job-card-${job.id}`}
    >
      {/* Priority indicator */}
      <div className={cn(
        "absolute left-0 top-0 bottom-0 w-1",
        job.priority === "EMERGENCY" ? "bg-red-500" : 
        job.priority === "HIGH" ? "bg-orange-500" : "bg-blue-500"
      )} />
      
      <div className="pl-2">
        {/* Header */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <GripVertical className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="font-medium text-sm">
                {job.customer?.first_name} {job.customer?.last_name}
              </p>
              <Badge className={priorityColors[job.priority]} variant="outline">
                {job.priority}
              </Badge>
            </div>
          </div>
          <Badge className={statusColors[job.status]}>
            {job.status}
          </Badge>
        </div>

        {/* Job Type */}
        <p className="text-sm font-medium text-primary mb-2">{job.job_type}</p>

        {/* Details */}
        <div className="space-y-1 text-xs text-muted-foreground">
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
          {job.customer?.phone && (
            <div className="flex items-center gap-1">
              <Phone className="h-3 w-3" />
              <span className="font-mono">{job.customer.phone}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
