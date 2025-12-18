import { useState, useEffect, useCallback } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Progress } from "../../components/ui/progress";
import { Separator } from "../../components/ui/separator";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../components/ui/tabs";
import { campaignAPI } from "../../lib/api";
import { toast } from "sonner";
import { 
  Plus, Megaphone, Play, Pause, Check, Clock, Users, 
  MessageSquare, Target, BarChart3, Send, Calendar,
  CheckCircle, XCircle, Loader2, Settings,
  TrendingUp, Trash2, RefreshCw
} from "lucide-react";

const statusColors = {
  DRAFT: "bg-gray-100 text-gray-800",
  RUNNING: "bg-green-100 text-green-800",
  PAUSED: "bg-yellow-100 text-yellow-800",
  COMPLETED: "bg-blue-100 text-blue-800",
};

const typeColors = {
  REACTIVATION: "bg-purple-100 text-purple-800",
  TUNEUP: "bg-cyan-100 text-cyan-800",
  SPECIAL_OFFER: "bg-orange-100 text-orange-800",
};

const typeIcons = {
  REACTIVATION: Target,
  TUNEUP: Settings,
  SPECIAL_OFFER: TrendingUp,
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [filter, setFilter] = useState("all");

  const fetchCampaigns = useCallback(async () => {
    try {
      const response = await campaignAPI.list();
      setCampaigns(response.data);
    } catch (error) {
      toast.error("Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
    const interval = setInterval(fetchCampaigns, 30000);
    return () => clearInterval(interval);
  }, [fetchCampaigns]);

  const handleCampaignClick = (campaign) => {
    setSelectedCampaign(campaign);
    setShowDetailModal(true);
  };

  const handleDeleteCampaign = async (campaignId) => {
    if (!window.confirm("Are you sure you want to delete this campaign?")) return;
    try {
      await campaignAPI.delete(campaignId);
      toast.success("Campaign deleted");
      fetchCampaigns();
    } catch (error) {
      toast.error("Failed to delete campaign");
    }
  };

  const filteredCampaigns = campaigns.filter(c => {
    if (filter === "all") return true;
    return c.status === filter;
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const stats = {
    total: campaigns.length,
    active: campaigns.filter(c => c.status === "RUNNING").length,
    draft: campaigns.filter(c => c.status === "DRAFT").length,
    completed: campaigns.filter(c => c.status === "COMPLETED").length,
  };

  return (
    <Layout title="Campaigns" subtitle="Manage reactivation and marketing campaigns">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Megaphone className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">{stats.total}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <Play className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Active</p>
              <p className="text-2xl font-bold text-green-600">{stats.active}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gray-100 rounded-lg">
              <Clock className="h-5 w-5 text-gray-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Drafts</p>
              <p className="text-2xl font-bold">{stats.draft}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <CheckCircle className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Completed</p>
              <p className="text-2xl font-bold text-blue-600">{stats.completed}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-2">
          <Button 
            variant={filter === "all" ? "default" : "outline"} 
            size="sm"
            onClick={() => setFilter("all")}
          >
            All
          </Button>
          <Button 
            variant={filter === "RUNNING" ? "default" : "outline"} 
            size="sm"
            onClick={() => setFilter("RUNNING")}
          >
            <Play className="h-3 w-3 mr-1" /> Active
          </Button>
          <Button 
            variant={filter === "DRAFT" ? "default" : "outline"} 
            size="sm"
            onClick={() => setFilter("DRAFT")}
          >
            <Clock className="h-3 w-3 mr-1" /> Drafts
          </Button>
          <Button 
            variant={filter === "COMPLETED" ? "default" : "outline"} 
            size="sm"
            onClick={() => setFilter("COMPLETED")}
          >
            <Check className="h-3 w-3 mr-1" /> Completed
          </Button>
        </div>

        <CreateCampaignDialog 
          open={showCreateDialog} 
          onOpenChange={setShowCreateDialog}
          onSuccess={fetchCampaigns}
        />
      </div>

      {/* Campaigns Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filteredCampaigns.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Megaphone className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-muted-foreground mb-4">
              {filter === "all" ? "No campaigns yet" : `No ${filter.toLowerCase()} campaigns`}
            </p>
            <Button onClick={() => setShowCreateDialog(true)}>
              Create your first campaign
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCampaigns.map((campaign) => (
            <CampaignCard 
              key={campaign.id} 
              campaign={campaign} 
              formatDate={formatDate}
              onClick={() => handleCampaignClick(campaign)}
              onDelete={() => handleDeleteCampaign(campaign.id)}
            />
          ))}
        </div>
      )}

      {/* Campaign Detail Modal */}
      <CampaignDetailModal
        campaign={selectedCampaign}
        open={showDetailModal}
        onOpenChange={setShowDetailModal}
        onUpdate={fetchCampaigns}
        formatDate={formatDate}
      />
    </Layout>
  );
}

function CampaignCard({ campaign, formatDate, onClick, onDelete }) {
  const TypeIcon = typeIcons[campaign.type] || Megaphone;
  const totalRecipients = campaign.total_recipients || 0;

  return (
    <Card 
      className="card-industrial cursor-pointer hover:shadow-md transition-shadow overflow-hidden"
      onClick={onClick}
    >
      <div className={`h-1 ${
        campaign.status === "RUNNING" ? "bg-green-500" : 
        campaign.status === "PAUSED" ? "bg-yellow-500" :
        campaign.status === "COMPLETED" ? "bg-blue-500" : "bg-gray-300"
      }`} />
      
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              campaign.type === "REACTIVATION" ? "bg-purple-100" :
              campaign.type === "TUNEUP" ? "bg-cyan-100" : "bg-orange-100"
            }`}>
              <TypeIcon className={`h-5 w-5 ${
                campaign.type === "REACTIVATION" ? "text-purple-600" :
                campaign.type === "TUNEUP" ? "text-cyan-600" : "text-orange-600"
              }`} />
            </div>
            <div>
              <h3 className="font-medium">{campaign.name}</h3>
              <Badge className={typeColors[campaign.type]} variant="outline">
                {campaign.type?.replace('_', ' ')}
              </Badge>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={statusColors[campaign.status]}>
              {campaign.status}
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {campaign.message_template && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-4 bg-muted/50 p-2 rounded italic">
            "{campaign.message_template}"
          </p>
        )}

        {totalRecipients > 0 && (
          <div className="mb-4">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Users className="h-3 w-3" /> {totalRecipients} recipients
              </span>
            </div>
          </div>
        )}
        
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-4">
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {formatDate(campaign.created_at)}
          </span>
        </div>
        
        <div className="flex gap-2 pt-3 border-t" onClick={(e) => e.stopPropagation()}>
          {campaign.status === "DRAFT" && (
            <Button size="sm" className="flex-1" onClick={onClick}>
              <Play className="h-3 w-3 mr-1" />
              Configure & Start
            </Button>
          )}
          {campaign.status === "RUNNING" && (
            <Button size="sm" variant="outline" className="flex-1" onClick={onClick}>
              <BarChart3 className="h-3 w-3 mr-1" />
              View Progress
            </Button>
          )}
          {campaign.status === "COMPLETED" && (
            <Button size="sm" variant="outline" className="flex-1" onClick={onClick}>
              <BarChart3 className="h-3 w-3 mr-1" />
              View Results
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CampaignDetailModal({ campaign, open, onOpenChange, onUpdate, formatDate }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [sending, setSending] = useState(false);
  const [starting, setStarting] = useState(false);

  const fetchStats = useCallback(async () => {
    if (!campaign?.id) return;
    setLoadingStats(true);
    try {
      const response = await campaignAPI.getStats(campaign.id);
      setStats(response.data);
    } catch (error) {
      console.error("Failed to load stats:", error);
    } finally {
      setLoadingStats(false);
    }
  }, [campaign?.id]);

  useEffect(() => {
    if (open && campaign) {
      fetchStats();
    }
  }, [open, campaign, fetchStats]);

  const handleStartCampaign = async () => {
    if (!campaign) return;
    setStarting(true);
    try {
      const response = await campaignAPI.start(campaign.id);
      toast.success(`Campaign started with ${response.data.recipients_created} recipients`);
      fetchStats();
      onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to start campaign");
    } finally {
      setStarting(false);
    }
  };

  const handleSendBatch = async () => {
    if (!campaign) return;
    setSending(true);
    try {
      const response = await campaignAPI.sendBatch(campaign.id, 10);
      if (response.data.status === "completed") {
        toast.success("All messages sent! Campaign completed.");
      } else {
        toast.success(`Sent ${response.data.sent_in_batch} messages. ${response.data.remaining} remaining.`);
      }
      fetchStats();
      onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send batch");
    } finally {
      setSending(false);
    }
  };

  const handlePauseCampaign = async () => {
    try {
      await campaignAPI.update(campaign.id, {
        ...campaign,
        status: "PAUSED"
      });
      toast.success("Campaign paused");
      onUpdate();
    } catch (error) {
      toast.error("Failed to pause campaign");
    }
  };

  if (!campaign) return null;

  const recipientStats = stats?.stats || {
    total: 0,
    pending: 0,
    sent: 0,
    responded: 0,
    opted_out: 0,
    response_rate: 0
  };

  const progress = recipientStats.total > 0 
    ? ((recipientStats.sent + recipientStats.opted_out) / recipientStats.total) * 100 
    : 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
              campaign.type === "REACTIVATION" ? "bg-purple-100" :
              campaign.type === "TUNEUP" ? "bg-cyan-100" : "bg-orange-100"
            }`}>
              <Megaphone className={`h-6 w-6 ${
                campaign.type === "REACTIVATION" ? "text-purple-600" :
                campaign.type === "TUNEUP" ? "text-cyan-600" : "text-orange-600"
              }`} />
            </div>
            <div>
              <DialogTitle className="font-heading text-xl">{campaign.name}</DialogTitle>
              <DialogDescription className="flex items-center gap-2 mt-1">
                <Badge className={typeColors[campaign.type]}>{campaign.type?.replace('_', ' ')}</Badge>
                <Badge className={statusColors[campaign.status]}>{campaign.status}</Badge>
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
          <TabsList className="w-full">
            <TabsTrigger value="overview" className="flex-1">Overview</TabsTrigger>
            <TabsTrigger value="recipients" className="flex-1">Recipients</TabsTrigger>
            <TabsTrigger value="send" className="flex-1">Send Messages</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6 mt-4">
            {/* Message Template */}
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <MessageSquare className="h-4 w-4" /> Message Template
              </h4>
              <div className="bg-muted/50 rounded-lg p-4 text-sm">
                {campaign.message_template || "No message template set"}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Variables: {"{first_name}"}, {"{last_name}"}, {"{company_name}"}
              </p>
            </div>

            {/* Segment Definition */}
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Target className="h-4 w-4" /> Target Segment
              </h4>
              <div className="bg-muted/50 rounded-lg p-4">
                {campaign.segment_definition ? (
                  <div className="text-sm">
                    {campaign.segment_definition.lastServiceDaysAgo && (
                      <p>• Last service: more than {campaign.segment_definition.lastServiceDaysAgo.replace(">", "")} days ago</p>
                    )}
                    {campaign.segment_definition.last_service_days_ago && (
                      <p>• Last service: more than {campaign.segment_definition.last_service_days_ago.replace(">", "")} days ago</p>
                    )}
                    {!campaign.segment_definition.lastServiceDaysAgo && !campaign.segment_definition.last_service_days_ago && (
                      <pre className="text-xs">{JSON.stringify(campaign.segment_definition, null, 2)}</pre>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">All customers with completed jobs</p>
                )}
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
              <Card className="p-3 text-center">
                <p className="text-2xl font-bold">{recipientStats.total}</p>
                <p className="text-xs text-muted-foreground">Recipients</p>
              </Card>
              <Card className="p-3 text-center">
                <p className="text-2xl font-bold text-green-600">{recipientStats.sent}</p>
                <p className="text-xs text-muted-foreground">Sent</p>
              </Card>
              <Card className="p-3 text-center">
                <p className="text-2xl font-bold text-blue-600">{recipientStats.responded}</p>
                <p className="text-xs text-muted-foreground">Responded</p>
              </Card>
              <Card className="p-3 text-center">
                <p className="text-2xl font-bold text-primary">{recipientStats.response_rate}%</p>
                <p className="text-xs text-muted-foreground">Response Rate</p>
              </Card>
            </div>

            {/* Progress */}
            {campaign.status === "RUNNING" && recipientStats.total > 0 && (
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Sending Progress</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <Progress value={progress} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  {recipientStats.pending} messages remaining
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="recipients" className="mt-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-medium">Campaign Recipients</h4>
                <Button variant="outline" size="sm" onClick={fetchStats} disabled={loadingStats}>
                  <RefreshCw className={`h-3 w-3 mr-1 ${loadingStats ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </div>

              {/* Status breakdown */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-gray-50 rounded-lg p-3 flex items-center gap-2">
                  <Clock className="h-4 w-4 text-gray-500" />
                  <div>
                    <p className="font-medium">{recipientStats.pending}</p>
                    <p className="text-xs text-muted-foreground">Pending</p>
                  </div>
                </div>
                <div className="bg-green-50 rounded-lg p-3 flex items-center gap-2">
                  <Send className="h-4 w-4 text-green-500" />
                  <div>
                    <p className="font-medium text-green-700">{recipientStats.sent}</p>
                    <p className="text-xs text-muted-foreground">Sent</p>
                  </div>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-blue-500" />
                  <div>
                    <p className="font-medium text-blue-700">{recipientStats.responded}</p>
                    <p className="text-xs text-muted-foreground">Responded</p>
                  </div>
                </div>
                <div className="bg-red-50 rounded-lg p-3 flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-500" />
                  <div>
                    <p className="font-medium text-red-700">{recipientStats.opted_out}</p>
                    <p className="text-xs text-muted-foreground">Failed/Opted Out</p>
                  </div>
                </div>
              </div>

              {/* Recipient list */}
              {stats?.recipients && stats.recipients.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left p-3">Customer</th>
                        <th className="text-left p-3">Phone</th>
                        <th className="text-left p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recipients.slice(0, 20).map((r) => (
                        <tr key={r.id} className="border-t">
                          <td className="p-3">{r.customer_name || "Unknown"}</td>
                          <td className="p-3 text-muted-foreground">{r.customer_phone}</td>
                          <td className="p-3">
                            <Badge className={
                              r.status === "SENT" ? "bg-green-100 text-green-800" :
                              r.status === "RESPONDED" ? "bg-blue-100 text-blue-800" :
                              r.status === "PENDING" ? "bg-gray-100 text-gray-800" :
                              "bg-red-100 text-red-800"
                            }>
                              {r.status}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {stats.recipients.length > 20 && (
                    <div className="p-3 text-center text-sm text-muted-foreground bg-muted/30">
                      Showing 20 of {stats.recipients.length} recipients
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-muted/30 rounded-lg p-8 text-center">
                  <Users className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    {campaign.status === "DRAFT" 
                      ? "Start the campaign to generate recipients" 
                      : "No recipients found"}
                  </p>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="send" className="mt-4">
            <div className="space-y-6">
              {campaign.status === "DRAFT" && (
                <Card className="p-6 text-center">
                  <Target className="h-12 w-12 mx-auto mb-4 text-purple-500" />
                  <h4 className="font-medium mb-2">Ready to Start Campaign?</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    This will find all customers matching your segment and prepare them for messaging.
                  </p>
                  <Button onClick={handleStartCampaign} disabled={starting}>
                    {starting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        Start Campaign
                      </>
                    )}
                  </Button>
                </Card>
              )}

              {campaign.status === "RUNNING" && (
                <div className="space-y-4">
                  <Card className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h4 className="font-medium">Send Messages</h4>
                        <p className="text-sm text-muted-foreground">
                          {recipientStats.pending} messages waiting to be sent
                        </p>
                      </div>
                      <Badge className="bg-green-100 text-green-800">Campaign Active</Badge>
                    </div>

                    {recipientStats.pending > 0 ? (
                      <div className="space-y-4">
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                          <p className="text-sm text-yellow-800">
                            <strong>Note:</strong> Messages are sent in batches of 10 to avoid rate limits. 
                            Click "Send Next Batch" repeatedly until all messages are sent.
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button onClick={handleSendBatch} disabled={sending} className="flex-1">
                            {sending ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Sending...
                              </>
                            ) : (
                              <>
                                <Send className="h-4 w-4 mr-2" />
                                Send Next Batch (10 messages)
                              </>
                            )}
                          </Button>
                          <Button variant="outline" onClick={handlePauseCampaign}>
                            <Pause className="h-4 w-4 mr-2" />
                            Pause
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                        <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-600" />
                        <p className="text-green-800 font-medium">All messages sent!</p>
                        <p className="text-sm text-green-600">Campaign will be marked as completed.</p>
                      </div>
                    )}
                  </Card>

                  {/* Progress summary */}
                  <div className="grid grid-cols-3 gap-4">
                    <Card className="p-4 text-center">
                      <p className="text-3xl font-bold text-green-600">{recipientStats.sent}</p>
                      <p className="text-sm text-muted-foreground">Messages Sent</p>
                    </Card>
                    <Card className="p-4 text-center">
                      <p className="text-3xl font-bold text-gray-600">{recipientStats.pending}</p>
                      <p className="text-sm text-muted-foreground">Remaining</p>
                    </Card>
                    <Card className="p-4 text-center">
                      <p className="text-3xl font-bold text-red-600">{recipientStats.opted_out}</p>
                      <p className="text-sm text-muted-foreground">Failed</p>
                    </Card>
                  </div>
                </div>
              )}

              {campaign.status === "COMPLETED" && (
                <Card className="p-6 text-center">
                  <CheckCircle className="h-12 w-12 mx-auto mb-4 text-blue-500" />
                  <h4 className="font-medium mb-2">Campaign Completed</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    Sent {recipientStats.sent} messages to customers.
                  </p>
                  <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
                    <Card className="p-3">
                      <p className="text-2xl font-bold text-blue-600">{recipientStats.responded}</p>
                      <p className="text-xs text-muted-foreground">Responses</p>
                    </Card>
                    <Card className="p-3">
                      <p className="text-2xl font-bold text-primary">{recipientStats.response_rate}%</p>
                      <p className="text-xs text-muted-foreground">Response Rate</p>
                    </Card>
                  </div>
                </Card>
              )}

              {campaign.status === "PAUSED" && (
                <Card className="p-6 text-center">
                  <Pause className="h-12 w-12 mx-auto mb-4 text-yellow-500" />
                  <h4 className="font-medium mb-2">Campaign Paused</h4>
                  <p className="text-sm text-muted-foreground mb-4">
                    {recipientStats.pending} messages still pending.
                  </p>
                  <Button onClick={handleStartCampaign}>
                    <Play className="h-4 w-4 mr-2" />
                    Resume Campaign
                  </Button>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CreateCampaignDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    name: "",
    type: "REACTIVATION",
    message_template: "",
    segment_definition: null,
    status: "DRAFT",
  });
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);
  const [segmentDays, setSegmentDays] = useState("180");

  const templates = {
    REACTIVATION: "Hi {first_name}, it's been a while since we serviced your HVAC system. Schedule a tune-up today and get 10% off! Reply YES to book or call us.",
    TUNEUP: "Hi {first_name}, it's that time of year! Get your system ready for the season with our $79 tune-up special. Reply YES to schedule!",
    SPECIAL_OFFER: "Hi {first_name}, exclusive offer for our valued customers! Get $50 off any repair this month. Reply YES or call us to claim.",
  };

  const handleTypeChange = (type) => {
    setFormData({
      ...formData,
      type,
      message_template: templates[type],
    });
  };

  useEffect(() => {
    // Update segment definition when days change
    setFormData(prev => ({
      ...prev,
      segment_definition: { last_service_days_ago: `>${segmentDays}` }
    }));
  }, [segmentDays]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await campaignAPI.create(formData);
      toast.success("Campaign created successfully");
      onOpenChange(false);
      setFormData({ name: "", type: "REACTIVATION", message_template: "", segment_definition: null, status: "DRAFT" });
      setStep(1);
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create campaign");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) setStep(1); }}>
      <DialogTrigger asChild>
        <Button className="btn-industrial">
          <Plus className="h-4 w-4 mr-2" />
          NEW CAMPAIGN
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-heading">Create Campaign</DialogTitle>
          <DialogDescription>
            Step {step} of 2: {step === 1 ? "Basic Info" : "Message & Targeting"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          {step === 1 ? (
            <div className="grid gap-6 py-4">
              <div className="space-y-2">
                <Label>Campaign Name *</Label>
                <Input
                  placeholder="e.g., Winter Reactivation 2025"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label>Campaign Type</Label>
                <div className="grid grid-cols-3 gap-3">
                  {["REACTIVATION", "TUNEUP", "SPECIAL_OFFER"].map((type) => (
                    <Card 
                      key={type}
                      className={`p-4 cursor-pointer transition-all ${
                        formData.type === type 
                          ? "ring-2 ring-primary bg-primary/5" 
                          : "hover:bg-muted/50"
                      }`}
                      onClick={() => handleTypeChange(type)}
                    >
                      <div className="text-center">
                        {type === "REACTIVATION" && <Target className="h-8 w-8 mx-auto mb-2 text-purple-600" />}
                        {type === "TUNEUP" && <Settings className="h-8 w-8 mx-auto mb-2 text-cyan-600" />}
                        {type === "SPECIAL_OFFER" && <TrendingUp className="h-8 w-8 mx-auto mb-2 text-orange-600" />}
                        <p className="font-medium text-sm">{type.replace('_', ' ')}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {type === "REACTIVATION" && "Win back inactive customers"}
                          {type === "TUNEUP" && "Seasonal maintenance offers"}
                          {type === "SPECIAL_OFFER" && "Limited time promotions"}
                        </p>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              <div className="flex justify-end">
                <Button type="button" onClick={() => setStep(2)} disabled={!formData.name}>
                  Next: Message & Targeting
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-6 py-4">
              <div className="space-y-2">
                <Label>Message Template</Label>
                <Textarea
                  placeholder="Your campaign message..."
                  value={formData.message_template}
                  onChange={(e) => setFormData({...formData, message_template: e.target.value})}
                  rows={4}
                />
                <p className="text-xs text-muted-foreground">
                  Variables: {"{first_name}"}, {"{last_name}"}, {"{company_name}"}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Target Customers</Label>
                <div className="bg-muted/50 rounded-lg p-4">
                  <div className="flex items-center gap-4">
                    <span className="text-sm">Customers with no service in the last</span>
                    <Select value={segmentDays} onValueChange={setSegmentDays}>
                      <SelectTrigger className="w-32">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="90">90 days</SelectItem>
                        <SelectItem value="180">180 days</SelectItem>
                        <SelectItem value="365">1 year</SelectItem>
                        <SelectItem value="730">2 years</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="flex justify-between">
                <Button type="button" variant="outline" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button type="submit" disabled={loading}>
                  {loading ? "Creating..." : "Create Campaign"}
                </Button>
              </div>
            </div>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
}
