import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Switch } from "../../components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { toast } from "sonner";
import { Building2, MessageSquare, Clock, Palette, Globe, Phone, Loader2, Save, Star, Link2, Wrench, Trash2, Pencil, Plus } from "lucide-react";
import { settingsAPI, customFieldsAPI, industryAPI } from "../../lib/api";
import { useBranding } from "../../contexts/BrandingContext";

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tenant, setTenant] = useState(null);
  const brandingCtx = useBranding();

  // Custom Fields state
  const [customFields, setCustomFields] = useState([]);
  const [industrySettings, setIndustrySettings] = useState({ industry_slug: '', custom_job_types: [] });
  const [showAddField, setShowAddField] = useState(false);
  const [newField, setNewField] = useState({ name: '', type: 'TEXT', applies_to: 'job', required: false, options: [] });
  const [editingField, setEditingField] = useState(null);
  const [fieldOptionsInput, setFieldOptionsInput] = useState('');

  useEffect(() => {
    fetchTenantSettings();
  }, []);

  const fetchTenantSettings = async () => {
    try {
      const [tenantRes, fieldsRes, industryRes] = await Promise.allSettled([
        settingsAPI.getTenantSettings(),
        customFieldsAPI.list(),
        industryAPI.getSettings(),
      ]);
      if (tenantRes.status === 'fulfilled') setTenant(tenantRes.value.data);
      if (fieldsRes.status === 'fulfilled') setCustomFields(fieldsRes.value.data.custom_fields || []);
      if (industryRes.status === 'fulfilled') setIndustrySettings(industryRes.value.data);
      if (tenantRes.status === 'rejected') toast.error("Failed to load settings");
    } catch (error) {
      toast.error("Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await settingsAPI.updateTenantSettings(tenant);
      toast.success("Settings saved successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field, value) => {
    setTenant(prev => ({ ...prev, [field]: value }));
  };

  const updateBranding = (field, value) => {
    setTenant(prev => ({
      ...prev,
      branding: { ...(prev?.branding || {}), [field]: value }
    }));
  };

  const updateReviewSettings = (field, value) => {
    setTenant(prev => ({
      ...prev,
      review_settings: { ...(prev?.review_settings || {}), [field]: value }
    }));
  };

  const handleSaveReviews = async () => {
    setSaving(true);
    try {
      await settingsAPI.updateReviewSettings(tenant?.review_settings || {});
      toast.success("Review settings saved");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save review settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveBranding = async () => {
    setSaving(true);
    try {
      const brandingData = tenant?.branding || {};
      await settingsAPI.updateBrandingSettings(brandingData);
      // Apply CSS variables via context
      if (brandingCtx?.applyBrandingCSS) {
        brandingCtx.applyBrandingCSS(brandingData);
      }
      if (brandingCtx?.setBranding) {
        brandingCtx.setBranding(prev => ({ ...prev, ...brandingData }));
      }
      toast.success("Branding settings saved");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save branding settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSavePortal = async () => {
    setSaving(true);
    try {
      const portalFields = {
        portal_title: tenant?.branding?.portal_title,
        portal_welcome_message: tenant?.branding?.portal_welcome_message,
        portal_support_email: tenant?.branding?.portal_support_email,
        portal_support_phone: tenant?.branding?.portal_support_phone,
      };
      await settingsAPI.updateBrandingSettings(portalFields);
      toast.success("Portal settings saved");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save portal settings");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Layout title="Settings" subtitle="Configure your company settings">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  const branding = tenant?.branding || {};

  return (
    <Layout title="Settings" subtitle="Configure your company settings">
      <Tabs defaultValue="company" className="max-w-4xl">
        <TabsList className="mb-6 flex-wrap h-auto gap-1">
          <TabsTrigger value="company" className="flex items-center gap-1 text-xs sm:text-sm">
            <Building2 className="h-4 w-4 hidden sm:block" />
            Company
          </TabsTrigger>
          <TabsTrigger value="branding" className="flex items-center gap-1 text-xs sm:text-sm">
            <Palette className="h-4 w-4 hidden sm:block" />
            Branding
          </TabsTrigger>
          <TabsTrigger value="portal" className="flex items-center gap-1 text-xs sm:text-sm">
            <Globe className="h-4 w-4 hidden sm:block" />
            Portal
          </TabsTrigger>
          <TabsTrigger value="messaging" className="flex items-center gap-1 text-xs sm:text-sm">
            <MessageSquare className="h-4 w-4 hidden sm:block" />
            Messaging
          </TabsTrigger>
          <TabsTrigger value="reviews" className="flex items-center gap-1 text-xs sm:text-sm">
            <Star className="h-3.5 w-3.5" />
            Reviews
          </TabsTrigger>
          <TabsTrigger value="scheduling" className="flex items-center gap-1 text-xs sm:text-sm">
            <Clock className="h-4 w-4 hidden sm:block" />
            Scheduling
          </TabsTrigger>
          <TabsTrigger value="fields" className="flex items-center gap-1 text-xs sm:text-sm">
            <Wrench className="h-4 w-4 hidden sm:block" />
            Fields
          </TabsTrigger>
        </TabsList>

        {/* Company Tab */}
        <TabsContent value="company" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Company Information
              </CardTitle>
              <CardDescription>Basic information about your field service company</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="company_name">Company Name</Label>
                  <Input 
                    id="company_name" 
                    value={tenant?.name || ""} 
                    onChange={(e) => updateField("name", e.target.value)}
                    data-testid="settings-company-name" 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Select value={tenant?.timezone || "America/New_York"} onValueChange={(v) => updateField("timezone", v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="America/New_York">Eastern</SelectItem>
                      <SelectItem value="America/Chicago">Central</SelectItem>
                      <SelectItem value="America/Denver">Mountain</SelectItem>
                      <SelectItem value="America/Los_Angeles">Pacific</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="primary_phone">Primary Phone</Label>
                  <Input id="primary_phone" value={tenant?.primary_phone || ""} onChange={(e) => updateField("primary_phone", e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="primary_email">Primary Email</Label>
                  <Input id="primary_email" type="email" value={tenant?.primary_contact_email || ""} onChange={(e) => updateField("primary_contact_email", e.target.value)} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="contact_name">Contact Name</Label>
                  <Input id="contact_name" value={tenant?.primary_contact_name || ""} onChange={(e) => updateField("primary_contact_name", e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Tone Profile</Label>
                  <Select value={tenant?.tone_profile || "PROFESSIONAL"} onValueChange={(v) => updateField("tone_profile", v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PROFESSIONAL">Professional</SelectItem>
                      <SelectItem value="FRIENDLY">Friendly</SelectItem>
                      <SelectItem value="BLUE_COLLAR_DIRECT">Blue Collar Direct</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="service_area">Service Area</Label>
                <Textarea id="service_area" value={tenant?.service_area || ""} onChange={(e) => updateField("service_area", e.target.value)} placeholder="Cities, zip codes, or regions you serve" rows={2} />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving} className="btn-industrial" data-testid="save-company-settings">
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              {saving ? "SAVING..." : "SAVE CHANGES"}
            </Button>
          </div>
        </TabsContent>

        {/* Branding Tab */}
        <TabsContent value="branding" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Palette className="h-5 w-5" />
                Brand Colors & Logo
              </CardTitle>
              <CardDescription>Customize your brand appearance across the app and customer portal</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
                <div>
                  <Label className="text-base">Enable White-Label Branding</Label>
                  <p className="text-sm text-muted-foreground">Remove FieldOS branding and use your own</p>
                </div>
                <Switch checked={branding.white_label_enabled || false} onCheckedChange={(checked) => updateBranding("white_label_enabled", checked)} />
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="logo_url">Logo URL</Label>
                  <Input id="logo_url" placeholder="https://example.com/logo.png" value={branding.logo_url || ""} onChange={(e) => updateBranding("logo_url", e.target.value)} />
                  <p className="text-xs text-muted-foreground">Enter a publicly accessible URL to your logo image</p>
                </div>
                {branding.logo_url && (
                  <div className="p-4 border rounded-lg bg-muted/30">
                    <Label className="text-sm text-muted-foreground mb-2 block">Logo Preview</Label>
                    <img
                      src={branding.logo_url}
                      alt="Company logo preview"
                      className="h-12 object-contain"
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  </div>
                )}
              </div>

              <div>
                <Label className="text-base mb-3 block">Brand Colors</Label>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { field: "primary_color", label: "Primary Color", default: "#0066CC" },
                    { field: "secondary_color", label: "Secondary Color", default: "#004499" },
                    { field: "accent_color", label: "Accent Color", default: "#FF6600" },
                    { field: "text_on_primary", label: "Text on Primary", default: "#FFFFFF" },
                  ].map(({ field, label, default: defaultColor }) => (
                    <div key={field} className="space-y-2">
                      <Label className="text-sm">{label}</Label>
                      <div className="flex gap-2 items-center">
                        <input
                          type="color"
                          value={branding[field] || defaultColor}
                          onChange={(e) => updateBranding(field, e.target.value)}
                          className="h-8 w-12 cursor-pointer rounded border flex-shrink-0"
                        />
                        <Input
                          value={branding[field] || defaultColor}
                          onChange={(e) => updateBranding(field, e.target.value)}
                          className="flex-1 font-mono text-sm"
                          placeholder={defaultColor}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {(branding.primary_color || branding.secondary_color || branding.accent_color) && (
                <div className="p-4 border rounded-lg bg-muted/30">
                  <Label className="text-sm text-muted-foreground mb-3 block">Color Preview</Label>
                  <div className="flex gap-3 items-center">
                    <div
                      className="h-10 w-24 rounded flex items-center justify-center text-xs font-medium"
                      style={{ backgroundColor: branding.primary_color || "#0066CC", color: branding.text_on_primary || "#FFFFFF" }}
                    >
                      Primary
                    </div>
                    <div
                      className="h-10 w-24 rounded flex items-center justify-center text-xs font-medium text-white"
                      style={{ backgroundColor: branding.secondary_color || "#004499" }}
                    >
                      Secondary
                    </div>
                    <div
                      className="h-10 w-24 rounded flex items-center justify-center text-xs font-medium text-white"
                      style={{ backgroundColor: branding.accent_color || "#FF6600" }}
                    >
                      Accent
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveBranding} disabled={saving} className="btn-industrial">
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              SAVE BRANDING
            </Button>
          </div>
        </TabsContent>

        {/* Portal Tab */}
        <TabsContent value="portal" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Customer Portal Settings
              </CardTitle>
              <CardDescription>Configure your customer-facing self-service portal</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Portal Title</Label>
                  <Input value={branding.portal_title || ""} onChange={(e) => updateBranding("portal_title", e.target.value)} placeholder="Customer Portal" />
                </div>
                <div className="space-y-2">
                  <Label>Support Phone</Label>
                  <Input value={branding.portal_support_phone || ""} onChange={(e) => updateBranding("portal_support_phone", e.target.value)} placeholder="+1 (555) 123-4567" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Support Email</Label>
                <Input type="email" value={branding.portal_support_email || ""} onChange={(e) => updateBranding("portal_support_email", e.target.value)} placeholder="support@company.com" />
              </div>
              <div className="space-y-2">
                <Label>Welcome Message</Label>
                <Textarea value={branding.portal_welcome_message || ""} onChange={(e) => updateBranding("portal_welcome_message", e.target.value)} placeholder="Welcome to our customer portal..." rows={3} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Link2 className="h-5 w-5" />
                Portal Links
              </CardTitle>
              <CardDescription>How to share the customer portal with your customers</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 border rounded-lg bg-muted/50 space-y-3">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-sm font-bold text-primary">1</span>
                  </div>
                  <div>
                    <p className="font-medium text-sm">Go to a Customer Record</p>
                    <p className="text-sm text-muted-foreground">Navigate to any customer in the Customers section of FieldOS.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-sm font-bold text-primary">2</span>
                  </div>
                  <div>
                    <p className="font-medium text-sm">Generate a Portal Link</p>
                    <p className="text-sm text-muted-foreground">Use the "Generate Portal Link" action on the customer record to create a unique, secure link for that customer.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-sm font-bold text-primary">3</span>
                  </div>
                  <div>
                    <p className="font-medium text-sm">Share with Your Customer</p>
                    <p className="text-sm text-muted-foreground">Send the generated link via SMS or email. Customers can then view appointments, invoices, submit service requests, and more — no login required.</p>
                  </div>
                </div>
              </div>
              <div className="p-3 border rounded-lg bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800">
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  <strong>Note:</strong> Each portal link is unique to a customer and uses a secure token. Links do not expire unless manually regenerated.
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSavePortal} disabled={saving} className="btn-industrial">
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              SAVE PORTAL SETTINGS
            </Button>
          </div>
        </TabsContent>

        {/* Messaging Tab */}
        <TabsContent value="messaging" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Phone className="h-5 w-5" />
                Twilio SMS Settings
              </CardTitle>
              <CardDescription>Your SMS messaging configuration (managed by admin)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Twilio Phone Number</Label>
                <Input value={tenant?.twilio_phone_number || ""} disabled className="bg-muted" />
                <p className="text-xs text-muted-foreground">Contact admin to change</p>
              </div>
              <div className="space-y-2">
                <Label>SMS Signature</Label>
                <Input value={tenant?.sms_signature || ""} onChange={(e) => updateField("sms_signature", e.target.value)} placeholder="- Your Company Name" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Email Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>From Name</Label>
                  <Input value={branding.email_from_name || ""} onChange={(e) => updateBranding("email_from_name", e.target.value)} placeholder="Your Company" />
                </div>
                <div className="space-y-2">
                  <Label>Reply-To Email</Label>
                  <Input type="email" value={branding.email_reply_to || ""} onChange={(e) => updateBranding("email_reply_to", e.target.value)} placeholder="reply@company.com" />
                </div>
              </div>
            </CardContent>
          </Card>
          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving} className="btn-industrial">
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              SAVE CHANGES
            </Button>
          </div>
        </TabsContent>

        {/* Reviews Tab */}
        <TabsContent value="reviews" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Star className="h-5 w-5" />
                Review Request Automation
              </CardTitle>
              <CardDescription>
                Automatically send review request SMS after job completion
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base">Enable Automated Reviews</Label>
                  <p className="text-sm text-muted-foreground">Send review requests after completed jobs</p>
                </div>
                <Switch
                  checked={tenant?.review_settings?.enabled !== false}
                  onCheckedChange={(v) => updateReviewSettings("enabled", v)}
                />
              </div>
              <div className="space-y-2">
                <Label>Send Delay (hours after completion)</Label>
                <Select
                  value={String(tenant?.review_settings?.delay_hours ?? 2)}
                  onValueChange={(v) => updateReviewSettings("delay_hours", parseInt(v))}
                >
                  <SelectTrigger className="w-[200px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 hour</SelectItem>
                    <SelectItem value="2">2 hours</SelectItem>
                    <SelectItem value="4">4 hours</SelectItem>
                    <SelectItem value="24">24 hours (next day)</SelectItem>
                    <SelectItem value="48">48 hours (2 days)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Preferred Platform</Label>
                <Select
                  value={tenant?.review_settings?.preferred_platform || "google"}
                  onValueChange={(v) => updateReviewSettings("preferred_platform", v)}
                >
                  <SelectTrigger className="w-[200px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="google">Google</SelectItem>
                    <SelectItem value="yelp">Yelp</SelectItem>
                    <SelectItem value="facebook">Facebook</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Review Links</CardTitle>
              <CardDescription>Paste your business review page URLs</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Google Review URL</Label>
                <Input
                  value={tenant?.review_settings?.google_review_url || ""}
                  onChange={(e) => updateReviewSettings("google_review_url", e.target.value)}
                  placeholder="https://g.page/r/..."
                />
              </div>
              <div className="space-y-2">
                <Label>Yelp Review URL</Label>
                <Input
                  value={tenant?.review_settings?.yelp_review_url || ""}
                  onChange={(e) => updateReviewSettings("yelp_review_url", e.target.value)}
                  placeholder="https://www.yelp.com/biz/..."
                />
              </div>
              <div className="space-y-2">
                <Label>Facebook Review URL</Label>
                <Input
                  value={tenant?.review_settings?.facebook_review_url || ""}
                  onChange={(e) => updateReviewSettings("facebook_review_url", e.target.value)}
                  placeholder="https://www.facebook.com/..."
                />
              </div>
              <div className="space-y-2">
                <Label>Custom Message Template</Label>
                <Textarea
                  value={tenant?.review_settings?.message_template || ""}
                  onChange={(e) => updateReviewSettings("message_template", e.target.value)}
                  placeholder="Hi {first_name}! Thanks for choosing {company_name}. Leave us a review: {review_link}"
                  rows={3}
                />
                <p className="text-xs text-muted-foreground">
                  Variables: {"{first_name}"}, {"{company_name}"}, {"{review_link}"}
                </p>
              </div>
            </CardContent>
          </Card>
          <div className="flex justify-end">
            <Button onClick={handleSaveReviews} disabled={saving} className="btn-industrial">
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              SAVE CHANGES
            </Button>
          </div>
        </TabsContent>

        {/* Scheduling Tab */}
        <TabsContent value="scheduling" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Scheduling Preferences
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Booking Mode</Label>
                <Select value={tenant?.booking_mode || "TIME_WINDOWS"} onValueChange={(v) => updateField("booking_mode", v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="TIME_WINDOWS">Time Windows (e.g., 8am-12pm)</SelectItem>
                    <SelectItem value="EXACT_TIME">Exact Time Slots</SelectItem>
                    <SelectItem value="CALLBACK">Callback Only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Emergency Rules</Label>
                <Textarea value={tenant?.emergency_rules || ""} onChange={(e) => updateField("emergency_rules", e.target.value)} placeholder="Define what constitutes an emergency and how to handle them..." rows={3} />
              </div>
            </CardContent>
          </Card>
          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving} className="btn-industrial">
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              SAVE CHANGES
            </Button>
          </div>
        </TabsContent>

        {/* Fields Tab */}
        <TabsContent value="fields" className="space-y-6">
          {/* Industry Section */}
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Wrench className="h-5 w-5" />
                Industry
              </CardTitle>
              <CardDescription>Select your industry to load default job types and terminology</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Industry</Label>
                <Select
                  value={industrySettings.industry_slug || ""}
                  onValueChange={async (v) => {
                    try {
                      const res = await industryAPI.updateSettings({ industry_slug: v });
                      setIndustrySettings(res.data);
                      toast.success("Industry updated");
                    } catch (err) {
                      toast.error("Failed to update industry");
                    }
                  }}
                >
                  <SelectTrigger className="w-[280px]">
                    <SelectValue placeholder="Select your industry" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hvac">HVAC</SelectItem>
                    <SelectItem value="plumbing">Plumbing</SelectItem>
                    <SelectItem value="electrical">Electrical</SelectItem>
                    <SelectItem value="landscaping">Landscaping</SelectItem>
                    <SelectItem value="cleaning">Cleaning</SelectItem>
                    <SelectItem value="general">General Contractor</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Custom Fields Section */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading flex items-center gap-2">
                  Custom Fields
                </CardTitle>
                <CardDescription>Define additional fields for jobs, customers, or properties</CardDescription>
              </div>
              <Button
                size="sm"
                className="btn-industrial"
                onClick={() => {
                  setShowAddField(true);
                  setEditingField(null);
                  setNewField({ name: '', type: 'TEXT', applies_to: 'job', required: false, options: [] });
                  setFieldOptionsInput('');
                }}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Field
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add / Edit Field Form */}
              {showAddField && (
                <div className="border rounded-lg p-4 bg-muted/30 space-y-4">
                  <h4 className="font-medium text-sm">{editingField ? "Edit Field" : "New Custom Field"}</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Field Name *</Label>
                      <Input
                        value={newField.name}
                        onChange={(e) => setNewField(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="e.g. Equipment Serial #"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Field Type</Label>
                      <Select
                        value={newField.type}
                        onValueChange={(v) => setNewField(prev => ({ ...prev, type: v }))}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="TEXT">Text</SelectItem>
                          <SelectItem value="NUMBER">Number</SelectItem>
                          <SelectItem value="SELECT">Select (dropdown)</SelectItem>
                          <SelectItem value="MULTISELECT">Multi-Select (checkboxes)</SelectItem>
                          <SelectItem value="DATE">Date</SelectItem>
                          <SelectItem value="BOOLEAN">Yes / No</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Applies To</Label>
                      <Select
                        value={newField.applies_to}
                        onValueChange={(v) => setNewField(prev => ({ ...prev, applies_to: v }))}
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="job">Job</SelectItem>
                          <SelectItem value="customer">Customer</SelectItem>
                          <SelectItem value="property">Property</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-center gap-3 pt-6">
                      <Switch
                        checked={newField.required}
                        onCheckedChange={(v) => setNewField(prev => ({ ...prev, required: v }))}
                      />
                      <Label>Required field</Label>
                    </div>
                  </div>
                  {(newField.type === 'SELECT' || newField.type === 'MULTISELECT') && (
                    <div className="space-y-2">
                      <Label>Options (comma-separated)</Label>
                      <Input
                        value={fieldOptionsInput}
                        onChange={(e) => {
                          setFieldOptionsInput(e.target.value);
                          setNewField(prev => ({
                            ...prev,
                            options: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                          }));
                        }}
                        placeholder="Option 1, Option 2, Option 3"
                      />
                    </div>
                  )}
                  <div className="flex gap-2 justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setShowAddField(false);
                        setEditingField(null);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      className="btn-industrial"
                      onClick={async () => {
                        if (!newField.name.trim()) {
                          toast.error("Field name is required");
                          return;
                        }
                        try {
                          if (editingField) {
                            const res = await customFieldsAPI.update(editingField.id, newField);
                            setCustomFields(prev => prev.map(f => f.id === editingField.id ? res.data.field : f));
                            toast.success("Field updated");
                          } else {
                            const res = await customFieldsAPI.create(newField);
                            setCustomFields(prev => [...prev, res.data.field]);
                            toast.success("Field created");
                          }
                          setShowAddField(false);
                          setEditingField(null);
                          setNewField({ name: '', type: 'TEXT', applies_to: 'job', required: false, options: [] });
                          setFieldOptionsInput('');
                        } catch (err) {
                          toast.error(err.response?.data?.detail || "Failed to save field");
                        }
                      }}
                    >
                      {editingField ? "Update Field" : "Create Field"}
                    </Button>
                  </div>
                </div>
              )}

              {/* Fields Table */}
              {customFields.length === 0 && !showAddField ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  No custom fields yet. Click "Add Field" to create one.
                </p>
              ) : customFields.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-4 py-2 font-medium">Name</th>
                        <th className="text-left px-4 py-2 font-medium">Type</th>
                        <th className="text-left px-4 py-2 font-medium">Applies To</th>
                        <th className="text-left px-4 py-2 font-medium">Required</th>
                        <th className="text-right px-4 py-2 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customFields.map((field) => (
                        <tr key={field.id} className="border-t hover:bg-muted/20">
                          <td className="px-4 py-2 font-medium">{field.name}</td>
                          <td className="px-4 py-2 text-muted-foreground capitalize">{field.type}</td>
                          <td className="px-4 py-2 text-muted-foreground capitalize">{field.applies_to}</td>
                          <td className="px-4 py-2">
                            {field.required ? (
                              <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">Required</span>
                            ) : (
                              <span className="text-xs text-muted-foreground">Optional</span>
                            )}
                          </td>
                          <td className="px-4 py-2 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => {
                                  setEditingField(field);
                                  setNewField({
                                    name: field.name,
                                    type: field.type,
                                    applies_to: field.applies_to,
                                    required: field.required,
                                    options: field.options || [],
                                  });
                                  setFieldOptionsInput((field.options || []).join(', '));
                                  setShowAddField(true);
                                }}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-destructive hover:text-destructive"
                                onClick={async () => {
                                  try {
                                    await customFieldsAPI.delete(field.id);
                                    setCustomFields(prev => prev.filter(f => f.id !== field.id));
                                    toast.success("Field deleted");
                                  } catch (err) {
                                    toast.error("Failed to delete field");
                                  }
                                }}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </Layout>
  );
}
