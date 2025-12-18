import { useState, useEffect } from "react";
import { Layout } from "../../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Textarea } from "../../components/ui/textarea";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { customerAPI, propertyAPI

 } from "../../lib/api";
import { toast } from "sonner";
import { 
  Plus, Search, User, MapPin, Phone, Mail, Home, Edit, 
  Save, X, MessageSquare, Calendar, ChevronRight, FileText, Trash2
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";

export default function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCustomerDetailDialog, setShowCustomerDetailDialog] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchCustomers();
    // Polling for real-time updates
    const interval = setInterval(fetchCustomers, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await customerAPI.list();
      // Fetch properties for each customer
      const customersWithProps = await Promise.all(
        response.data.map(async (customer) => {
          try {
            const propsResponse = await propertyAPI.list(customer.id);
            return { ...customer, properties: propsResponse.data };
          } catch {
            return { ...customer, properties: [] };
          }
        })
      );
      setCustomers(customersWithProps);
    } catch (error) {
      toast.error("Failed to load customers");
    } finally {
      setLoading(false);
    }
  };

  const handleCustomerClick = (customer) => {
    setSelectedCustomer(customer);
    setShowCustomerDetailDialog(true);
  };

  const handleSelectCustomer = (customerId, checked) => {
    if (checked) {
      setSelectedIds([...selectedIds, customerId]);
    } else {
      setSelectedIds(selectedIds.filter(id => id !== customerId));
    }
  };

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedIds(filteredCustomers.map(c => c.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedIds.length} customer(s)? This will also delete all their leads, jobs, properties, and conversations.`)) return;
    
    setDeleting(true);
    try {
      await customerAPI.bulkDelete(selectedIds);
      toast.success(`${selectedIds.length} customer(s) deleted`);
      setSelectedIds([]);
      fetchCustomers();
    } catch (error) {
      toast.error("Failed to delete customers");
    } finally {
      setDeleting(false);
    }
  };

  const filteredCustomers = customers.filter((customer) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    const propertyMatch = customer.properties?.some(p => 
      p.address_line1?.toLowerCase().includes(searchLower) ||
      p.city?.toLowerCase().includes(searchLower)
    );
    return (
      customer.first_name?.toLowerCase().includes(searchLower) ||
      customer.last_name?.toLowerCase().includes(searchLower) ||
      customer.email?.toLowerCase().includes(searchLower) ||
      customer.phone?.includes(search) ||
      propertyMatch
    );
  });

  return (
    <Layout title="Customers" subtitle="Manage your customer database">
      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search customers, addresses..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="customers-search"
          />
        </div>

        <CreateCustomerDialog 
          open={showCreateDialog} 
          onOpenChange={setShowCreateDialog}
          onSuccess={fetchCustomers}
        />
      </div>

      {/* Bulk Actions */}
      {selectedIds.length > 0 && (
        <div className="flex items-center gap-4 mb-4 p-3 bg-muted rounded-lg">
          <input
            type="checkbox"
            checked={selectedIds.length === filteredCustomers.length && filteredCustomers.length > 0}
            onChange={(e) => handleSelectAll(e.target.checked)}
            className="h-4 w-4"
          />
          <span className="text-sm font-medium">{selectedIds.length} selected</span>
          <Button 
            variant="destructive" 
            size="sm" 
            onClick={handleBulkDelete}
            disabled={deleting}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            {deleting ? "Deleting..." : "Delete Selected"}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setSelectedIds([])}>
            Clear Selection
          </Button>
        </div>
      )}

      {/* Customers Table */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : filteredCustomers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No customers found</p>
            <Button 
              className="mt-4" 
              onClick={() => setShowCreateDialog(true)}
              data-testid="create-first-customer"
            >
              Add your first customer
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table data-testid="customers-table">
            <TableHeader>
              <TableRow className="table-industrial">
                <TableHead className="w-10">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === filteredCustomers.length && filteredCustomers.length > 0}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="h-4 w-4"
                  />
                </TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Property Address</TableHead>
                <TableHead>Preferred Channel</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCustomers.map((customer) => (
                <TableRow 
                  key={customer.id} 
                  className={`table-industrial cursor-pointer hover:bg-muted/50 ${selectedIds.includes(customer.id) ? 'bg-primary/5' : ''}`}
                  data-testid={`customer-row-${customer.id}`}
                  onClick={() => handleCustomerClick(customer)}
                >
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(customer.id)}
                      onChange={(e) => handleSelectCustomer(customer.id, e.target.checked)}
                      className="h-4 w-4"
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                        <User className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">
                          {customer.first_name} {customer.last_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          ID: <span className="font-mono">{customer.id.slice(0, 8)}</span>
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="font-mono">{customer.phone}</span>
                      </div>
                      {customer.email && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Mail className="h-3.5 w-3.5" />
                          <span>{customer.email}</span>
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {customer.properties?.length > 0 ? (
                      <div className="flex items-start gap-2">
                        <MapPin className="h-3.5 w-3.5 text-muted-foreground mt-0.5" />
                        <div className="text-sm">
                          <p>{customer.properties[0].address_line1}</p>
                          <p className="text-muted-foreground">
                            {customer.properties[0].city}, {customer.properties[0].state}
                          </p>
                          {customer.properties.length > 1 && (
                            <span className="text-xs text-primary">
                              +{customer.properties.length - 1} more
                            </span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-sm">No properties</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {customer.preferred_channel}
                    </Badge>
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Button 
                      size="sm" 
                      variant="ghost"
                      onClick={() => handleCustomerClick(customer)}
                    >
                      <Edit className="h-3.5 w-3.5 mr-1" />
                      View/Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Customer Detail Dialog */}
      <CustomerDetailDialog
        open={showCustomerDetailDialog}
        onOpenChange={setShowCustomerDetailDialog}
        customer={selectedCustomer}
        onUpdate={fetchCustomers}
      />
    </Layout>
  );
}

function CustomerDetailDialog({ open, onOpenChange, customer, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [newNote, setNewNote] = useState("");
  const [properties, setProperties] = useState([]);
  const [showAddProperty, setShowAddProperty] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (customer) {
      setFormData({
        first_name: customer.first_name || "",
        last_name: customer.last_name || "",
        phone: customer.phone || "",
        email: customer.email || "",
        preferred_channel: customer.preferred_channel || "SMS",
        notes: customer.notes || "",
      });
      setProperties(customer.properties || []);
    }
  }, [customer]);

  const handleSave = async () => {
    if (!customer) return;
    setLoading(true);
    try {
      // Send null for empty email to pass validation
      const updateData = {
        ...formData,
        email: formData.email?.trim() || null,
      };
      await customerAPI.update(customer.id, updateData);
      toast.success("Customer updated!");
      setEditing(false);
      onUpdate();
    } catch (error) {
      console.error("Customer update error:", error);
      toast.error(error.response?.data?.detail?.[0]?.msg || "Failed to update customer");
    } finally {
      setLoading(false);
    }
  };

  const handleAddNote = async () => {
    if (!customer || !newNote.trim()) return;
    
    const existingNotes = formData.notes || "";
    const timestamp = new Date().toLocaleString();
    const updatedNotes = existingNotes 
      ? `${existingNotes}\n\n[${timestamp}]\n${newNote}`
      : `[${timestamp}]\n${newNote}`;
    
    setLoading(true);
    try {
      const updateData = {
        ...formData,
        notes: updatedNotes,
        email: formData.email?.trim() || null,
      };
      await customerAPI.update(customer.id, updateData);
      setFormData({ ...formData, notes: updatedNotes });
      setNewNote("");
      toast.success("Note added!");
      onUpdate();
    } catch (error) {
      console.error("Note add error:", error);
      toast.error("Failed to add note");
    } finally {
      setLoading(false);
    }
  };

  if (!customer) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading text-xl flex items-center gap-2">
            <User className="h-5 w-5" />
            {editing ? "Edit Customer" : "Customer Details"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Basic Info */}
          <div className="bg-muted/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium">Contact Information</h4>
              {!editing && (
                <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
                  <Edit className="h-4 w-4 mr-1" />
                  Edit
                </Button>
              )}
            </div>
            
            {editing ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>First Name</Label>
                  <Input
                    value={formData.first_name}
                    onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Last Name</Label>
                  <Input
                    value={formData.last_name}
                    onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                  />
                </div>
                <div className="space-y-2 col-span-2">
                  <Label>Preferred Channel</Label>
                  <Select 
                    value={formData.preferred_channel} 
                    onValueChange={(v) => setFormData({...formData, preferred_channel: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="SMS">SMS</SelectItem>
                      <SelectItem value="CALL">Call</SelectItem>
                      <SelectItem value="EMAIL">Email</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-2 flex gap-2 mt-2">
                  <Button onClick={handleSave} disabled={loading}>
                    <Save className="h-4 w-4 mr-1" />
                    Save Changes
                  </Button>
                  <Button variant="outline" onClick={() => setEditing(false)}>
                    <X className="h-4 w-4 mr-1" />
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Name:</span>
                  <p className="font-medium">{customer.first_name} {customer.last_name}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Phone:</span>
                  <p className="font-medium flex items-center gap-1">
                    <Phone className="h-3 w-3" />
                    {customer.phone}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Email:</span>
                  <p className="font-medium flex items-center gap-1">
                    <Mail className="h-3 w-3" />
                    {customer.email || "Not provided"}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Preferred Channel:</span>
                  <p><Badge variant="outline">{customer.preferred_channel}</Badge></p>
                </div>
              </div>
            )}
          </div>

          {/* Properties */}
          <div className="bg-muted/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium flex items-center gap-2">
                <Home className="h-4 w-4" />
                Properties ({properties.length})
              </h4>
              <Button variant="outline" size="sm" onClick={() => setShowAddProperty(true)}>
                <Plus className="h-4 w-4 mr-1" />
                Add Property
              </Button>
            </div>
            
            {properties.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No properties on file
              </p>
            ) : (
              <div className="space-y-3">
                {properties.map((prop, idx) => (
                  <PropertyCard 
                    key={prop.id || idx} 
                    property={prop}
                    onUpdate={() => {
                      propertyAPI.list(customer.id).then(res => setProperties(res.data));
                    }}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Notes */}
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="font-medium flex items-center gap-2 mb-3">
              <FileText className="h-4 w-4" />
              Notes
            </h4>
            
            {formData.notes && (
              <div className="bg-background rounded-lg p-3 border mb-4 text-sm whitespace-pre-wrap max-h-[200px] overflow-y-auto">
                {formData.notes}
              </div>
            )}
            
            <div className="flex gap-2">
              <Textarea
                placeholder="Add a note..."
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                rows={2}
                className="flex-1"
              />
              <Button onClick={handleAddNote} disabled={loading || !newNote.trim()}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>

        {/* Add Property Sub-Dialog */}
        <AddPropertyDialog
          open={showAddProperty}
          onOpenChange={setShowAddProperty}
          customer={customer}
          onSuccess={() => {
            setShowAddProperty(false);
            // Refresh properties
            propertyAPI.list(customer.id).then(res => setProperties(res.data));
            toast.success("Property added!");
          }}
        />
      </DialogContent>
    </Dialog>
  );
}

function CreateCustomerDialog({ open, onOpenChange, onSuccess }) {
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    preferred_channel: "SMS",
    notes: "",
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await customerAPI.create(formData);
      toast.success("Customer created successfully");
      onOpenChange(false);
      setFormData({
        first_name: "",
        last_name: "",
        phone: "",
        email: "",
        preferred_channel: "SMS",
        notes: "",
      });
      onSuccess();
    } catch (error) {
      toast.error("Failed to create customer");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="btn-industrial" data-testid="create-customer-button">
          <Plus className="h-4 w-4 mr-2" />
          NEW CUSTOMER
        </Button>
      </DialogTrigger>
      <DialogContent data-testid="create-customer-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">Add New Customer</DialogTitle>
          <DialogDescription>
            Add a customer to your database
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name *</Label>
                <Input
                  id="first_name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name *</Label>
                <Input
                  id="last_name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                  required
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="phone">Phone *</Label>
              <Input
                id="phone"
                type="tel"
                placeholder="+1 (555) 123-4567"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Preferred Channel</Label>
              <Select 
                value={formData.preferred_channel} 
                onValueChange={(v) => setFormData({...formData, preferred_channel: v})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="SMS">SMS</SelectItem>
                  <SelectItem value="CALL">Call</SelectItem>
                  <SelectItem value="EMAIL">Email</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Creating..." : "Add Customer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function AddPropertyDialog({ open, onOpenChange, customer, onSuccess }) {
  const [formData, setFormData] = useState({
    address_line1: "",
    address_line2: "",
    city: "",
    state: "",
    postal_code: "",
    property_type: "RESIDENTIAL",
    system_type: "",
    notes: "",
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!customer) return;
    
    setLoading(true);
    try {
      await propertyAPI.create({
        customer_id: customer.id,
        ...formData,
      });
      onOpenChange(false);
      setFormData({
        address_line1: "",
        address_line2: "",
        city: "",
        state: "",
        postal_code: "",
        property_type: "RESIDENTIAL",
        system_type: "",
        notes: "",
      });
      onSuccess();
    } catch (error) {
      toast.error("Failed to add property");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Property</DialogTitle>
          <DialogDescription>
            Add a service location for {customer?.first_name} {customer?.last_name}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Address Line 1 *</Label>
              <Input
                placeholder="123 Main St"
                value={formData.address_line1}
                onChange={(e) => setFormData({...formData, address_line1: e.target.value})}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label>Address Line 2</Label>
              <Input
                placeholder="Apt 4B"
                value={formData.address_line2}
                onChange={(e) => setFormData({...formData, address_line2: e.target.value})}
              />
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>City *</Label>
                <Input
                  value={formData.city}
                  onChange={(e) => setFormData({...formData, city: e.target.value})}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>State *</Label>
                <Input
                  value={formData.state}
                  onChange={(e) => setFormData({...formData, state: e.target.value})}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>ZIP *</Label>
                <Input
                  value={formData.postal_code}
                  onChange={(e) => setFormData({...formData, postal_code: e.target.value})}
                  required
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Property Type</Label>
                <Select 
                  value={formData.property_type} 
                  onValueChange={(v) => setFormData({...formData, property_type: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="RESIDENTIAL">Residential</SelectItem>
                    <SelectItem value="COMMERCIAL">Commercial</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>System Type</Label>
                <Input
                  placeholder="e.g., Gas Furnace + AC"
                  value={formData.system_type}
                  onChange={(e) => setFormData({...formData, system_type: e.target.value})}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Adding..." : "Add Property"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function PropertyCard({ property, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    address_line1: property.address_line1 || "",
    address_line2: property.address_line2 || "",
    city: property.city || "",
    state: property.state || "",
    postal_code: property.postal_code || "",
    property_type: property.property_type || "RESIDENTIAL",
    system_type: property.system_type || "",
    notes: property.notes || "",
  });
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      await propertyAPI.update(property.id, {
        customer_id: property.customer_id,
        ...formData,
      });
      toast.success("Property updated!");
      setEditing(false);
      onUpdate();
    } catch (error) {
      toast.error("Failed to update property");
    } finally {
      setLoading(false);
    }
  };

  if (editing) {
    return (
      <div className="bg-background rounded-lg p-4 border space-y-3">
        <div className="flex items-center justify-between">
          <h5 className="font-medium text-sm">Edit Property</h5>
          <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        <div className="space-y-3">
          <div className="space-y-1">
            <Label className="text-xs">Address Line 1</Label>
            <Input
              value={formData.address_line1}
              onChange={(e) => setFormData({...formData, address_line1: e.target.value})}
              placeholder="123 Main St"
            />
          </div>
          
          <div className="space-y-1">
            <Label className="text-xs">Address Line 2</Label>
            <Input
              value={formData.address_line2}
              onChange={(e) => setFormData({...formData, address_line2: e.target.value})}
              placeholder="Apt 4B"
            />
          </div>
          
          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1">
              <Label className="text-xs">City</Label>
              <Input
                value={formData.city}
                onChange={(e) => setFormData({...formData, city: e.target.value})}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">State</Label>
              <Input
                value={formData.state}
                onChange={(e) => setFormData({...formData, state: e.target.value})}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">ZIP</Label>
              <Input
                value={formData.postal_code}
                onChange={(e) => setFormData({...formData, postal_code: e.target.value})}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-xs">Property Type</Label>
              <Select 
                value={formData.property_type} 
                onValueChange={(v) => setFormData({...formData, property_type: v})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="RESIDENTIAL">Residential</SelectItem>
                  <SelectItem value="COMMERCIAL">Commercial</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">System Type</Label>
              <Input
                value={formData.system_type}
                onChange={(e) => setFormData({...formData, system_type: e.target.value})}
                placeholder="e.g., Gas Furnace + AC"
              />
            </div>
          </div>
          
          <div className="flex gap-2 pt-2">
            <Button size="sm" onClick={handleSave} disabled={loading}>
              <Save className="h-3 w-3 mr-1" />
              {loading ? "Saving..." : "Save"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-background rounded-lg p-3 border">
      <div className="flex items-start gap-2">
        <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
        <div className="flex-1">
          <p className="font-medium">{property.address_line1}</p>
          {property.address_line2 && <p className="text-sm text-muted-foreground">{property.address_line2}</p>}
          <p className="text-sm text-muted-foreground">
            {property.city}, {property.state} {property.postal_code}
          </p>
          <div className="flex gap-2 mt-2">
            <Badge variant="outline">{property.property_type}</Badge>
            {property.system_type && <Badge variant="secondary">{property.system_type}</Badge>}
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
          <Edit className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

