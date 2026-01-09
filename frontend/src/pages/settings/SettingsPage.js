import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Switch } from "../../components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { toast } from "sonner";
import { Building2, MessageSquare, Clock, Users, Palette, Globe, Phone, Loader2 } from "lucide-react";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Branding settings
  const [branding, setBranding] = useState({
    logo_url: "",
    favicon_url: "",
    primary_color: "#0066CC",
    secondary_color: "#004499",
    accent_color: "#FF6600",
    text_on_primary: "#FFFFFF",
    font_family: "Inter",
    email_from_name: "",
    email_reply_to: "",
    sms_sender_name: "",
    portal_title: "",
    portal_welcome_message: "",
    portal_support_email: "",
    portal_support_phone: "",
    custom_domain: "",
    white_label_enabled: false
  });

  useEffect(() => {
    fetchBrandingSettings();
  }, []);

  const fetchBrandingSettings = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await axios.get(`${API_URL}/api/v1/settings/branding`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBranding(prev => ({ ...prev, ...response.data }));
    } catch (error) {
      console.error("Error fetching branding:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveBranding = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem("token");
      await axios.put(`${API_URL}/api/v1/settings/branding`, branding, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("Branding settings saved successfully");
    } catch (error) {
      toast.error("Failed to save branding settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSave = () => {
    toast.success("Settings saved successfully");
  };

  const updateBranding = (key, value) => {
    setBranding(prev => ({ ...prev, [key]: value }));
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

  return (
    <Layout title="Settings" subtitle="Configure your company settings">
      <Tabs defaultValue="company" className="max-w-4xl">
        <TabsList className="mb-6">
          <TabsTrigger value="company" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Company
          </TabsTrigger>
          <TabsTrigger value="branding" className="flex items-center gap-2">
            <Palette className="h-4 w-4" />
            Branding
          </TabsTrigger>
          <TabsTrigger value="portal" className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            Customer Portal
          </TabsTrigger>
          <TabsTrigger value="messaging" className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Messaging
          </TabsTrigger>
          <TabsTrigger value="scheduling" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
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
              <CardDescription>
                Basic information about your field service company
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="company_name">Company Name</Label>
                  <Input id="company_name" placeholder="Your Company Name" data-testid="settings-company-name" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Select defaultValue="America/New_York">
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
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="primary_phone">Primary Phone</Label>
                  <Input 
                    id="primary_phone" 
                    placeholder="+1 (555) 123-4567"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="primary_email">Primary Email</Label>
                  <Input 
                    id="primary_email" 
                    type="email"
                    placeholder="contact@yourcompany.com"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="service_area">Service Area</Label>
                <Textarea 
                  id="service_area" 
                  placeholder="Describe your service area (cities, zip codes, etc.)"
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Users className="h-5 w-5" />
                Team & Notifications
              </CardTitle>
              <CardDescription>
                Configure team notifications and alerts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="alert_email">Alert Email</Label>
                <Input 
                  id="alert_email" 
                  type="email"
                  placeholder="alerts@yourcompany.com"
                />
                <p className="text-xs text-muted-foreground">
                  Receive notifications for new leads, emergencies, and system alerts
                </p>
              </div>
              
              <div className="space-y-2">
                <Label>Reminder Notifications</Label>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded" />
                    <span className="text-sm">Day before reminders</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded" />
                    <span className="text-sm">Morning of reminders</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded" />
                    <span className="text-sm">En-route alerts</span>
                  </label>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSave} className="btn-industrial" data-testid="save-company-settings">
              SAVE CHANGES
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
              <CardDescription>
                Customize your brand appearance across all customer touchpoints
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
                <div>
                  <Label className="text-base">Enable White-Label Branding</Label>
                  <p className="text-sm text-muted-foreground">
                    Remove FieldOS branding and use your own brand identity
                  </p>
                </div>
                <Switch
                  checked={branding.white_label_enabled}
                  onCheckedChange={(checked) => updateBranding("white_label_enabled", checked)}
                  data-testid="white-label-toggle"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="logo_url">Logo URL</Label>
                  <Input 
                    id="logo_url" 
                    placeholder="https://example.com/logo.png"
                    value={branding.logo_url || ""}
                    onChange={(e) => updateBranding("logo_url", e.target.value)}
                    data-testid="branding-logo-url"
                  />
                  <p className="text-xs text-muted-foreground">Recommended size: 200x50px</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="favicon_url">Favicon URL</Label>
                  <Input 
                    id="favicon_url" 
                    placeholder="https://example.com/favicon.ico"
                    value={branding.favicon_url || ""}
                    onChange={(e) => updateBranding("favicon_url", e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">32x32px .ico or .png</p>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="primary_color">Primary Color</Label>
                  <div className="flex gap-2">
                    <input 
                      type="color" 
                      value={branding.primary_color}
                      onChange={(e) => updateBranding("primary_color", e.target.value)}
                      className="h-10 w-14 rounded border cursor-pointer"
                    />
                    <Input 
                      id="primary_color"
                      value={branding.primary_color}
                      onChange={(e) => updateBranding("primary_color", e.target.value)}
                      className="flex-1"
                      data-testid="branding-primary-color"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="secondary_color">Secondary Color</Label>
                  <div className="flex gap-2">
                    <input 
                      type="color" 
                      value={branding.secondary_color}
                      onChange={(e) => updateBranding("secondary_color", e.target.value)}
                      className="h-10 w-14 rounded border cursor-pointer"
                    />
                    <Input 
                      id="secondary_color"
                      value={branding.secondary_color}
                      onChange={(e) => updateBranding("secondary_color", e.target.value)}
                      className="flex-1"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="accent_color">Accent Color</Label>
                  <div className="flex gap-2">
                    <input 
                      type="color" 
                      value={branding.accent_color}
                      onChange={(e) => updateBranding("accent_color", e.target.value)}
                      className="h-10 w-14 rounded border cursor-pointer"
                    />
                    <Input 
                      id="accent_color"
                      value={branding.accent_color}
                      onChange={(e) => updateBranding("accent_color", e.target.value)}
                      className="flex-1"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="text_on_primary">Text on Primary</Label>
                  <div className="flex gap-2">
                    <input 
                      type="color" 
                      value={branding.text_on_primary}
                      onChange={(e) => updateBranding("text_on_primary", e.target.value)}
                      className="h-10 w-14 rounded border cursor-pointer"
                    />
                    <Input 
                      id="text_on_primary"
                      value={branding.text_on_primary}
                      onChange={(e) => updateBranding("text_on_primary", e.target.value)}
                      className="flex-1"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Font Family</Label>
                <Select 
                  value={branding.font_family} 
                  onValueChange={(value) => updateBranding("font_family", value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Inter">Inter (Modern)</SelectItem>
                    <SelectItem value="Roboto">Roboto (Clean)</SelectItem>
                    <SelectItem value="Open Sans">Open Sans (Friendly)</SelectItem>
                    <SelectItem value="Lato">Lato (Professional)</SelectItem>
                    <SelectItem value="Poppins">Poppins (Bold)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Preview */}
              <div className="mt-6 p-4 border rounded-lg">
                <Label className="text-sm text-muted-foreground mb-3 block">Preview</Label>
                <div 
                  className="p-4 rounded-lg" 
                  style={{ backgroundColor: branding.primary_color }}
                >
                  <h3 
                    className="text-lg font-semibold mb-2"
                    style={{ color: branding.text_on_primary, fontFamily: branding.font_family }}
                  >
                    Your Company Name
                  </h3>
                  <p 
                    className="text-sm opacity-90"
                    style={{ color: branding.text_on_primary, fontFamily: branding.font_family }}
                  >
                    Welcome to your customer portal
                  </p>
                  <button 
                    className="mt-3 px-4 py-2 rounded text-sm font-medium"
                    style={{ 
                      backgroundColor: branding.accent_color, 
                      color: branding.text_on_primary,
                      fontFamily: branding.font_family 
                    }}
                  >
                    Book Service
                  </button>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button 
              onClick={handleSaveBranding} 
              className="btn-industrial" 
              disabled={saving}
              data-testid="save-branding-settings"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  SAVING...
                </>
              ) : (
                "SAVE BRANDING"
              )}
            </Button>
          </div>
        </TabsContent>

        {/* Customer Portal Tab */}
        <TabsContent value="portal" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Customer Portal Settings
              </CardTitle>
              <CardDescription>
                Configure your self-service customer portal
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="portal_title">Portal Title</Label>
                <Input 
                  id="portal_title" 
                  placeholder="Your Company Customer Portal"
                  value={branding.portal_title || ""}
                  onChange={(e) => updateBranding("portal_title", e.target.value)}
                  data-testid="portal-title"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="portal_welcome">Welcome Message</Label>
                <Textarea 
                  id="portal_welcome" 
                  placeholder="Welcome to your customer portal. View appointments, pay invoices, and more."
                  value={branding.portal_welcome_message || ""}
                  onChange={(e) => updateBranding("portal_welcome_message", e.target.value)}
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="portal_support_email">Support Email</Label>
                  <Input 
                    id="portal_support_email" 
                    type="email"
                    placeholder="support@yourcompany.com"
                    value={branding.portal_support_email || ""}
                    onChange={(e) => updateBranding("portal_support_email", e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="portal_support_phone">Support Phone</Label>
                  <Input 
                    id="portal_support_phone" 
                    placeholder="+1 (555) 123-4567"
                    value={branding.portal_support_phone || ""}
                    onChange={(e) => updateBranding("portal_support_phone", e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2 pt-4 border-t">
                <Label htmlFor="custom_domain">Custom Domain</Label>
                <Input 
                  id="custom_domain" 
                  placeholder="portal.yourcompany.com"
                  value={branding.custom_domain || ""}
                  onChange={(e) => updateBranding("custom_domain", e.target.value)}
                  data-testid="custom-domain"
                />
                <p className="text-xs text-muted-foreground">
                  To use a custom domain, add a CNAME record pointing to <code className="bg-muted px-1 rounded">portal.fieldos.com</code>.
                  Contact support for verification.
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button 
              onClick={handleSaveBranding} 
              className="btn-industrial" 
              disabled={saving}
              data-testid="save-portal-settings"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  SAVING...
                </>
              ) : (
                "SAVE PORTAL SETTINGS"
              )}
            </Button>
          </div>
        </TabsContent>

        {/* Messaging Tab */}
        <TabsContent value="messaging" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Messaging Style
              </CardTitle>
              <CardDescription>
                Configure how AI responds to your customers
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Tone Profile</Label>
                <Select defaultValue="PROFESSIONAL">
                  <SelectTrigger data-testid="settings-tone">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PROFESSIONAL">Professional</SelectItem>
                    <SelectItem value="FRIENDLY">Friendly</SelectItem>
                    <SelectItem value="BLUE_COLLAR_DIRECT">Blue Collar Direct</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  This affects how AI generates SMS responses
                </p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="sms_signature">SMS Signature</Label>
                <Input 
                  id="sms_signature" 
                  placeholder="– Your Company Team"
                  data-testid="settings-signature"
                />
                <p className="text-xs text-muted-foreground">
                  Added to the end of outbound messages
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email_from_name">Email From Name</Label>
                <Input 
                  id="email_from_name" 
                  placeholder="Your Company"
                  value={branding.email_from_name || ""}
                  onChange={(e) => updateBranding("email_from_name", e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email_reply_to">Email Reply-To</Label>
                <Input 
                  id="email_reply_to" 
                  type="email"
                  placeholder="support@yourcompany.com"
                  value={branding.email_reply_to || ""}
                  onChange={(e) => updateBranding("email_reply_to", e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Phone className="h-5 w-5" />
                Voice AI Settings
              </CardTitle>
              <CardDescription>
                Configure your AI phone receptionist
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
                <div>
                  <Label className="text-base">Enable Self-Hosted Voice AI</Label>
                  <p className="text-sm text-muted-foreground">
                    Use our cost-optimized voice AI instead of third-party services (saves ~70%)
                  </p>
                </div>
                <Switch data-testid="self-hosted-voice-toggle" />
              </div>
              
              <p className="text-sm text-muted-foreground">
                Voice AI automatically answers calls, collects customer information, and books appointments.
                When enabled, calls to your Twilio number will be handled by our AI receptionist.
              </p>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSaveBranding} className="btn-industrial" disabled={saving}>
              {saving ? "SAVING..." : "SAVE MESSAGING SETTINGS"}
            </Button>
          </div>
        </TabsContent>

        {/* Scheduling Tab */}
        <TabsContent value="scheduling" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Scheduling
              </CardTitle>
              <CardDescription>
                Configure booking and scheduling options
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Booking Mode</Label>
                <Select defaultValue="TIME_WINDOWS">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="TIME_WINDOWS">Time Windows (8am-12pm, etc.)</SelectItem>
                    <SelectItem value="EXACT_TIMES">Exact Times</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Morning Window</Label>
                  <div className="flex gap-2">
                    <Input type="time" defaultValue="08:00" className="flex-1" />
                    <span className="flex items-center text-muted-foreground">to</span>
                    <Input type="time" defaultValue="12:00" className="flex-1" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Afternoon Window</Label>
                  <div className="flex gap-2">
                    <Input type="time" defaultValue="12:00" className="flex-1" />
                    <span className="flex items-center text-muted-foreground">to</span>
                    <Input type="time" defaultValue="17:00" className="flex-1" />
                  </div>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="emergency_rules">Emergency Rules</Label>
                <Textarea 
                  id="emergency_rules" 
                  placeholder="Describe how emergencies should be handled..."
                  rows={3}
                />
                <p className="text-xs text-muted-foreground">
                  Instructions for handling emergency service requests
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSave} className="btn-industrial" data-testid="save-scheduling-settings">
              SAVE SCHEDULING SETTINGS
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </Layout>
  );
}
