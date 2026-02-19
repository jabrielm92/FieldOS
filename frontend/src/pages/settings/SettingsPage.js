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
import { Building2, MessageSquare, Clock, Palette, Globe, Phone, Loader2, Save, Star } from "lucide-react";
import { settingsAPI } from "../../lib/api";

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tenant, setTenant] = useState(null);

  useEffect(() => {
    fetchTenantSettings();
  }, []);

  const fetchTenantSettings = async () => {
    try {
      const response = await settingsAPI.getTenantSettings();
      setTenant(response.data);
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
          <TabsTrigger value="branding" disabled className="flex items-center gap-1 text-xs sm:text-sm opacity-50 cursor-not-allowed">
            <Palette className="h-4 w-4 hidden sm:block" />
            Branding
          </TabsTrigger>
          <TabsTrigger value="portal" disabled className="flex items-center gap-1 text-xs sm:text-sm opacity-50 cursor-not-allowed">
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
              <CardDescription>Customize your brand appearance</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
                <div>
                  <Label className="text-base">Enable White-Label Branding</Label>
                  <p className="text-sm text-muted-foreground">Remove FieldOS branding and use your own</p>
                </div>
                <Switch checked={branding.white_label_enabled || false} onCheckedChange={(checked) => updateBranding("white_label_enabled", checked)} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="logo_url">Logo URL</Label>
                  <Input id="logo_url" placeholder="https://example.com/logo.png" value={branding.logo_url || ""} onChange={(e) => updateBranding("logo_url", e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="favicon_url">Favicon URL</Label>
                  <Input id="favicon_url" placeholder="https://example.com/favicon.ico" value={branding.favicon_url || ""} onChange={(e) => updateBranding("favicon_url", e.target.value)} />
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4">
                {["primary_color", "secondary_color", "accent_color", "text_on_primary"].map((colorField) => (
                  <div key={colorField} className="space-y-2">
                    <Label>{colorField.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</Label>
                    <div className="flex gap-2">
                      <input type="color" value={branding[colorField] || "#0066CC"} onChange={(e) => updateBranding(colorField, e.target.value)} className="h-10 w-14 rounded border cursor-pointer" />
                      <Input value={branding[colorField] || ""} onChange={(e) => updateBranding(colorField, e.target.value)} className="flex-1" />
                    </div>
                  </div>
                ))}
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

        {/* Portal Tab */}
        <TabsContent value="portal" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Customer Portal Settings
              </CardTitle>
              <CardDescription>Configure your customer-facing portal</CardDescription>
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
          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving} className="btn-industrial">
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              SAVE CHANGES
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
      </Tabs>
    </Layout>
  );
}
