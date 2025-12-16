import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { dashboardAPI } from "../../lib/api";
import { toast } from "sonner";
import { 
  TrendingUp, 
  Briefcase, 
  Users, 
  FileText,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  MapPin,
  ChevronRight,
  Calendar,
  MessageSquare,
  Phone
} from "lucide-react";

const statusColors = {
  NEW: "bg-blue-100 text-blue-800",
  BOOKED: "bg-yellow-100 text-yellow-800",
  EN_ROUTE: "bg-purple-100 text-purple-800",
  ON_SITE: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-800",
};

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboard();
    // Polling for real-time updates every 30 seconds
    const interval = setInterval(fetchDashboard, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await dashboardAPI.get();
      setData(response.data);
    } catch (error) {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </Layout>
    );
  }

  const metrics = data?.metrics || {};
  const jobsToday = data?.jobs_today || [];
  const jobsTomorrow = data?.jobs_tomorrow || [];
  const recentLeads = data?.recent_leads || [];
  const charts = data?.charts || {};

  return (
    <Layout title="Dashboard" subtitle="Your field service operations at a glance">
      {/* Metrics Grid - All Clickable */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard
          title="Leads This Week"
          value={metrics.leads_this_week || 0}
          icon={TrendingUp}
          trend="+12%"
          trendUp
          onClick={() => navigate('/leads')}
        />
        <MetricCard
          title="Leads This Month"
          value={metrics.leads_this_month || 0}
          icon={Users}
          trend="+8%"
          trendUp
          onClick={() => navigate('/leads')}
        />
        <MetricCard
          title="Jobs This Week"
          value={metrics.jobs_this_week || 0}
          icon={Briefcase}
          trend="+5%"
          trendUp
          onClick={() => navigate('/jobs')}
        />
        <MetricCard
          title="Quote Conversion"
          value={`${metrics.quote_conversion || 0}%`}
          icon={FileText}
          trend="-2%"
          trendUp={false}
          onClick={() => navigate('/quotes')}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Jobs Today - Clickable */}
        <Card 
          className="lg:col-span-2 cursor-pointer hover:shadow-md transition-shadow" 
          data-testid="jobs-today-card"
          onClick={() => navigate('/calendar')}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <Clock className="h-5 w-5 text-primary" />
                Today's Schedule
              </CardTitle>
              <Button variant="ghost" size="sm" className="text-primary">
                View Calendar <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </CardHeader>
          <CardContent onClick={(e) => e.stopPropagation()}>
            {jobsToday.length === 0 ? (
              <p className="text-muted-foreground text-sm py-8 text-center">
                No jobs scheduled for today
              </p>
            ) : (
              <div className="space-y-3">
                {jobsToday.map((job) => (
                  <JobCard 
                    key={job.id} 
                    job={job} 
                    onClick={() => navigate('/jobs')}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Leads - Clickable */}
        <Card 
          className="cursor-pointer hover:shadow-md transition-shadow" 
          data-testid="recent-leads-card"
          onClick={() => navigate('/leads')}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-accent" />
                Recent Leads
              </CardTitle>
              <Button variant="ghost" size="sm" className="text-primary">
                View All <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </CardHeader>
          <CardContent onClick={(e) => e.stopPropagation()}>
            {recentLeads.length === 0 ? (
              <p className="text-muted-foreground text-sm py-8 text-center">
                No recent leads
              </p>
            ) : (
              <div className="space-y-3">
                {recentLeads.map((lead) => (
                  <LeadCard 
                    key={lead.id} 
                    lead={lead} 
                    onClick={() => navigate('/leads')}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tomorrow's Jobs - Clickable */}
      <Card 
        className="mt-6 cursor-pointer hover:shadow-md transition-shadow" 
        data-testid="jobs-tomorrow-card"
        onClick={() => navigate('/calendar')}
      >
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              Tomorrow's Schedule
            </CardTitle>
            <Button variant="ghost" size="sm" className="text-primary">
              View Calendar <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </CardHeader>
        <CardContent onClick={(e) => e.stopPropagation()}>
          {jobsTomorrow.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              No jobs scheduled for tomorrow
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {jobsTomorrow.map((job) => (
                <JobCard key={job.id} job={job} compact onClick={() => navigate('/jobs')} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        <Button 
          variant="outline" 
          className="h-auto py-4 flex flex-col items-center gap-2"
          onClick={() => navigate('/dispatch')}
        >
          <Briefcase className="h-5 w-5" />
          <span>Dispatch Board</span>
        </Button>
        <Button 
          variant="outline" 
          className="h-auto py-4 flex flex-col items-center gap-2"
          onClick={() => navigate('/conversations')}
        >
          <MessageSquare className="h-5 w-5" />
          <span>Inbox</span>
        </Button>
        <Button 
          variant="outline" 
          className="h-auto py-4 flex flex-col items-center gap-2"
          onClick={() => navigate('/customers')}
        >
          <Users className="h-5 w-5" />
          <span>Customers</span>
        </Button>
        <Button 
          variant="outline" 
          className="h-auto py-4 flex flex-col items-center gap-2"
          onClick={() => navigate('/reports')}
        >
          <TrendingUp className="h-5 w-5" />
          <span>Reports</span>
        </Button>
      </div>

      {/* Charts Section - Clickable */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <Card 
          className="cursor-pointer hover:shadow-md transition-shadow" 
          data-testid="leads-by-source-card"
          onClick={() => navigate('/leads')}
        >
          <CardHeader className="pb-3">
            <CardTitle className="font-heading text-lg">Leads by Source</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(charts.leads_by_source || {}).map(([source, count]) => (
                <div key={source} className="flex items-center justify-between">
                  <span className="text-sm">{source.replace('_', ' ')}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-primary rounded-full"
                        style={{ width: `${Math.min(count * 10, 100)}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono font-medium w-8">{count}</span>
                  </div>
                </div>
              ))}
              {Object.keys(charts.leads_by_source || {}).length === 0 && (
                <p className="text-muted-foreground text-sm text-center py-4">No data</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card 
          className="cursor-pointer hover:shadow-md transition-shadow" 
          data-testid="jobs-by-status-card"
          onClick={() => navigate('/jobs')}
        >
          <CardHeader className="pb-3">
            <CardTitle className="font-heading text-lg">Jobs by Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(charts.jobs_by_status || {}).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between">
                  <Badge className={statusColors[status] || "bg-gray-100"}>
                    {status}
                  </Badge>
                  <span className="text-sm font-mono font-medium">{count}</span>
                </div>
              ))}
              {Object.keys(charts.jobs_by_status || {}).length === 0 && (
                <p className="text-muted-foreground text-sm text-center py-4">No data</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

function MetricCard({ title, value, icon: Icon, trend, trendUp, onClick }) {
  return (
    <Card 
      className="card-industrial cursor-pointer hover:shadow-md transition-shadow" 
      data-testid={`metric-${title.toLowerCase().replace(/\s/g, '-')}`}
      onClick={onClick}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">{title}</p>
            <p className="text-3xl font-heading font-bold tracking-tight">{value}</p>
          </div>
          <div className="p-2 bg-primary/10 rounded-md">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
        {trend && (
          <div className={`flex items-center gap-1 mt-3 text-sm ${trendUp ? 'text-green-600' : 'text-red-600'}`}>
            {trendUp ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
            <span>{trend} from last period</span>
          </div>
        )}
        <div className="flex items-center justify-end mt-2">
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardContent>
    </Card>
  );
}

function JobCard({ job, compact, onClick }) {
  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div 
      className={`relative p-4 bg-muted/50 rounded-md border border-border hover:border-primary/30 transition-colors cursor-pointer ${compact ? '' : ''}`}
      onClick={onClick}
    >
      <div className={`status-bar status-bar-${job.status?.toLowerCase()}`} />
      <div className="pl-3">
        <div className="flex items-start justify-between mb-2">
          <div>
            <p className="font-medium text-sm">
              {job.customer?.first_name} {job.customer?.last_name}
            </p>
            <p className="text-xs text-muted-foreground">{job.job_type}</p>
          </div>
          <Badge className={statusColors[job.status] || "bg-gray-100"}>
            {job.status}
          </Badge>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatTime(job.service_window_start)} - {formatTime(job.service_window_end)}
          </span>
          {job.property && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {job.property.city}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function LeadCard({ lead, onClick }) {
  const urgencyColors = {
    EMERGENCY: "bg-red-100 text-red-800",
    URGENT: "bg-orange-100 text-orange-800",
    ROUTINE: "bg-blue-100 text-blue-800",
  };

  return (
    <div 
      className="p-3 bg-muted/50 rounded-md border border-border hover:border-primary/30 transition-colors cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-1">
        <p className="font-medium text-sm">{lead.issue_type || "New Lead"}</p>
        <Badge className={urgencyColors[lead.urgency] || "bg-gray-100"} variant="outline">
          {lead.urgency}
        </Badge>
      </div>
      {lead.customer && (
        <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
          <Phone className="h-3 w-3" />
          {lead.customer.first_name} {lead.customer.last_name}
        </p>
      )}
      <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
        {lead.description || "No description"}
      </p>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{lead.source?.replace('_', ' ')}</span>
        <Badge className={statusColors[lead.status] || "bg-gray-100"}>
          {lead.status}
        </Badge>
      </div>
    </div>
  );
}
