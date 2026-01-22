import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Textarea } from "../../components/ui/textarea";
import { Switch } from "../../components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "../../components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "../../components/ui/alert-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { adminAPI } from "../../lib/api";
import { toast } from "sonner";
import { Plus, Building2, TrendingUp, Briefcase, Pencil, Trash2, Users, MessageSquare, HardDrive, Phone, Mic, Settings, Check, AlertCircle } from "lucide-react";

export default function AdminTenantsPage() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingTenant, setEditingTenant] = useState(null);
  const [deletingTenant, setDeletingTenant] = useState(null);
  const [viewingStorage, setViewingStorage] = useState(null);
  const [configuringVoice, setConfiguringVoice] = useState(null);
  const [storageData, setStorageData] = useState(null);
  const [storageLoading, setStorageLoading] = useState(false);

  useEffect(() => { fetchTenants(); }, []);

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

  const handleDelete = async () => {
    if (!deletingTenant) return;
    try {
      await adminAPI.deleteTenant(deletingTenant.id);
      toast.success(`Tenant "${deletingTenant.name}" deleted`);
      setDeletingTenant(null);
      fetchTenants();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete tenant");
    }
  };

  const handleViewStorage = async (tenant) => {
    setViewingStorage(tenant);
    setStorageLoading(true);
    try {
      const response = await adminAPI.getTenantStorage(tenant.id);
      setStorageData(response.data);
    } catch (error) {
      toast.error("Failed to load storage data");
    } finally {
      setStorageLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  };

  return (
    <Layout title="Tenants" subtitle="Manage field service companies">
      <div className="flex justify-end mb-6">
        <CreateTenantDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} onSuccess={fetchTenants} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card><CardContent className="p-6"><div className="flex items-center gap-4"><div className="p-3 bg-primary/10 rounded-md"><Building2 className="h-6 w-6 text-primary" /></div><div><p className="text-sm text-muted-foreground">Total Tenants</p><p className="text-2xl font-bold">{tenants.length}</p></div></div></CardContent></Card>
        <Card><CardContent className="p-6"><div className="flex items-center gap-4"><div className="p-3 bg-accent/10 rounded-md"><TrendingUp className="h-6 w-6 text-accent" /></div><div><p className="text-sm text-muted-foreground">Total Leads (30d)</p><p className="text-2xl font-bold">{tenants.reduce((sum, t) => sum + (t.leads_last_30d || 0), 0)}</p></div></div></CardContent></Card>
        <Card><CardContent className="p-6"><div className="flex items-center gap-4"><div className="p-3 bg-green-500/10 rounded-md"><Briefcase className="h-6 w-6 text-green-600" /></div><div><p className="text-sm text-muted-foreground">Total Jobs (30d)</p><p className="text-2xl font-bold">{tenants.reduce((sum, t) => sum + (t.jobs_last_30d || 0), 0)}</p></div></div></CardContent></Card>
      </div>

      {/* Tenants Table */}
      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
      ) : tenants.length === 0 ? (
        <Card><CardContent className="py-12 text-center"><Building2 className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" /><p className="text-muted-foreground mb-4">No tenants yet</p><Button onClick={() => setShowCreateDialog(true)}>Add your first tenant</Button></CardContent></Card>
      ) : (
        <Card>
          <Table data-testid="tenants-table">
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Voice AI</TableHead>
                <TableHead>Activity (30d)</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tenants.map((tenant) => (
                <TableRow key={tenant.id} data-testid={`tenant-row-${tenant.id}`}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary/10 rounded-md flex items-center justify-center"><Building2 className="h-5 w-5 text-primary" /></div>
                      <div><p className="font-medium">{tenant.name}</p><p className="text-xs text-muted-foreground font-mono">{tenant.slug}</p></div>
                    </div>
                  </TableCell>
                  <TableCell><p className="text-sm">{tenant.primary_contact_name}</p><p className="text-xs text-muted-foreground">{tenant.primary_contact_email}</p></TableCell>
                  <TableCell>
                    {tenant.voice_ai_enabled ? (
                      <Badge className="bg-green-100 text-green-800"><Check className="h-3 w-3 mr-1" />Active</Badge>
                    ) : (
                      <Badge variant="secondary"><AlertCircle className="h-3 w-3 mr-1" />Not Configured</Badge>
                    )}
                  </TableCell>
                  <TableCell><span className="font-mono text-sm">{tenant.leads_last_30d || 0} leads / {tenant.jobs_last_30d || 0} jobs</span></TableCell>
                  <TableCell><span className="text-sm text-muted-foreground">{formatDate(tenant.created_at)}</span></TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => setConfiguringVoice(tenant)} title="Configure Voice AI" data-testid={`voice-config-${tenant.id}`}><Mic className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => handleViewStorage(tenant)} title="View Storage"><HardDrive className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => setEditingTenant(tenant)} title="Edit"><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={() => setDeletingTenant(tenant)} title="Delete"><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Edit Dialog */}
      {editingTenant && <EditTenantDialog tenant={editingTenant} open={!!editingTenant} onOpenChange={(open) => !open && setEditingTenant(null)} onSuccess={() => { setEditingTenant(null); fetchTenants(); }} />}

      {/* Voice AI Config Dialog */}
      {configuringVoice && <VoiceAIConfigDialog tenant={configuringVoice} open={!!configuringVoice} onOpenChange={(open) => !open && setConfiguringVoice(null)} onSuccess={() => { setConfiguringVoice(null); fetchTenants(); }} />}

      {/* Delete Confirmation */}
      <AlertDialog open={!!deletingTenant} onOpenChange={(open) => !open && setDeletingTenant(null)}>
        <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Delete Tenant</AlertDialogTitle><AlertDialogDescription>Are you sure you want to delete <strong>{deletingTenant?.name}</strong>?<br /><br /><span className="text-destructive font-medium">This will permanently delete ALL data.</span></AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Delete Tenant</AlertDialogAction></AlertDialogFooter></AlertDialogContent>
      </AlertDialog>

      {/* Storage Dialog */}
      <Dialog open={!!viewingStorage} onOpenChange={(open) => !open && setViewingStorage(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><HardDrive className="h-5 w-5" />Storage: {viewingStorage?.name}</DialogTitle></DialogHeader>
          {storageLoading ? (<div className="flex items-center justify-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>) : storageData ? (
            <div className="space-y-4">
              <div className="bg-muted/50 rounded-lg p-4"><p className="text-sm text-muted-foreground">Total Documents</p><p className="text-3xl font-bold">{storageData.total_documents.toLocaleString()}</p></div>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(storageData.collections).map(([name, count]) => (
                  <div key={name} className="flex items-center justify-between p-3 bg-background border rounded-md"><span className="text-sm capitalize">{name.replace(/_/g, ' ')}</span><Badge variant="secondary" className="font-mono">{count}</Badge></div>
                ))}
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </Layout>
  );
}

function CreateTenantDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({ name: "", slug: "", timezone: "America/New_York", primary_contact_name: "", primary_contact_email: "", primary_phone: "", booking_mode: "TIME_WINDOWS", tone_profile: "PROFESSIONAL", twilio_phone_number: "", owner_name: "", owner_email: "", owner_password: "" });
  const [loading, setLoading] = useState(false);

  const generateSlug = (name) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await adminAPI.createTenant(formData);
      toast.success("Tenant created successfully");
      onOpenChange(false);
      setFormData({ name: "", slug: "", timezone: "America/New_York", primary_contact_name: "", primary_contact_email: "", primary_phone: "", booking_mode: "TIME_WINDOWS", tone_profile: "PROFESSIONAL", twilio_phone_number: "", owner_name: "", owner_email: "", owner_password: "" });
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create tenant");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild><Button className="btn-industrial" data-testid="create-tenant-button"><Plus className="h-4 w-4 mr-2" />NEW TENANT</Button></DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Add New Tenant</DialogTitle><DialogDescription>Create a new field service company account</DialogDescription></DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <h4 className="font-medium text-sm text-muted-foreground uppercase">Company Information</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Company Name *</Label><Input value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value, slug: generateSlug(e.target.value)})} required /></div>
              <div className="space-y-2"><Label>Slug *</Label><Input value={formData.slug} onChange={(e) => setFormData({...formData, slug: e.target.value})} required /></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Timezone</Label><Select value={formData.timezone} onValueChange={(v) => setFormData({...formData, timezone: v})}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="America/New_York">Eastern</SelectItem><SelectItem value="America/Chicago">Central</SelectItem><SelectItem value="America/Denver">Mountain</SelectItem><SelectItem value="America/Los_Angeles">Pacific</SelectItem></SelectContent></Select></div>
              <div className="space-y-2"><Label>Tone Profile</Label><Select value={formData.tone_profile} onValueChange={(v) => setFormData({...formData, tone_profile: v})}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="PROFESSIONAL">Professional</SelectItem><SelectItem value="FRIENDLY">Friendly</SelectItem><SelectItem value="BLUE_COLLAR_DIRECT">Blue Collar Direct</SelectItem></SelectContent></Select></div>
            </div>
            <h4 className="font-medium text-sm text-muted-foreground uppercase mt-4">Primary Contact</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Contact Name *</Label><Input value={formData.primary_contact_name} onChange={(e) => setFormData({...formData, primary_contact_name: e.target.value})} required /></div>
              <div className="space-y-2"><Label>Phone *</Label><Input value={formData.primary_phone} onChange={(e) => setFormData({...formData, primary_phone: e.target.value})} required /></div>
            </div>
            <div className="space-y-2"><Label>Contact Email *</Label><Input type="email" value={formData.primary_contact_email} onChange={(e) => setFormData({...formData, primary_contact_email: e.target.value})} required /></div>
            <h4 className="font-medium text-sm text-muted-foreground uppercase mt-4">Owner Account</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Owner Name *</Label><Input value={formData.owner_name} onChange={(e) => setFormData({...formData, owner_name: e.target.value})} required /></div>
              <div className="space-y-2"><Label>Owner Email *</Label><Input type="email" value={formData.owner_email} onChange={(e) => setFormData({...formData, owner_email: e.target.value})} required /></div>
            </div>
            <div className="space-y-2"><Label>Owner Password *</Label><Input type="password" value={formData.owner_password} onChange={(e) => setFormData({...formData, owner_password: e.target.value})} required /></div>
          </div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" disabled={loading}>{loading ? "Creating..." : "Create Tenant"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditTenantDialog({ tenant, open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({ name: tenant?.name || "", timezone: tenant?.timezone || "America/New_York", primary_contact_name: tenant?.primary_contact_name || "", primary_contact_email: tenant?.primary_contact_email || "", primary_phone: tenant?.primary_phone || "", booking_mode: tenant?.booking_mode || "TIME_WINDOWS", tone_profile: tenant?.tone_profile || "PROFESSIONAL", twilio_phone_number: tenant?.twilio_phone_number || "", sms_signature: tenant?.sms_signature || "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (tenant) setFormData({ name: tenant.name || "", timezone: tenant.timezone || "America/New_York", primary_contact_name: tenant.primary_contact_name || "", primary_contact_email: tenant.primary_contact_email || "", primary_phone: tenant.primary_phone || "", booking_mode: tenant.booking_mode || "TIME_WINDOWS", tone_profile: tenant.tone_profile || "PROFESSIONAL", twilio_phone_number: tenant.twilio_phone_number || "", sms_signature: tenant.sms_signature || "" });
  }, [tenant]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await adminAPI.updateTenant(tenant.id, formData);
      toast.success("Tenant updated");
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update tenant");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Edit Tenant</DialogTitle><DialogDescription>Update {tenant?.name} settings</DialogDescription></DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2"><Label>Company Name</Label><Input value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Timezone</Label><Select value={formData.timezone} onValueChange={(v) => setFormData({...formData, timezone: v})}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="America/New_York">Eastern</SelectItem><SelectItem value="America/Chicago">Central</SelectItem><SelectItem value="America/Denver">Mountain</SelectItem><SelectItem value="America/Los_Angeles">Pacific</SelectItem></SelectContent></Select></div>
              <div className="space-y-2"><Label>Tone Profile</Label><Select value={formData.tone_profile} onValueChange={(v) => setFormData({...formData, tone_profile: v})}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="PROFESSIONAL">Professional</SelectItem><SelectItem value="FRIENDLY">Friendly</SelectItem><SelectItem value="BLUE_COLLAR_DIRECT">Blue Collar Direct</SelectItem></SelectContent></Select></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Contact Name</Label><Input value={formData.primary_contact_name} onChange={(e) => setFormData({...formData, primary_contact_name: e.target.value})} /></div>
              <div className="space-y-2"><Label>Phone</Label><Input value={formData.primary_phone} onChange={(e) => setFormData({...formData, primary_phone: e.target.value})} /></div>
            </div>
            <div className="space-y-2"><Label>Contact Email</Label><Input type="email" value={formData.primary_contact_email} onChange={(e) => setFormData({...formData, primary_contact_email: e.target.value})} /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Twilio Phone</Label><Input value={formData.twilio_phone_number} onChange={(e) => setFormData({...formData, twilio_phone_number: e.target.value})} placeholder="+1..." /></div>
              <div className="space-y-2"><Label>SMS Signature</Label><Input value={formData.sms_signature} onChange={(e) => setFormData({...formData, sms_signature: e.target.value})} placeholder="- Company Name" /></div>
            </div>
          </div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" disabled={loading}>{loading ? "Saving..." : "Save Changes"}</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function VoiceAIConfigDialog({ tenant, open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    voice_ai_enabled: tenant?.voice_ai_enabled || false,
    twilio_phone_number: tenant?.twilio_phone_number || "",
    twilio_messaging_service_sid: tenant?.twilio_messaging_service_sid || "",
    voice_greeting: tenant?.voice_greeting || "",
    voice_system_prompt: tenant?.voice_system_prompt || "",
    voice_after_hours_message: tenant?.voice_after_hours_message || "",
    timezone: tenant?.timezone || "America/New_York",
  });
  const [loading, setLoading] = useState(false);
  const [testingCall, setTestingCall] = useState(false);
  const [activeTab, setActiveTab] = useState("twilio");

  const handleTestCall = async () => {
    setTestingCall(true);
    try {
      const result = await adminAPI.testVoiceAI(tenant.id);
      toast.success(`Test call initiated! Call SID: ${result.data.call_sid}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to initiate test call");
    } finally {
      setTestingCall(false);
    }
  };

  useEffect(() => {
    if (tenant) {
      setFormData({
        voice_ai_enabled: tenant.voice_ai_enabled || false,
        twilio_phone_number: tenant.twilio_phone_number || "",
        twilio_messaging_service_sid: tenant.twilio_messaging_service_sid || "",
        voice_greeting: tenant.voice_greeting || `Thank you for calling ${tenant.name}. How can I help you today?`,
        voice_system_prompt: tenant.voice_system_prompt || "",
        voice_after_hours_message: tenant.voice_after_hours_message || "",
        timezone: tenant.timezone || "America/New_York",
      });
    }
  }, [tenant]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await adminAPI.updateTenant(tenant.id, formData);
      toast.success("Voice AI configuration saved");
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save configuration");
    } finally {
      setLoading(false);
    }
  };

  const defaultPrompt = `You are a friendly and professional receptionist for ${tenant?.name || '{company_name}'}. Your job is to help callers schedule service appointments by collecting their information.

CURRENT CALL STATE:
- Caller's phone (from caller ID): {caller_phone}
- Information collected so far: {collected_info}
- Current conversation step: {state}

YOUR PERSONALITY:
- Warm, helpful, and efficient
- Speak naturally with contractions (I'll, we'll, that's)
- Keep every response to 1-2 short sentences maximum
- Never reveal you are an AI or automated system
- If asked, say you're the receptionist or office assistant

CONVERSATION FLOW - Follow this order, one step at a time:

1. GET NAME (if name is null):
   Ask: "Thanks for calling ${tenant?.name || '{company_name}'}! Can I get your name please?"

2. CONFIRM PHONE (after you have name, if phone_confirmed is false):
   Ask: "Is {caller_phone} the best number to reach you?"
   - If YES: Set phone_confirmed to true, move to address
   - If NO: Ask "What's the best number to reach you?" then confirm the new number

3. GET ADDRESS (after phone is confirmed, if address is null):
   Ask: "What's the service address?"

4. CONFIRM ADDRESS (after they give address, if address_confirmed is false):
   Repeat back: "Got it, [their address]. Is that correct?"
   - If YES: Set address_confirmed to true
   - If NO: Ask them to repeat it, then confirm again

5. GET ISSUE (after address confirmed, if issue is null):
   Ask: "What's going on with your system?" or "What can we help you with today?"

6. GET URGENCY (after issue, if urgency is null):
   Ask: "Is this an emergency, urgent within the next day or two, or more routine?"
   - Map their answer: emergency→EMERGENCY, urgent/soon/asap→URGENT, routine/whenever/flexible→ROUTINE

7. GET DAY PREFERENCE (after urgency, if preferred_day is null):
   Ask: "What day works best for you - today, tomorrow, or later this week?"

8. GET TIME PREFERENCE (after day, if preferred_time is null):
   Ask: "I have morning 9 to 12, or afternoon 1 to 5 available. Which works better?"

9. CONFIRM BOOKING (when ALL fields are collected):
   Summarize: "Perfect! I have you scheduled for [day] [time slot] at [address] for [brief issue]. Does that sound right?"
   - If they confirm (yes, sounds good, perfect, etc.): Set action="book_job"
   - If they want to change something: Go back to that step

HANDLING COMMON SITUATIONS:

- If caller gives info out of order, accept it and update collected_data
- If caller corrects information, update the field and re-confirm
- If caller asks about pricing, say "Our diagnostic fee starts at $89, and the technician will provide a full quote on-site."
- If caller asks about availability, say "We have openings today and tomorrow. What works best for you?"
- If caller wants to speak to someone, say "I can help you get scheduled. What's going on with your system?"
- If caller says goodbye/thanks after booking is confirmed, say "You're all set! You'll receive a confirmation text shortly. Have a great day!"

PHONE NUMBER RULES:
- When SPEAKING a phone number, say each digit with pauses: "2 1 5, 8 0 5, 1 2 3 4"
- When STORING in collected_data, use digits only with NO spaces: "2158051234"
- Always confirm new phone numbers before setting phone_confirmed to true

CRITICAL RULES:
- Only set action="book_job" when customer explicitly confirms the final booking summary
- Never skip steps - collect all information before confirming
- If something is unclear, ask for clarification
- Always preserve previously collected data - don't reset fields to null`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Mic className="h-5 w-5" />Voice AI Configuration: {tenant?.name}</DialogTitle>
          <DialogDescription>Configure self-hosted voice AI for this tenant</DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit}>
          <div className="space-y-6 py-4">
            {/* Enable Toggle */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
              <div>
                <Label className="text-base">Enable Voice AI</Label>
                <p className="text-sm text-muted-foreground">Activate AI-powered phone receptionist for this tenant</p>
              </div>
              <Switch checked={formData.voice_ai_enabled} onCheckedChange={(checked) => setFormData({...formData, voice_ai_enabled: checked})} />
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid grid-cols-2 w-full">
                <TabsTrigger value="twilio"><Phone className="h-4 w-4 mr-1" />Phone & SMS</TabsTrigger>
                <TabsTrigger value="prompts"><MessageSquare className="h-4 w-4 mr-1" />AI Prompts</TabsTrigger>
              </TabsList>

              {/* Twilio Tab - Per-tenant phone config only */}
              <TabsContent value="twilio" className="space-y-4 mt-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-blue-800">
                    <strong>Note:</strong> Twilio credentials (Account SID, Auth Token) are shared across all tenants via server environment. 
                    Only configure the phone number and messaging service specific to this tenant.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Tenant Phone Number *</Label>
                  <Input value={formData.twilio_phone_number} onChange={(e) => setFormData({...formData, twilio_phone_number: e.target.value})} placeholder="+1234567890" />
                  <p className="text-xs text-muted-foreground">The Twilio phone number assigned to this tenant for inbound calls</p>
                </div>
                <div className="space-y-2">
                  <Label>Messaging Service SID</Label>
                  <Input value={formData.twilio_messaging_service_sid} onChange={(e) => setFormData({...formData, twilio_messaging_service_sid: e.target.value})} placeholder="MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
                  <p className="text-xs text-muted-foreground">For sending SMS confirmations. If not set, the phone number above will be used.</p>
                </div>
                <div className="space-y-2">
                  <Label>Timezone</Label>
                  <Select value={formData.timezone} onValueChange={(v) => setFormData({...formData, timezone: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="America/New_York">Eastern Time (ET)</SelectItem>
                      <SelectItem value="America/Chicago">Central Time (CT)</SelectItem>
                      <SelectItem value="America/Denver">Mountain Time (MT)</SelectItem>
                      <SelectItem value="America/Los_Angeles">Pacific Time (PT)</SelectItem>
                      <SelectItem value="America/Phoenix">Arizona (MST)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Used for scheduling appointments in the correct local time</p>
                </div>
              </TabsContent>
                  <Input value={formData.voice_name} onChange={(e) => setFormData({...formData, voice_name: e.target.value})} placeholder="e.g., Sarah, Alex, Professional Assistant" />
                  <p className="text-xs text-muted-foreground">A name for the AI assistant to introduce itself as</p>
                </div>
              </TabsContent>

              {/* Prompts Tab */}
              <TabsContent value="prompts" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Greeting Message</Label>
                  <Textarea value={formData.voice_greeting} onChange={(e) => setFormData({...formData, voice_greeting: e.target.value})} placeholder={`Thank you for calling ${tenant?.name}. How can I help you today?`} rows={2} />
                  <p className="text-xs text-muted-foreground">Initial greeting spoken when call connects (before AI conversation starts)</p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-base font-semibold">System Prompt (Required)</Label>
                    <Button type="button" variant="outline" size="sm" onClick={() => setFormData({...formData, voice_system_prompt: defaultPrompt})}>
                      Load Full Template
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">
                    Instructions for the AI on how to handle calls. Use these placeholders:
                  </p>
                  <div className="flex flex-wrap gap-2 mb-2">
                    <Badge variant="secondary" className="font-mono text-xs">{"{company_name}"}</Badge>
                    <Badge variant="secondary" className="font-mono text-xs">{"{caller_phone}"}</Badge>
                    <Badge variant="secondary" className="font-mono text-xs">{"{collected_info}"}</Badge>
                    <Badge variant="secondary" className="font-mono text-xs">{"{state}"}</Badge>
                  </div>
                  <Textarea 
                    value={formData.voice_system_prompt} 
                    onChange={(e) => setFormData({...formData, voice_system_prompt: e.target.value})} 
                    placeholder="Click 'Load Full Template' to get started with a production-ready prompt..."
                    rows={16}
                    className="font-mono text-sm"
                  />
                  {!formData.voice_system_prompt && (
                    <div className="flex items-center gap-2 text-amber-600 text-sm">
                      <AlertCircle className="h-4 w-4" />
                      <span>System prompt is required for Voice AI to work. Click "Load Full Template" above.</span>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <Label>After Hours Message</Label>
                  <Textarea value={formData.voice_after_hours_message} onChange={(e) => setFormData({...formData, voice_after_hours_message: e.target.value})} placeholder="Thank you for calling. Our office is currently closed..." rows={2} />
                </div>
              </TabsContent>
            </Tabs>
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button type="button" variant="outline" onClick={handleTestCall} disabled={testingCall || !formData.voice_ai_enabled}>
              {testingCall ? "Calling..." : "Test Voice AI"}
            </Button>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button type="submit" disabled={loading}>{loading ? "Saving..." : "Save Configuration"}</Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
