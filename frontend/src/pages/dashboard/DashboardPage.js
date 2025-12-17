import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { dashboardAPI, jobAPI, leadAPI, conversationAPI } from "../../lib/api";
import { toast } from "sonner";
import { 
  TrendingUp, Briefcase, Users, FileText, ArrowUpRight, ArrowDownRight,
  Clock, MapPin, ChevronRight, Calendar, MessageSquare, Phone, AlertTriangle,
  DollarSign, CheckCircle, Loader2
} from "lucide-react";

const statusColors = {
  NEW: "bg-blue-100 text-blue-800",
  BOOKED: "bg-yellow-100 text-yellow-800",
  EN_ROUTE: "bg-purple-100 text-purple-800",
  ON_SITE: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-800",
};

const urgencyColors = {
  EMERGENCY: "bg-red-500 text-white",
  URGENT: "bg-orange-500 text-white",
  ROUTINE: "bg-blue-100 text-blue-800",
};

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [upcomingJobs, setUpcomingJobs] = useState([]);
  const [recentLeads, setRecentLeads] = useState([]);
  const [recentConversations, setRecentConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [dashRes, jobsRes, leadsRes, convsRes] = await Promise.all([
        dashboardAPI.get(),
        jobAPI.list(),
        leadAPI.list(),
        conversationAPI.list()
      ]);
      
      setData(dashRes.data);
      
      // Get upcoming 7 days of jobs
      const now = new Date();
      const sevenDaysLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      const upcoming = jobsRes.data
        .filter(job => {
          if (!job.service_window_start) return false;
          const jobDate = new Date(job.service_window_start);
          return jobDate >= now && jobDate <= sevenDaysLater && job.status !== "COMPLETED" && job.status !== "CANCELLED";
        })
        .sort((a, b) => new Date(a.service_window_start) - new Date(b.service_window_start))
        .slice(0, 10);
      setUpcomingJobs(upcoming);
      
      // Get recent leads (last 7 days)
      const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      const recent = leadsRes.data
        .filter(lead => new Date(lead.created_at) >= sevenDaysAgo)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 5);
      setRecentLeads(recent);
      
      // Get recent conversations
      setRecentConversations(convsRes.data.slice(0, 5));
      
    } catch (error) {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleLeadClick = (leadId) => {
    // Navigate to leads page with lead ID as query param to open modal
    navigate(`/leads?open=${leadId}`);
  };

  if (loading) {
    return (
      <Layout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  const metrics = data?.metrics || {};
  const charts = data?.charts || {};

  // Calculate additional metrics
  const totalRevenue = upcomingJobs.reduce((sum, j) => sum + (j.estimated_amount || 0), 0);
  const emergencyJobs = upcomingJobs.filter(j => j.priority === "EMERGENCY").length;
  const unassignedJobs = upcomingJobs.filter(j => !j.assigned_technician_id).length;

  return (
    <Layout title="Dashboard" subtitle="Your operations at a glance">
      {/* Top Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
        <MetricCard
          title="Leads (Week)"
          value={metrics.leads_this_week || 0}
          icon={TrendingUp}
          color="blue"
          onClick={() => navigate('/leads')}
        />
        <MetricCard
          title="Leads (Month)"
          value={metrics.leads_this_month || 0}
          icon={Users}
          color="green"
          onClick={() => navigate('/leads')}
        />
        <MetricCard
          title="Jobs (Week)"
          value={metrics.jobs_this_week || 0}
          icon={Briefcase}
          color="purple"
          onClick={() => navigate('/jobs')}
        />
        <MetricCard
          title="Quote Conv."
          value={`${metrics.quote_conversion || 0}%`}
          icon={FileText}
          color="orange"
          onClick={() => navigate('/quotes')}
        />
        <MetricCard
          title="Upcoming Jobs"
          value={upcomingJobs.length}
          icon={Calendar}
          color="cyan"
          onClick={() => navigate('/calendar')}
        />
        <MetricCard
          title="Unassigned"
          value={unassignedJobs}
          icon={AlertTriangle}
          color={unassignedJobs > 0 ? "red" : "gray"}
          onClick={() => navigate('/dispatch')}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upcoming Jobs - Next 7 Days */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Calendar className="h-5 w-5 text-primary" />
                Upcoming Jobs (Next 7 Days)
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => navigate('/calendar')}>
                View Calendar <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {upcomingJobs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Calendar className="h-12 w-12 mx-auto mb-2 opacity-30" />
                <p>No upcoming jobs scheduled</p>
                <Button variant="outline" className="mt-4" onClick={() => navigate('/jobs')}>
                  Schedule a Job
                </Button>
              </div>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {upcomingJobs.map((job) => (
                  <JobRow 
                    key={job.id} 
                    job={job} 
                    onClick={() => navigate('/jobs')}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Recent Leads - Clickable */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="font-heading text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-accent" />
                  Recent Leads
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => navigate('/leads')}>
                  View All <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {recentLeads.length === 0 ? (
                <p className="text-muted-foreground text-sm text-center py-4">No recent leads</p>
              ) : (
                <div className="space-y-2">
                  {recentLeads.map((lead) => (
                    <LeadRow 
                      key={lead.id} 
                      lead={lead} 
                      onClick={() => handleLeadClick(lead.id)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Conversations */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="font-heading text-base flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-primary" />
                  Recent Messages
                </CardTitle>
                <Button variant="ghost" size="sm" onClick={() => navigate('/conversations')}>
                  Inbox <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {recentConversations.length === 0 ? (
                <p className="text-muted-foreground text-sm text-center py-4">No recent messages</p>
              ) : (
                <div className="space-y-2">
                  {recentConversations.map((conv) => (
                    <div 
                      key={conv.id}
                      className="p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => navigate('/conversations')}
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium">
                          {conv.customer?.first_name} {conv.customer?.last_name}
                        </p>
                        <Badge variant="outline" className="text-xs">
                          {conv.status}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {conv.primary_channel} • {formatTimeAgo(conv.last_message_at)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Bottom Row - Charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {/* Leads by Source */}
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/leads')}>
          <CardHeader className="pb-2">
            <CardTitle className="font-heading text-base">Leads by Source</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(charts.leads_by_source || {}).length === 0 ? (
                <p className="text-muted-foreground text-sm text-center py-4">No data</p>
              ) : (
                Object.entries(charts.leads_by_source || {}).map(([source, count]) => (
                  <div key={source} className="flex items-center justify-between">
                    <span className="text-sm">{source.replace('_', ' ')}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${Math.min(count * 20, 100)}%` }}
                        />
                      </div>
                      <span className="text-sm font-mono w-6 text-right">{count}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Jobs by Status */}
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/jobs')}>
          <CardHeader className="pb-2">
            <CardTitle className="font-heading text-base">Jobs by Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(charts.jobs_by_status || {}).length === 0 ? (
                <p className="text-muted-foreground text-sm text-center py-4">No data</p>
              ) : (
                Object.entries(charts.jobs_by_status || {}).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <Badge className={statusColors[status] || "bg-gray-100"}>{status}</Badge>
                    <span className="text-sm font-mono">{count}</span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="font-heading text-base">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2">
            <Button variant="outline" size="sm" className="h-auto py-3" onClick={() => navigate('/dispatch')}>
              <Briefcase className="h-4 w-4 mr-1" />
              Dispatch
            </Button>
            <Button variant="outline" size="sm" className="h-auto py-3" onClick={() => navigate('/conversations')}>
              <MessageSquare className="h-4 w-4 mr-1" />
              Inbox
            </Button>
            <Button variant="outline" size="sm" className="h-auto py-3" onClick={() => navigate('/customers')}>
              <Users className="h-4 w-4 mr-1" />
              Customers
            </Button>
            <Button variant="outline" size="sm" className="h-auto py-3" onClick={() => navigate('/reports')}>
              <TrendingUp className="h-4 w-4 mr-1" />
              Reports
            </Button>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

function MetricCard({ title, value, icon: Icon, color, onClick }) {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    purple: "bg-purple-50 text-purple-600",
    orange: "bg-orange-50 text-orange-600",
    cyan: "bg-cyan-50 text-cyan-600",
    red: "bg-red-50 text-red-600",
    gray: "bg-gray-50 text-gray-600",
  };

  return (
    <Card 
      className="cursor-pointer hover:shadow-md transition-all hover:-translate-y-0.5" 
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-xs text-muted-foreground">{title}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function JobRow({ job, onClick }) {
  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    if (date.toDateString() === today.toDateString()) return "Today";
    if (date.toDateString() === tomorrow.toDateString()) return "Tomorrow";
    return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div 
      className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors border-l-4"
      style={{ borderLeftColor: job.priority === "EMERGENCY" ? "#ef4444" : job.priority === "HIGH" ? "#f97316" : "#3b82f6" }}
      onClick={onClick}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium truncate">
            {job.customer?.first_name} {job.customer?.last_name}
          </p>
          {job.priority === "EMERGENCY" && (
            <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
          <span>{job.job_type}</span>
          {job.property && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {job.property.city}
            </span>
          )}
        </div>
      </div>
      <div className="text-right flex-shrink-0">
        <p className="text-sm font-medium">{formatDate(job.service_window_start)}</p>
        <p className="text-xs text-muted-foreground">{formatTime(job.service_window_start)}</p>
      </div>
      <Badge className={statusColors[job.status] || "bg-gray-100"} variant="outline">
        {job.status}
      </Badge>
    </div>
  );
}

function LeadRow({ lead, onClick }) {
  return (
    <div 
      className="p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors border-l-2"
      style={{ borderLeftColor: lead.urgency === "EMERGENCY" ? "#ef4444" : lead.urgency === "URGENT" ? "#f97316" : "#3b82f6" }}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium truncate flex-1">{lead.issue_type || "New Lead"}</p>
        <Badge className={urgencyColors[lead.urgency]} variant="outline" className="text-xs ml-2">
          {lead.urgency}
        </Badge>
      </div>
      {lead.customer && (
        <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
          <Phone className="h-3 w-3" />
          {lead.customer.first_name} {lead.customer.last_name}
        </p>
      )}
      <div className="flex items-center justify-between mt-1">
        <span className="text-xs text-muted-foreground">{lead.source?.replace('_', ' ')}</span>
        <Badge className={statusColors[lead.status] || "bg-gray-100"} variant="outline" className="text-xs">
          {lead.status}
        </Badge>
      </div>
    </div>
  );
}

function formatTimeAgo(dateStr) {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}
