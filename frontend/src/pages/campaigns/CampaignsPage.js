import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
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
import { campaignAPI, customerAPI } from "../../lib/api";
import { toast } from "sonner";
import { 
  Plus, Megaphone, Play, Pause, Check, Clock, Users, 
  MessageSquare, Target, BarChart3, Send, Calendar,
  AlertCircle, CheckCircle, XCircle, Loader2, Settings,
  TrendingUp, Eye, Edit, Copy, Trash2
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

  useEffect(() => {
    fetchCampaigns();
    const interval = setInterval(fetchCampaigns, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchCampaigns = async () => {
    try {
      const response = await campaignAPI.list();
      setCampaigns(response.data);
    } catch (error) {
      toast.error("Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  };

  const handleCampaignClick = (campaign) => {
    setSelectedCampaign(campaign);
    setShowDetailModal(true);
  };

  const handleStatusChange = async (campaign, newStatus) => {
    try {
      // Only send fields that are in CampaignCreate model
      const payload = {
        name: campaign.name,
        type: campaign.type,
        status: newStatus,
        message_template: campaign.message_template || null,
        segment_definition: campaign.segment_definition || null,
      };
      await campaignAPI.update(campaign.id, payload);
      toast.success(`Campaign ${newStatus === "RUNNING" ? "started" : newStatus.toLowerCase()}`);
      fetchCampaigns();
    } catch (error) {
      console.error("Campaign update error:", error);
      toast.error(error.response?.data?.detail || "Failed to update campaign");
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

  // Stats
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
              onStatusChange={handleStatusChange}
              onClick={() => handleCampaignClick(campaign)}
            />
          ))}
        </div>
      )}

      {/* Campaign Detail Modal */}
      <CampaignDetailModal
        campaign={selectedCampaign}
        open={showDetailModal}
        onOpenChange={setShowDetailModal}
        onStatusChange={handleStatusChange}
        onUpdate={fetchCampaigns}
        formatDate={formatDate}
      />
    </Layout>
  );
}

function CampaignCard({ campaign, formatDate, onStatusChange, onClick }) {
  const TypeIcon = typeIcons[campaign.type] || Megaphone;
  
  // Mock recipient data (would come from backend in real app)
  const recipientStats = {
    total: Math.floor(Math.random() * 100) + 20,
    sent: Math.floor(Math.random() * 80),
    responded: Math.floor(Math.random() * 20),
  };
  const progress = campaign.status === "RUNNING" || campaign.status === "COMPLETED" 
    ? Math.min(100, (recipientStats.sent / recipientStats.total) * 100) 
    : 0;

  return (
    <Card 
      className="card-industrial cursor-pointer hover:shadow-md transition-shadow overflow-hidden"
      onClick={onClick}
    >
      {/* Status indicator bar */}
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
          <Badge className={statusColors[campaign.status]}>
            {campaign.status}
          </Badge>
        </div>
        
        {campaign.message_template && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-4 bg-muted/50 p-2 rounded italic">
            "{campaign.message_template}"
          </p>
        )}

        {/* Progress for running campaigns */}
        {(campaign.status === "RUNNING" || campaign.status === "COMPLETED") && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Users className="h-3 w-3" /> {recipientStats.total} recipients
              </span>
              <span className="flex items-center gap-1">
                <Send className="h-3 w-3" /> {recipientStats.sent} sent
              </span>
              <span className="flex items-center gap-1">
                <MessageSquare className="h-3 w-3" /> {recipientStats.responded} responded
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
            <Button 
              size="sm" 
              className="flex-1"
              onClick={() => onStatusChange(campaign, "RUNNING")}
            >
              <Play className="h-3 w-3 mr-1" />
              Start Campaign
            </Button>
          )}
          {campaign.status === "RUNNING" && (
            <>
              <Button 
                size="sm" 
                variant="outline"
                className="flex-1"
                onClick={() => onStatusChange(campaign, "PAUSED")}
              >
                <Pause className="h-3 w-3 mr-1" />
                Pause
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => onStatusChange(campaign, "COMPLETED")}
              >
                <Check className="h-3 w-3" />
              </Button>
            </>
          )}
          {campaign.status === "PAUSED" && (
            <>
              <Button 
                size="sm" 
                className="flex-1"
                onClick={() => onStatusChange(campaign, "RUNNING")}
              >
                <Play className="h-3 w-3 mr-1" />
                Resume
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => onStatusChange(campaign, "COMPLETED")}
              >
                <Check className="h-3 w-3" />
              </Button>
            </>
          )}
          {campaign.status === "COMPLETED" && (
            <Button size="sm" variant="outline" className="flex-1">
              <BarChart3 className="h-3 w-3 mr-1" />
              View Results
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function CampaignDetailModal({ campaign, open, onOpenChange, onStatusChange, onUpdate, formatDate }) {
  const [activeTab, setActiveTab] = useState("overview");

  if (!campaign) return null;

  // Mock data for demonstration
  const recipientStats = {
    total: 85,
    pending: 12,
    sent: 60,
    responded: 18,
    optedOut: 3,
  };

  const responseRate = ((recipientStats.responded / recipientStats.sent) * 100).toFixed(1);

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
            <TabsTrigger value="analytics" className="flex-1">Analytics</TabsTrigger>
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
                Use {"{first_name}"}, {"{company_name}"} for personalization
              </p>
            </div>

            {/* Segment Definition */}
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Target className="h-4 w-4" /> Target Segment
              </h4>
              <div className="bg-muted/50 rounded-lg p-4">
                {campaign.segment_definition ? (
                  <pre className="text-xs">{JSON.stringify(JSON.parse(campaign.segment_definition), null, 2)}</pre>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {campaign.type === "REACTIVATION" 
                      ? "Customers with no service in last 6+ months"
                      : campaign.type === "TUNEUP"
                      ? "Customers due for seasonal maintenance"
                      : "All active customers"}
                  </p>
                )}
              </div>
            </div>

            {/* Quick Stats */}
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
                <p className="text-2xl font-bold text-primary">{responseRate}%</p>
                <p className="text-xs text-muted-foreground">Response Rate</p>
              </Card>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              {campaign.status === "DRAFT" && (
                <Button onClick={() => onStatusChange(campaign, "RUNNING")} className="flex-1">
                  <Play className="h-4 w-4 mr-2" />
                  Start Campaign
                </Button>
              )}
              {campaign.status === "RUNNING" && (
                <>
                  <Button variant="outline" onClick={() => onStatusChange(campaign, "PAUSED")} className="flex-1">
                    <Pause className="h-4 w-4 mr-2" />
                    Pause
                  </Button>
                  <Button variant="outline" onClick={() => onStatusChange(campaign, "COMPLETED")}>
                    <Check className="h-4 w-4 mr-2" />
                    Complete
                  </Button>
                </>
              )}
              {campaign.status === "PAUSED" && (
                <Button onClick={() => onStatusChange(campaign, "RUNNING")} className="flex-1">
                  <Play className="h-4 w-4 mr-2" />
                  Resume
                </Button>
              )}
            </div>
          </TabsContent>

          <TabsContent value="recipients" className="mt-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-medium">Campaign Recipients</h4>
                <Badge variant="outline">{recipientStats.total} total</Badge>
              </div>

              {/* Recipient status breakdown */}
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
                    <p className="font-medium text-red-700">{recipientStats.optedOut}</p>
                    <p className="text-xs text-muted-foreground">Opted Out</p>
                  </div>
                </div>
              </div>

              {/* Sample recipient list */}
              <div className="bg-muted/30 rounded-lg p-4">
                <p className="text-sm text-muted-foreground text-center">
                  Recipient list will populate when campaign is active
                </p>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics" className="mt-4">
            <div className="space-y-6">
              {/* Performance metrics */}
              <div>
                <h4 className="font-medium mb-3">Performance Metrics</h4>
                <div className="grid grid-cols-3 gap-4">
                  <Card className="p-4 text-center">
                    <p className="text-3xl font-bold text-green-600">{responseRate}%</p>
                    <p className="text-sm text-muted-foreground">Response Rate</p>
                  </Card>
                  <Card className="p-4 text-center">
                    <p className="text-3xl font-bold text-blue-600">$2,450</p>
                    <p className="text-sm text-muted-foreground">Revenue Generated</p>
                  </Card>
                  <Card className="p-4 text-center">
                    <p className="text-3xl font-bold text-purple-600">5</p>
                    <p className="text-sm text-muted-foreground">Jobs Booked</p>
                  </Card>
                </div>
              </div>

              {/* Timeline */}
              <div>
                <h4 className="font-medium mb-3">Campaign Timeline</h4>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-green-500 rounded-full" />
                    <span className="text-sm">Created on {formatDate(campaign.created_at)}</span>
                  </div>
                  {campaign.status !== "DRAFT" && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-blue-500 rounded-full" />
                      <span className="text-sm">Started sending messages</span>
                    </div>
                  )}
                  {campaign.status === "COMPLETED" && (
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-purple-500 rounded-full" />
                      <span className="text-sm">Campaign completed</span>
                    </div>
                  )}
                </div>
              </div>
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

  const templates = {
    REACTIVATION: "Hi {first_name}, it's been a while since we serviced your HVAC system. Schedule a tune-up today and get 10% off! Reply YES to book or call us at [phone].",
    TUNEUP: "Hi {first_name}, it's that time of year! Get your system ready for the season with our $79 tune-up special. Reply YES to schedule!",
    SPECIAL_OFFER: "Hi {first_name}, exclusive offer for our valued customers! Get $50 off any repair this month. Reply YES or call [phone] to claim.",
  };

  const segmentPresets = {
    REACTIVATION: { lastServiceDaysAgo: ">180", hasActiveService: false },
    TUNEUP: { lastMaintenanceDaysAgo: ">300", propertyType: "RESIDENTIAL" },
    SPECIAL_OFFER: { totalJobsCompleted: ">0", status: "active" },
  };

  const handleTypeChange = (type) => {
    setFormData({
      ...formData,
      type,
      message_template: templates[type],
      segment_definition: segmentPresets[type],
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Ensure segment_definition is sent as an object, not a string
      const payload = {
        ...formData,
        segment_definition: typeof formData.segment_definition === 'string' 
          ? (formData.segment_definition ? JSON.parse(formData.segment_definition) : null)
          : formData.segment_definition || null,
      };
      await campaignAPI.create(payload);
      toast.success("Campaign created successfully");
      onOpenChange(false);
      setFormData({ name: "", type: "REACTIVATION", message_template: "", segment_definition: null, status: "DRAFT" });
      setStep(1);
      onSuccess();
    } catch (error) {
      console.error("Campaign creation error:", error);
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
                  placeholder="e.g., Summer Reactivation 2025"
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
                  Variables: {"{first_name}"}, {"{last_service_date}"}, {"{property_address}"}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Target Segment</Label>
                <div className="bg-muted/50 rounded-lg p-4 text-sm">
                  <p className="font-medium mb-2">
                    {formData.type === "REACTIVATION" && "Customers with no service in last 6 months"}
                    {formData.type === "TUNEUP" && "Customers due for seasonal maintenance"}
                    {formData.type === "SPECIAL_OFFER" && "All active customers"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Estimated reach: ~45 customers
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex justify-between">
                <Button type="button" variant="outline" onClick={() => setStep(1)}>
                  Back
                </Button>
                <div className="flex gap-2">
                  <Button type="submit" variant="outline" disabled={loading}>
                    Save as Draft
                  </Button>
                  <Button type="submit" disabled={loading}>
                    {loading ? "Creating..." : "Create & Start"}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
}
