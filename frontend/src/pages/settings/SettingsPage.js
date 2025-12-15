import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Separator } from "../../components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { toast } from "sonner";
import { Building2, Phone, MessageSquare, Clock, Shield } from "lucide-react";

export default function SettingsPage() {
  const handleSave = () => {
    toast.success("Settings saved successfully");
  };

  return (
    <Layout title="Settings" subtitle="Configure your company settings">
      <div className="max-w-3xl space-y-6">
        {/* Company Information */}
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

        {/* SMS & Twilio */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading flex items-center gap-2">
              <Phone className="h-5 w-5" />
              SMS Configuration
            </CardTitle>
            <CardDescription>
              Twilio settings for SMS messaging
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="twilio_phone">Twilio Phone Number</Label>
              <Input 
                id="twilio_phone" 
                placeholder="+1 (555) 123-4567"
                data-testid="settings-twilio-phone"
              />
              <p className="text-xs text-muted-foreground">
                This number will be used for all outbound SMS
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Messaging Style */}
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
          </CardContent>
        </Card>

        {/* Scheduling */}
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
            
            <div className="space-y-2">
              <Label htmlFor="emergency_rules">Emergency Rules</Label>
              <Textarea 
                id="emergency_rules" 
                placeholder="Describe how emergencies should be handled..."
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Vapi Integration */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Vapi Integration
            </CardTitle>
            <CardDescription>
              Configure Vapi voice assistant integration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-muted rounded-md">
              <h4 className="font-medium mb-2">Webhook Endpoints</h4>
              <p className="text-sm text-muted-foreground mb-4">
                Configure these URLs in your Vapi assistant:
              </p>
              <div className="space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between p-2 bg-background rounded">
                  <span>Create Lead:</span>
                  <code className="text-primary">/api/v1/vapi/create-lead</code>
                </div>
                <div className="flex items-center justify-between p-2 bg-background rounded">
                  <span>Check Availability:</span>
                  <code className="text-primary">/api/v1/vapi/check-availability</code>
                </div>
                <div className="flex items-center justify-between p-2 bg-background rounded">
                  <span>Book Job:</span>
                  <code className="text-primary">/api/v1/vapi/book-job</code>
                </div>
                <div className="flex items-center justify-between p-2 bg-background rounded">
                  <span>Send SMS:</span>
                  <code className="text-primary">/api/v1/vapi/send-sms</code>
                </div>
                <div className="flex items-center justify-between p-2 bg-background rounded">
                  <span>Call Summary:</span>
                  <code className="text-primary">/api/v1/vapi/call-summary</code>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button onClick={handleSave} className="btn-industrial" data-testid="save-settings">
            SAVE CHANGES
          </Button>
        </div>
      </div>
    </Layout>
  );
}
