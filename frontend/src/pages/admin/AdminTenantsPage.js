import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { adminAPI } from "../../lib/api";
import { toast } from "sonner";
import { Plus, Building2, Users, Briefcase, TrendingUp } from "lucide-react";

export default function AdminTenantsPage() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  useEffect(() => {
    fetchTenants();
  }, []);

  const fetchTenants = async () => {
    try {
      const response = await adminAPI.getTenants();
      setTenants(response.data);
    } catch (error) {
      toast.error("Failed to load tenants");
    } finally {
      setLoading(false);
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
    <Layout title="Tenants" subtitle="Manage field service companies">
      {/* Header */}
      <div className="flex justify-end mb-6">
        <CreateTenantDialog 
          open={showCreateDialog} 
          onOpenChange={setShowCreateDialog}
          onSuccess={fetchTenants}
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary/10 rounded-md">
                <Building2 className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Tenants</p>
                <p className="text-2xl font-bold font-heading">{tenants.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-accent/10 rounded-md">
                <TrendingUp className="h-6 w-6 text-accent" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Leads (30d)</p>
                <p className="text-2xl font-bold font-heading">
                  {tenants.reduce((sum, t) => sum + (t.leads_last_30d || 0), 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-500/10 rounded-md">
                <Briefcase className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Jobs (30d)</p>
                <p className="text-2xl font-bold font-heading">
                  {tenants.reduce((sum, t) => sum + (t.jobs_last_30d || 0), 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tenants Table */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : tenants.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Building2 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-muted-foreground mb-4">No tenants yet</p>
            <Button onClick={() => setShowCreateDialog(true)} data-testid="create-first-tenant">
              Add your first tenant
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table data-testid="tenants-table">
            <TableHeader>
              <TableRow className="table-industrial">
                <TableHead>Company</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Leads (30d)</TableHead>
                <TableHead>Jobs (30d)</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tenants.map((tenant) => (
                <TableRow key={tenant.id} className="table-industrial" data-testid={`tenant-row-${tenant.id}`}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary/10 rounded-md flex items-center justify-center">
                        <Building2 className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{tenant.name}</p>
                        <p className="text-xs text-muted-foreground font-mono">{tenant.slug}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <p className="text-sm">{tenant.primary_contact_name}</p>
                    <p className="text-xs text-muted-foreground">{tenant.primary_contact_email}</p>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono font-semibold">{tenant.leads_last_30d || 0}</span>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono font-semibold">{tenant.jobs_last_30d || 0}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {formatDate(tenant.created_at)}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </Layout>
  );
}

function CreateTenantDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    timezone: "America/New_York",
    primary_contact_name: "",
    primary_contact_email: "",
    primary_phone: "",
    booking_mode: "TIME_WINDOWS",
    tone_profile: "PROFESSIONAL",
    twilio_phone_number: "",
    owner_name: "",
    owner_email: "",
    owner_password: "",
  });
  const [loading, setLoading] = useState(false);

  const generateSlug = (name) => {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await adminAPI.createTenant(formData);
      toast.success("Tenant created successfully");
      onOpenChange(false);
      setFormData({
        name: "",
        slug: "",
        timezone: "America/New_York",
        primary_contact_name: "",
        primary_contact_email: "",
        primary_phone: "",
        booking_mode: "TIME_WINDOWS",
        tone_profile: "PROFESSIONAL",
        twilio_phone_number: "",
        owner_name: "",
        owner_email: "",
        owner_password: "",
      });
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create tenant");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="btn-industrial" data-testid="create-tenant-button">
          <Plus className="h-4 w-4 mr-2" />
          NEW TENANT
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="create-tenant-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Add New Tenant</DialogTitle>
          <DialogDescription>
            Create a new field service company account
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
              Company Information
            </h4>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Company Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({
                    ...formData, 
                    name: e.target.value,
                    slug: generateSlug(e.target.value)
                  })}
                  required
                  data-testid="tenant-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="slug">Slug *</Label>
                <Input
                  id="slug"
                  value={formData.slug}
                  onChange={(e) => setFormData({...formData, slug: e.target.value})}
                  required
                  data-testid="tenant-slug"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Timezone</Label>
                <Select 
                  value={formData.timezone} 
                  onValueChange={(v) => setFormData({...formData, timezone: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="America/New_York">Eastern</SelectItem>
                    <SelectItem value="America/Chicago">Central</SelectItem>
                    <SelectItem value="America/Denver">Mountain</SelectItem>
                    <SelectItem value="America/Los_Angeles">Pacific</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Tone Profile</Label>
                <Select 
                  value={formData.tone_profile} 
                  onValueChange={(v) => setFormData({...formData, tone_profile: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PROFESSIONAL">Professional</SelectItem>
                    <SelectItem value="FRIENDLY">Friendly</SelectItem>
                    <SelectItem value="BLUE_COLLAR_DIRECT">Blue Collar Direct</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide mt-4">
              Primary Contact
            </h4>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="primary_contact_name">Contact Name *</Label>
                <Input
                  id="primary_contact_name"
                  value={formData.primary_contact_name}
                  onChange={(e) => setFormData({...formData, primary_contact_name: e.target.value})}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="primary_phone">Phone *</Label>
                <Input
                  id="primary_phone"
                  type="tel"
                  value={formData.primary_phone}
                  onChange={(e) => setFormData({...formData, primary_phone: e.target.value})}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="primary_contact_email">Contact Email *</Label>
              <Input
                id="primary_contact_email"
                type="email"
                value={formData.primary_contact_email}
                onChange={(e) => setFormData({...formData, primary_contact_email: e.target.value})}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="twilio_phone_number">Twilio Phone Number</Label>
              <Input
                id="twilio_phone_number"
                placeholder="+1..."
                value={formData.twilio_phone_number}
                onChange={(e) => setFormData({...formData, twilio_phone_number: e.target.value})}
              />
            </div>

            <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide mt-4">
              Owner Account
            </h4>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="owner_name">Owner Name *</Label>
                <Input
                  id="owner_name"
                  value={formData.owner_name}
                  onChange={(e) => setFormData({...formData, owner_name: e.target.value})}
                  required
                  data-testid="owner-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="owner_email">Owner Email *</Label>
                <Input
                  id="owner_email"
                  type="email"
                  value={formData.owner_email}
                  onChange={(e) => setFormData({...formData, owner_email: e.target.value})}
                  required
                  data-testid="owner-email"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="owner_password">Owner Password *</Label>
              <Input
                id="owner_password"
                type="password"
                value={formData.owner_password}
                onChange={(e) => setFormData({...formData, owner_password: e.target.value})}
                required
                data-testid="owner-password"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading} data-testid="submit-tenant">
              {loading ? "Creating..." : "Create Tenant"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
