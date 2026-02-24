import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { toast } from "sonner";
import axios from "axios";
import {
  MapPin, Clock, CheckCircle2, Truck, Wrench, Phone,
  ChevronRight, Loader2, RefreshCw, LogOut, User,
  Navigation, Camera, AlertCircle, Circle,
} from "lucide-react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

const STATUS_CONFIG = {
  BOOKED: { label: "Booked", color: "bg-blue-500/20 text-blue-300 border-blue-500/30", icon: Clock },
  EN_ROUTE: { label: "En Route", color: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30", icon: Truck },
  ON_SITE: { label: "On Site", color: "bg-purple-500/20 text-purple-300 border-purple-500/30", icon: Wrench },
  COMPLETED: { label: "Completed", color: "bg-green-500/20 text-green-300 border-green-500/30", icon: CheckCircle2 },
  NO_SHOW: { label: "No Show", color: "bg-red-500/20 text-red-300 border-red-500/30", icon: AlertCircle },
  CANCELLED: { label: "Cancelled", color: "bg-gray-500/20 text-gray-400 border-gray-500/30", icon: Circle },
};

const NEXT_STATUS = {
  BOOKED: { status: "EN_ROUTE", label: "Start Driving", icon: Truck, color: "bg-yellow-600 hover:bg-yellow-700" },
  EN_ROUTE: { status: "ON_SITE", label: "Arrived On Site", icon: Wrench, color: "bg-purple-600 hover:bg-purple-700" },
  ON_SITE: { status: "COMPLETED", label: "Mark Complete", icon: CheckCircle2, color: "bg-green-600 hover:bg-green-700" },
};

function formatWindow(start, end) {
  const opts = { hour: "numeric", minute: "2-digit", hour12: true };
  const s = new Date(start).toLocaleTimeString("en-US", opts);
  const e = new Date(end).toLocaleTimeString("en-US", opts);
  const d = new Date(start).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return `${d} · ${s} – ${e}`;
}

function JobCard({ job, onStatusChange, updating }) {
  const statusCfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.BOOKED;
  const StatusIcon = statusCfg.icon;
  const nextStatus = NEXT_STATUS[job.status];
  const customer = job.customer || {};
  const property = job.property || {};

  const address = [
    property.address_line1,
    property.city,
    property.state,
    property.postal_code,
  ].filter(Boolean).join(", ");

  const mapsUrl = address
    ? `https://maps.google.com/?q=${encodeURIComponent(address)}`
    : null;

  return (
    <div className="bg-[#0d1424] border border-white/10 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-center justify-between mb-2">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-medium ${statusCfg.color}`}>
            <StatusIcon className="h-3 w-3" />
            {statusCfg.label}
          </span>
          <span className="text-xs text-gray-500 font-mono">#{job.id?.slice(-6).toUpperCase()}</span>
        </div>
        <p className="text-white font-semibold text-lg leading-tight">
          {job.job_type?.replace(/_/g, " ")}
        </p>
        <p className="text-gray-400 text-sm mt-0.5">{formatWindow(job.service_window_start, job.service_window_end)}</p>
      </div>

      {/* Customer + Address */}
      <div className="p-4 space-y-3">
        {(customer.first_name || customer.last_name) && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white/5 rounded-lg flex items-center justify-center flex-shrink-0">
              <User className="h-4 w-4 text-gray-400" />
            </div>
            <div>
              <p className="text-white text-sm font-medium">
                {customer.first_name} {customer.last_name}
              </p>
              {customer.phone && (
                <a href={`tel:${customer.phone}`} className="text-blue-400 text-xs hover:text-blue-300 flex items-center gap-1">
                  <Phone className="h-3 w-3" />
                  {customer.phone}
                </a>
              )}
            </div>
          </div>
        )}

        {address && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white/5 rounded-lg flex items-center justify-center flex-shrink-0">
              <MapPin className="h-4 w-4 text-gray-400" />
            </div>
            <div className="flex-1">
              <p className="text-gray-300 text-sm">{address}</p>
              {mapsUrl && (
                <a
                  href={mapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 text-xs hover:text-blue-300 flex items-center gap-1 mt-0.5"
                >
                  <Navigation className="h-3 w-3" />
                  Get Directions
                </a>
              )}
            </div>
          </div>
        )}

        {job.notes && (
          <div className="bg-white/5 rounded-lg p-3">
            <p className="text-gray-400 text-xs font-medium mb-1">Notes</p>
            <p className="text-gray-300 text-sm">{job.notes}</p>
          </div>
        )}
      </div>

      {/* Status Action Button */}
      {nextStatus && (
        <div className="px-4 pb-4">
          <button
            onClick={() => onStatusChange(job.id, nextStatus.status)}
            disabled={updating === job.id}
            className={`w-full h-12 rounded-xl font-semibold text-sm text-white transition-colors flex items-center justify-center gap-2 ${nextStatus.color} disabled:opacity-50`}
          >
            {updating === job.id ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <nextStatus.icon className="h-4 w-4" />
                {nextStatus.label}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default function TechAppPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updating, setUpdating] = useState(null);
  const [filter, setFilter] = useState("active"); // active | all | completed

  const loadJobs = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const token = localStorage.getItem("fieldos_token");
      const res = await axios.get(`${BACKEND_URL}/api/v1/jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const allJobs = res.data || [];
      setJobs(allJobs);
    } catch {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
    // Auto-refresh every 60 seconds
    const interval = setInterval(() => loadJobs(true), 60000);
    return () => clearInterval(interval);
  }, [loadJobs]);

  const handleStatusChange = async (jobId, newStatus) => {
    setUpdating(jobId);
    try {
      const token = localStorage.getItem("fieldos_token");
      await axios.patch(
        `${BACKEND_URL}/api/v1/jobs/${jobId}`,
        { status: newStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, status: newStatus } : j))
      );
      toast.success(`Job marked as ${newStatus.replace(/_/g, " ").toLowerCase()}`);
    } catch {
      toast.error("Failed to update job status");
    } finally {
      setUpdating(null);
    }
  };

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // My jobs - filter by assigned_technician_id if tech role, else show all
  const myJobs = jobs.filter((j) => {
    if (user?.role === "TECH") {
      // In real implementation, tech would have their own technician record
      // For now show all jobs assigned to any technician
      return j.assigned_technician_id;
    }
    return true;
  });

  const filteredJobs = myJobs.filter((j) => {
    const jobDate = new Date(j.service_window_start);
    if (filter === "active") {
      return ["BOOKED", "EN_ROUTE", "ON_SITE"].includes(j.status);
    }
    if (filter === "today") {
      return jobDate >= today && jobDate < tomorrow;
    }
    if (filter === "completed") {
      return j.status === "COMPLETED";
    }
    return true;
  });

  // Sort: active first, then by start time
  filteredJobs.sort((a, b) => {
    const statusOrder = { EN_ROUTE: 0, ON_SITE: 1, BOOKED: 2, COMPLETED: 3, NO_SHOW: 4, CANCELLED: 5 };
    const ao = statusOrder[a.status] ?? 9;
    const bo = statusOrder[b.status] ?? 9;
    if (ao !== bo) return ao - bo;
    return new Date(a.service_window_start) - new Date(b.service_window_start);
  });

  const activeCount = myJobs.filter((j) => ["EN_ROUTE", "ON_SITE"].includes(j.status)).length;
  const todayCount = myJobs.filter((j) => {
    const d = new Date(j.service_window_start);
    return d >= today && d < tomorrow;
  }).length;

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white">
      {/* Top Bar */}
      <div className="sticky top-0 z-10 bg-[#0a0f1a]/95 backdrop-blur border-b border-white/10 px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500">Welcome back</p>
            <p className="text-white font-semibold">{user?.name || "Technician"}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadJobs(true)}
              disabled={refreshing}
              className="w-9 h-9 bg-white/5 hover:bg-white/10 rounded-xl flex items-center justify-center transition-colors"
            >
              <RefreshCw className={`h-4 w-4 text-gray-400 ${refreshing ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={() => { logout(); navigate("/login"); }}
              className="w-9 h-9 bg-white/5 hover:bg-white/10 rounded-xl flex items-center justify-center transition-colors"
            >
              <LogOut className="h-4 w-4 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Stats row */}
        <div className="flex gap-3 mt-3">
          <div className="flex-1 bg-blue-600/10 border border-blue-500/20 rounded-xl px-3 py-2 text-center">
            <p className="text-blue-300 text-lg font-bold">{todayCount}</p>
            <p className="text-blue-400/70 text-xs">Today</p>
          </div>
          <div className="flex-1 bg-purple-600/10 border border-purple-500/20 rounded-xl px-3 py-2 text-center">
            <p className="text-purple-300 text-lg font-bold">{activeCount}</p>
            <p className="text-purple-400/70 text-xs">In Progress</p>
          </div>
          <div className="flex-1 bg-green-600/10 border border-green-500/20 rounded-xl px-3 py-2 text-center">
            <p className="text-green-300 text-lg font-bold">
              {myJobs.filter((j) => j.status === "COMPLETED" && new Date(j.service_window_start) >= today).length}
            </p>
            <p className="text-green-400/70 text-xs">Done Today</p>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-1 mt-3 bg-white/5 rounded-xl p-1">
          {[
            { key: "active", label: "Active" },
            { key: "today", label: "Today" },
            { key: "all", label: "All" },
            { key: "completed", label: "Done" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFilter(tab.key)}
              className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filter === tab.key
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Job List */}
      <div className="px-4 py-4 space-y-4 pb-8">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="text-center py-16">
            <CheckCircle2 className="h-12 w-12 text-green-400/40 mx-auto mb-3" />
            <p className="text-gray-400 font-medium">No jobs here</p>
            <p className="text-gray-500 text-sm mt-1">
              {filter === "active" ? "All caught up!" : "Nothing to show"}
            </p>
          </div>
        ) : (
          filteredJobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onStatusChange={handleStatusChange}
              updating={updating}
            />
          ))
        )}
      </div>

      {/* Bottom nav hint */}
      <div className="fixed bottom-0 left-0 right-0 bg-[#0a0f1a]/95 backdrop-blur border-t border-white/10 px-4 py-3">
        <a
          href="/dashboard"
          className="flex items-center justify-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ChevronRight className="h-4 w-4" />
          Switch to full dashboard
        </a>
      </div>
    </div>
  );
}
