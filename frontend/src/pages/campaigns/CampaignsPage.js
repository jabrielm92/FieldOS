import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
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
import { campaignAPI } from "../../lib/api";
import { toast } from "sonner";
import { Plus, Megaphone, Play, Pause, Check, Clock } from "lucide-react";

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

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  useEffect(() => {
    fetchCampaigns();
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

  const handleStatusChange = async (campaign, newStatus) => {
    try {
      await campaignAPI.update(campaign.id, {
        ...campaign,
        status: newStatus,
      });
      toast.success(`Campaign ${newStatus.toLowerCase()}`);
      fetchCampaigns();
    } catch (error) {
      toast.error("Failed to update campaign");
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <Layout title="Campaigns" subtitle="Manage reactivation and marketing campaigns">
      {/* Header */}
      <div className="flex justify-end mb-6">
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
      ) : campaigns.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Megaphone className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-muted-foreground mb-4">No campaigns yet</p>
            <Button onClick={() => setShowCreateDialog(true)} data-testid="create-first-campaign">
              Create your first campaign
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {campaigns.map((campaign) => (
            <CampaignCard 
              key={campaign.id} 
              campaign={campaign} 
              formatDate={formatDate}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}
    </Layout>
  );
}

function CampaignCard({ campaign, formatDate, onStatusChange }) {
  return (
    <Card className="card-industrial" data-testid={`campaign-card-${campaign.id}`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-accent/10 rounded-md flex items-center justify-center">
              <Megaphone className="h-5 w-5 text-accent" />
            </div>
            <div>
              <h3 className="font-medium">{campaign.name}</h3>
              <Badge className={typeColors[campaign.type]} variant="outline">
                {campaign.type?.replace('_', ' ')}
              </Badge>
            </div>
          </div>
        </div>
        
        {campaign.message_template && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-4 bg-muted p-2 rounded">
            "{campaign.message_template}"
          </p>
        )}
        
        <div className="flex items-center justify-between">
          <Badge className={statusColors[campaign.status]}>
            {campaign.status}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {formatDate(campaign.created_at)}
          </span>
        </div>
        
        <div className="flex gap-2 mt-4 pt-4 border-t">
          {campaign.status === "DRAFT" && (
            <Button 
              size="sm" 
              className="flex-1"
              onClick={() => onStatusChange(campaign, "RUNNING")}
            >
              <Play className="h-3 w-3 mr-1" />
              Start
            </Button>
          )}
          {campaign.status === "RUNNING" && (
            <Button 
              size="sm" 
              variant="outline"
              className="flex-1"
              onClick={() => onStatusChange(campaign, "PAUSED")}
            >
              <Pause className="h-3 w-3 mr-1" />
              Pause
            </Button>
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
        </div>
      </CardContent>
    </Card>
  );
}

function CreateCampaignDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    name: "",
    type: "REACTIVATION",
    message_template: "",
    status: "DRAFT",
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await campaignAPI.create(formData);
      toast.success("Campaign created successfully");
      onOpenChange(false);
      setFormData({
        name: "",
        type: "REACTIVATION",
        message_template: "",
        status: "DRAFT",
      });
      onSuccess();
    } catch (error) {
      toast.error("Failed to create campaign");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="btn-industrial" data-testid="create-campaign-button">
          <Plus className="h-4 w-4 mr-2" />
          NEW CAMPAIGN
        </Button>
      </DialogTrigger>
      <DialogContent data-testid="create-campaign-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Create Campaign</DialogTitle>
          <DialogDescription>
            Set up a new marketing or reactivation campaign
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Campaign Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Summer Tune-Up Special"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
                data-testid="campaign-name"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Campaign Type</Label>
              <Select 
                value={formData.type} 
                onValueChange={(v) => setFormData({...formData, type: v})}
              >
                <SelectTrigger data-testid="campaign-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="REACTIVATION">Reactivation</SelectItem>
                  <SelectItem value="TUNEUP">Tune-Up</SelectItem>
                  <SelectItem value="SPECIAL_OFFER">Special Offer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="message_template">Message Template</Label>
              <Textarea
                id="message_template"
                placeholder="Hi {first_name}, it's been a while since your last service..."
                value={formData.message_template}
                onChange={(e) => setFormData({...formData, message_template: e.target.value})}
                rows={4}
                data-testid="campaign-message"
              />
              <p className="text-xs text-muted-foreground">
                Use {"{first_name}"} for personalization
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading} data-testid="submit-campaign">
              {loading ? "Creating..." : "Create Campaign"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
