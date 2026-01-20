import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import { reportsAPI } from "../../lib/api";
import { toast } from "sonner";
import { DollarSign, TrendingUp, Clock, AlertTriangle, Calendar, BarChart3, PieChart } from "lucide-react";

export default function RevenueReportsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const res = await reportsAPI.getRevenue({ start_date: startDate, end_date: endDate });
      setData(res.data);
    } catch (e) { toast.error("Failed to load report"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchReport(); }, []);

  const StatCard = ({ title, value, icon: Icon, color, subtitle }) => (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          <div className={`p-3 rounded-lg ${color.replace('text-', 'bg-')}/10`}>
            <Icon className={`h-6 w-6 ${color}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <Layout title="Revenue Reports" subtitle="Financial analytics and payment tracking">
      {/* Date Filter */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex items-end gap-4">
            <div className="space-y-1">
              <Label>Start Date</Label>
              <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-40" />
            </div>
            <div className="space-y-1">
              <Label>End Date</Label>
              <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-40" />
            </div>
            <Button onClick={fetchReport} disabled={loading}>{loading ? "Loading..." : "Apply"}</Button>
            <div className="flex gap-2 ml-auto">
              {["7", "30", "90"].map(d => (
                <Button key={d} variant="outline" size="sm" onClick={() => {
                  const end = new Date(), start = new Date();
                  start.setDate(start.getDate() - parseInt(d));
                  setStartDate(start.toISOString().split('T')[0]);
                  setEndDate(end.toISOString().split('T')[0]);
                }}>Last {d}d</Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
      ) : data ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
            <StatCard title="Total Invoiced" value={`$${data.summary.total_invoiced.toLocaleString()}`} icon={DollarSign} color="text-blue-600" />
            <StatCard title="Total Paid" value={`$${data.summary.total_paid.toLocaleString()}`} icon={TrendingUp} color="text-green-600" />
            <StatCard title="Outstanding" value={`$${data.summary.total_outstanding.toLocaleString()}`} icon={Clock} color="text-yellow-600" />
            <StatCard title="Overdue" value={`$${data.summary.total_overdue.toLocaleString()}`} icon={AlertTriangle} color="text-red-600" />
            <StatCard title="Collection Rate" value={`${data.summary.collection_rate}%`} icon={PieChart} color="text-purple-600" subtitle={`${data.invoices_count.paid}/${data.invoices_count.total} invoices`} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue by Job Type */}
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5" />Revenue by Job Type</CardTitle></CardHeader>
              <CardContent>
                {Object.keys(data.revenue_by_job_type).length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">No job data for this period</p>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(data.revenue_by_job_type).sort((a, b) => b[1] - a[1]).map(([type, amount]) => {
                      const max = Math.max(...Object.values(data.revenue_by_job_type));
                      const pct = max > 0 ? (amount / max) * 100 : 0;
                      return (
                        <div key={type}>
                          <div className="flex justify-between text-sm mb-1">
                            <span>{type}</span>
                            <span className="font-mono font-medium">${amount.toLocaleString()}</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Daily Revenue */}
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Calendar className="h-5 w-5" />Daily Revenue</CardTitle></CardHeader>
              <CardContent>
                {Object.keys(data.daily_revenue).length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">No payments in this period</p>
                ) : (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {Object.entries(data.daily_revenue).reverse().map(([date, amount]) => (
                      <div key={date} className="flex justify-between items-center p-2 bg-muted/50 rounded">
                        <span className="text-sm">{new Date(date + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                        <Badge variant="secondary" className="font-mono">${amount.toLocaleString()}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Invoice Counts */}
          <Card className="mt-6">
            <CardHeader><CardTitle>Invoice Summary</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4 text-center">
                <div className="p-4 bg-muted/50 rounded-lg">
                  <p className="text-3xl font-bold">{data.invoices_count.total}</p>
                  <p className="text-sm text-muted-foreground">Total</p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <p className="text-3xl font-bold text-green-600">{data.invoices_count.paid}</p>
                  <p className="text-sm text-muted-foreground">Paid</p>
                </div>
                <div className="p-4 bg-yellow-50 rounded-lg">
                  <p className="text-3xl font-bold text-yellow-600">{data.invoices_count.outstanding}</p>
                  <p className="text-sm text-muted-foreground">Outstanding</p>
                </div>
                <div className="p-4 bg-red-50 rounded-lg">
                  <p className="text-3xl font-bold text-red-600">{data.invoices_count.overdue}</p>
                  <p className="text-sm text-muted-foreground">Overdue</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </Layout>
  );
}
