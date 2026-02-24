import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import { Badge } from "../../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { settingsAPI } from "../../lib/api";
import { toast } from "sonner";
import { Zap, Clock, MessageSquare, Star, CreditCard, Bell, Save, Plus, Trash2, ArrowRight } from "lucide-react";

const WORKFLOW_TEMPLATES = [
  { id: "review_request", name: "Auto Review Request", icon: Star, description: "Send review request X days after job completion", trigger: "job_completed", action: "send_review_sms", configKey: "auto_review_request_days", default: 3 },
  { id: "payment_reminder", name: "Payment Reminder", icon: CreditCard, description: "Send payment reminder X days after invoice due", trigger: "invoice_overdue", action: "send_payment_sms", configKey: "auto_payment_reminder_days", default: 7 },
  { id: "appointment_reminder", name: "Appointment Reminder", icon: Bell, description: "Send reminder day before scheduled job", trigger: "job_day_before", action: "send_reminder_sms", configKey: "reminder_day_before_enabled", default: true },
  { id: "morning_reminder", name: "Morning-Of Reminder", icon: Clock, description: "Send reminder morning of scheduled job", trigger: "job_morning_of", action: "send_reminder_sms", configKey: "reminder_morning_of_enabled", default: true },
];

export default function WorkflowBuilderPage() {
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [workflows, setWorkflows] = useState({});

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await settingsAPI.getTenantSettings();
        setTenant(res.data);
        // Initialize workflow states from tenant settings
        const wf = {};
        WORKFLOW_TEMPLATES.forEach(t => {
          const val = res.data[t.configKey];
          wf[t.id] = { enabled: val !== 0 && val !== false, value: typeof val === 'number' ? val : (val ? 1 : 0) };
        });
        setWorkflows(wf);
      } catch (e) { toast.error("Failed to load settings"); }
      finally { setLoading(false); }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updates = {};
      WORKFLOW_TEMPLATES.forEach(t => {
        const wf = workflows[t.id];
        if (typeof t.default === 'boolean') {
          updates[t.configKey] = wf?.enabled ?? t.default;
        } else {
          updates[t.configKey] = wf?.enabled ? (wf.value || t.default) : 0;
        }
      });
      await settingsAPI.updateTenantSettings(updates);
      toast.success("Workflows saved");
    } catch (e) { toast.error("Failed to save"); }
    finally { setSaving(false); }
  };

  const updateWorkflow = (id, field, value) => {
    setWorkflows(prev => ({ ...prev, [id]: { ...prev[id], [field]: value } }));
  };

  if (loading) return <Layout title="Workflows"><div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div></Layout>;

  return (
    <Layout title="Workflow Automation" subtitle="Configure automated actions and notifications">
      <div className="max-w-4xl">
        {/* Active Workflows */}
        <div className="space-y-4 mb-8">
          {WORKFLOW_TEMPLATES.map(template => {
            const wf = workflows[template.id] || { enabled: false, value: template.default };
            const Icon = template.icon;
            return (
              <Card key={template.id} className={wf.enabled ? "border-primary/50" : ""}>
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-lg ${wf.enabled ? 'bg-primary/10' : 'bg-muted'}`}>
                      <Icon className={`h-6 w-6 ${wf.enabled ? 'text-primary' : 'text-muted-foreground'}`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <h3 className="font-semibold flex items-center gap-2">
                            {template.name}
                            {wf.enabled && <Badge className="bg-green-100 text-green-800">Active</Badge>}
                          </h3>
                          <p className="text-sm text-muted-foreground">{template.description}</p>
                        </div>
                        <Switch checked={wf.enabled} onCheckedChange={v => updateWorkflow(template.id, 'enabled', v)} />
                      </div>
                      
                      {wf.enabled && typeof template.default === 'number' && (
                        <div className="mt-4 p-4 bg-muted/50 rounded-lg">
                          <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 text-sm">
                              <Badge variant="outline">{template.trigger.replace(/_/g, ' ')}</Badge>
                              <ArrowRight className="h-4 w-4 text-muted-foreground" />
                              <span>Wait</span>
                              <Input type="number" min="1" max="30" value={wf.value} onChange={e => updateWorkflow(template.id, 'value', parseInt(e.target.value) || 1)} className="w-16 h-8" />
                              <span>days</span>
                              <ArrowRight className="h-4 w-4 text-muted-foreground" />
                              <Badge variant="outline">{template.action.replace(/_/g, ' ')}</Badge>
                            </div>
                          </div>
                        </div>
                      )}

                      {wf.enabled && typeof template.default === 'boolean' && (
                        <div className="mt-4 p-4 bg-muted/50 rounded-lg">
                          <div className="flex items-center gap-2 text-sm">
                            <Badge variant="outline">{template.trigger.replace(/_/g, ' ')}</Badge>
                            <ArrowRight className="h-4 w-4 text-muted-foreground" />
                            <Badge variant="outline">{template.action.replace(/_/g, ' ')}</Badge>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={saving} className="btn-industrial">
            <Save className="h-4 w-4 mr-2" />
            {saving ? "SAVING..." : "SAVE WORKFLOWS"}
          </Button>
        </div>

        {/* Info Card */}
        <Card className="mt-8 bg-muted/30">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2"><Zap className="h-5 w-5" />How Workflows Work</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p><strong>Auto Review Request:</strong> Automatically sends a review request SMS to customers X days after their job is marked complete.</p>
            <p><strong>Payment Reminder:</strong> Sends payment reminder SMS for invoices that are X days past due date.</p>
            <p><strong>Appointment Reminders:</strong> Sends SMS reminders to customers the day before and morning of their scheduled service.</p>
            <p className="pt-2 text-xs">Workflows run automatically via background scheduler. Changes take effect immediately after saving.</p>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
