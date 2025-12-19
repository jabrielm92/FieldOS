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
import { toast } from "sonner";

// Helper to display lead source nicely
const formatSource = (source) => {
  const sourceLabels = {
    'VAPI_CALL': 'AI Receptionist',
    'WEB_FORM': 'Web Form',
    'PHONE': 'Phone',
    'WALK_IN': 'Walk-in',
    'REFERRAL': 'Referral',
    'MANUAL': 'Manual',
  };
  return sourceLabels[source] || source?.replace('_', ' ') || 'Unknown';
};
import { 
  TrendingUp, 
  TrendingDown,
  Users, 
  Briefcase, 
  FileText,
  DollarSign,
  Target,
  CheckCircle,
  BarChart3,
  PieChart,
  Activity
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart as RechartsPie,
  Pie,
  Cell
} from "recharts";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const COLORS = ['#0066CC', '#FF6B00', '#22C55E', '#EAB308', '#EF4444', '#8B5CF6', '#06B6D4'];

export default function ReportsPage() {
  const [period, setPeriod] = useState("30d");
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, [period]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("fieldos_token");
      const response = await axios.get(`${API_URL}/api/v1/analytics/overview?period=${period}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAnalytics(response.data);
    } catch (error) {
      toast.error("Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0
    }).format(amount || 0);
  };

  if (loading) {
    return (
      <Layout title="Reports & Analytics">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </Layout>
    );
  }

  const summary = analytics?.summary || {};
  const conversionRates = analytics?.conversion_rates || {};
  const dailyTrends = analytics?.daily_trends || [];
  const leadsBySource = analytics?.leads?.by_source || {};
  const leadsByStatus = analytics?.leads?.by_status || {};
  const jobsByType = analytics?.jobs?.by_type || {};
  const jobsByStatus = analytics?.jobs?.by_status || {};
  const techPerformance = analytics?.technician_performance || [];

  // Prepare chart data
  const sourceChartData = Object.entries(leadsBySource).map(([name, value]) => ({
    name: formatSource(name),
    value
  }));

  const jobTypeChartData = Object.entries(jobsByType).map(([name, value]) => ({
    name,
    value
  }));

  return (
    <Layout title="Reports & Analytics" subtitle="Track performance and business metrics">
      {/* Period Selector */}
      <div className="flex justify-end mb-6">
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[180px]" data-testid="period-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7d">Last 7 days</SelectItem>
            <SelectItem value="30d">Last 30 days</SelectItem>
            <SelectItem value="90d">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard
          title="Total Leads"
          value={summary.total_leads || 0}
          icon={Users}
          color="text-blue-600"
          bgColor="bg-blue-50"
        />
        <KPICard
          title="Total Jobs"
          value={summary.total_jobs || 0}
          icon={Briefcase}
          color="text-orange-600"
          bgColor="bg-orange-50"
        />
        <KPICard
          title="Completed Jobs"
          value={summary.completed_jobs || 0}
          icon={CheckCircle}
          color="text-green-600"
          bgColor="bg-green-50"
        />
        <KPICard
          title="Total Revenue"
          value={formatCurrency(summary.total_revenue)}
          icon={DollarSign}
          color="text-emerald-600"
          bgColor="bg-emerald-50"
          isLarge
        />
      </div>

      {/* Revenue Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card className="card-industrial">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Potential Revenue</p>
                <p className="text-2xl font-bold text-blue-600 font-mono">{formatCurrency(summary.potential_revenue)}</p>
                <p className="text-xs text-muted-foreground">From booked jobs</p>
              </div>
              <div className="p-2 rounded-lg bg-blue-50">
                <Target className="h-5 w-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="card-industrial">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Completed Revenue</p>
                <p className="text-2xl font-bold text-green-600 font-mono">{formatCurrency(summary.job_completed_revenue)}</p>
                <p className="text-xs text-muted-foreground">From completed jobs</p>
              </div>
              <div className="p-2 rounded-lg bg-green-50">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="card-industrial">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Invoiced Revenue</p>
                <p className="text-2xl font-bold text-emerald-600 font-mono">{formatCurrency(summary.invoiced_revenue)}</p>
                <p className="text-xs text-muted-foreground">Paid invoices</p>
              </div>
              <div className="p-2 rounded-lg bg-emerald-50">
                <DollarSign className="h-5 w-5 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Conversion Rates */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <ConversionCard
          title="Lead → Job"
          rate={conversionRates.lead_to_job || 0}
          description="Leads converted to booked jobs"
          color="bg-blue-500"
        />
        <ConversionCard
          title="Quote Acceptance"
          rate={conversionRates.quote_acceptance || 0}
          description="Quotes accepted by customers"
          color="bg-green-500"
        />
        <ConversionCard
          title="Job Completion"
          rate={conversionRates.job_completion || 0}
          description="Jobs completed successfully"
          color="bg-purple-500"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Daily Trends */}
        <Card data-testid="daily-trends-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-heading flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Daily Trends (14 days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyTrends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(val) => {
                    const d = new Date(val);
                    return `${d.getMonth()+1}/${d.getDate()}`;
                  }}
                  label={{ value: 'Date', position: 'insideBottom', offset: -5, fontSize: 11, fill: '#6b7280' }}
                />
                <YAxis 
                  tick={{ fontSize: 12 }} 
                  label={{ value: 'Count', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#6b7280' }}
                />
                <Tooltip formatter={(value, name) => [value, name]} />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />
                <Line 
                  type="monotone" 
                  dataKey="leads" 
                  stroke="#0066CC" 
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Leads"
                />
                <Line 
                  type="monotone" 
                  dataKey="jobs" 
                  stroke="#FF6B00" 
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Jobs"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Leads by Source */}
        <Card data-testid="leads-source-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-heading flex items-center gap-2">
              <PieChart className="h-5 w-5 text-primary" />
              Leads by Source
            </CardTitle>
          </CardHeader>
          <CardContent>
            {sourceChartData.length === 0 ? (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <RechartsPie>
                  <Pie
                    data={sourceChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {sourceChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPie>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Jobs by Type */}
        <Card data-testid="jobs-type-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-heading flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              Jobs by Type
            </CardTitle>
          </CardHeader>
          <CardContent>
            {jobTypeChartData.length === 0 ? (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={jobTypeChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    type="number" 
                    tick={{ fontSize: 12 }} 
                    label={{ value: 'Number of Jobs', position: 'insideBottom', offset: -5, fontSize: 11, fill: '#6b7280' }}
                  />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={100} />
                  <Tooltip formatter={(value) => [`${value} jobs`, 'Count']} />
                  <Bar dataKey="value" fill="#0066CC" radius={[0, 4, 4, 0]} name="Jobs" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Technician Performance */}
        <Card data-testid="tech-performance-chart">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-heading flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Technician Performance
            </CardTitle>
          </CardHeader>
          <CardContent>
            {techPerformance.length === 0 ? (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={techPerformance}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    dataKey="technician_name" 
                    tick={{ fontSize: 12 }} 
                    label={{ value: 'Technician', position: 'insideBottom', offset: -5, fontSize: 11, fill: '#6b7280' }}
                  />
                  <YAxis 
                    tick={{ fontSize: 12 }} 
                    label={{ value: 'Jobs Completed', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#6b7280' }}
                  />
                  <Tooltip formatter={(value) => [`${value} jobs`, 'Completed']} />
                  <Legend wrapperStyle={{ paddingTop: '10px' }} />
                  <Bar dataKey="completed_jobs" fill="#22C55E" radius={[4, 4, 0, 0]} name="Completed Jobs" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Status Breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Lead Status */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-heading">Lead Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(leadsByStatus).map(([status, count]) => (
                <StatusBar key={status} label={status} count={count} total={summary.total_leads} />
              ))}
              {Object.keys(leadsByStatus).length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">No data</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Job Status */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-heading">Job Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(jobsByStatus).map(([status, count]) => (
                <StatusBar key={status} label={status} count={count} total={summary.total_jobs} color="bg-orange-500" />
              ))}
              {Object.keys(jobsByStatus).length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">No data</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

function KPICard({ title, value, icon: Icon, color, bgColor, isLarge }) {
  return (
    <Card className="card-industrial" data-testid={`kpi-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">{title}</p>
            <p className={`font-heading font-bold tracking-tight ${isLarge ? 'text-2xl' : 'text-3xl'}`}>
              {value}
            </p>
          </div>
          <div className={`p-3 rounded-lg ${bgColor}`}>
            <Icon className={`h-6 w-6 ${color}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ConversionCard({ title, rate, description, color }) {
  return (
    <Card className="card-industrial">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-sm">{title}</h3>
          <Badge variant="outline" className="font-mono">
            {rate}%
          </Badge>
        </div>
        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
          <div 
            className={`h-full ${color} rounded-full transition-all duration-500`}
            style={{ width: `${Math.min(rate, 100)}%` }}
          />
        </div>
        <p className="text-xs text-muted-foreground mt-2">{description}</p>
      </CardContent>
    </Card>
  );
}

function StatusBar({ label, count, total, color = "bg-primary" }) {
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
  
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm w-28 truncate">{label.replace('_', ' ')}</span>
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-sm font-mono w-12 text-right">{count}</span>
    </div>
  );
}
