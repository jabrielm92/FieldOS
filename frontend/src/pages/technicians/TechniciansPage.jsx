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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { technicianAPI } from "../../lib/api";
import { toast } from "sonner";
import { Plus, Search, User, Phone, Mail, Wrench, Check, X } from "lucide-react";

export default function TechniciansPage() {
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  useEffect(() => {
    fetchTechnicians();
  }, []);

  const fetchTechnicians = async () => {
    try {
      const response = await technicianAPI.list();
      setTechnicians(response.data);
    } catch (error) {
      toast.error("Failed to load technicians");
    } finally {
      setLoading(false);
    }
  };

  const filteredTechnicians = technicians.filter((tech) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      tech.name?.toLowerCase().includes(searchLower) ||
      tech.email?.toLowerCase().includes(searchLower) ||
      tech.phone?.includes(search)
    );
  });

  return (
    <Layout title="Technicians" subtitle="Manage your service team">
      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search technicians..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="technicians-search"
          />
        </div>

        <CreateTechnicianDialog 
          open={showCreateDialog} 
          onOpenChange={setShowCreateDialog}
          onSuccess={fetchTechnicians}
        />
      </div>

      {/* Technicians Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filteredTechnicians.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No technicians found</p>
            <Button 
              className="mt-4" 
              onClick={() => setShowCreateDialog(true)}
              data-testid="create-first-tech"
            >
              Add your first technician
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTechnicians.map((tech) => (
            <TechnicianCard key={tech.id} technician={tech} />
          ))}
        </div>
      )}
    </Layout>
  );
}

function TechnicianCard({ technician }) {
  return (
    <Card className="card-industrial" data-testid={`tech-card-${technician.id}`}>
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-accent/10 rounded-full flex items-center justify-center">
            <Wrench className="h-6 w-6 text-accent" />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium">{technician.name}</h3>
              <Badge variant={technician.active ? "default" : "secondary"}>
                {technician.active ? (
                  <><Check className="h-3 w-3 mr-1" /> Active</>
                ) : (
                  <><X className="h-3 w-3 mr-1" /> Inactive</>
                )}
              </Badge>
            </div>
            
            <div className="space-y-1 text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Phone className="h-3.5 w-3.5" />
                <span className="font-mono">{technician.phone}</span>
              </div>
              {technician.email && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Mail className="h-3.5 w-3.5" />
                  <span>{technician.email}</span>
                </div>
              )}
            </div>
            
            {technician.skills?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                {technician.skills.map((skill, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {skill}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CreateTechnicianDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    email: "",
    active: true,
    skills: [],
  });
  const [skillInput, setSkillInput] = useState("");
  const [loading, setLoading] = useState(false);

  const addSkill = () => {
    if (skillInput.trim() && !formData.skills.includes(skillInput.trim())) {
      setFormData({
        ...formData,
        skills: [...formData.skills, skillInput.trim()]
      });
      setSkillInput("");
    }
  };

  const removeSkill = (skill) => {
    setFormData({
      ...formData,
      skills: formData.skills.filter(s => s !== skill)
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await technicianAPI.create(formData);
      toast.success("Technician added successfully");
      onOpenChange(false);
      setFormData({
        name: "",
        phone: "",
        email: "",
        active: true,
        skills: [],
      });
      onSuccess();
    } catch (error) {
      toast.error("Failed to add technician");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="btn-industrial" data-testid="create-tech-button">
          <Plus className="h-4 w-4 mr-2" />
          NEW TECHNICIAN
        </Button>
      </DialogTrigger>
      <DialogContent data-testid="create-tech-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Add Technician</DialogTitle>
          <DialogDescription>
            Add a new technician to your team
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
                data-testid="tech-name"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="phone">Phone *</Label>
              <Input
                id="phone"
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                required
                data-testid="tech-phone"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                data-testid="tech-email"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Skills</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g., HVAC, Plumbing"
                  value={skillInput}
                  onChange={(e) => setSkillInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
                />
                <Button type="button" variant="outline" onClick={addSkill}>
                  Add
                </Button>
              </div>
              {formData.skills.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {formData.skills.map((skill, i) => (
                    <Badge key={i} variant="secondary" className="cursor-pointer" onClick={() => removeSkill(skill)}>
                      {skill} ×
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading} data-testid="submit-tech">
              {loading ? "Adding..." : "Add Technician"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
