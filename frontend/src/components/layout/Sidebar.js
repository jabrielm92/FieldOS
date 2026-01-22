import { cn } from "../../lib/utils";
import { 
  LayoutDashboard, 
  Users, 
  Briefcase, 
  MessageSquare, 
  FileText, 
  Settings,
  Building2,
  Wrench,
  TrendingUp,
  Megaphone,
  LogOut,
  ChevronLeft,
  Truck,
  BarChart3,
  Calendar
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { Button } from "../ui/button";
import { useState } from "react";

export const tenantNavItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/leads", icon: TrendingUp, label: "Leads" },
  { to: "/jobs", icon: Briefcase, label: "Jobs" },
  { to: "/calendar", icon: Calendar, label: "Calendar" },
  { to: "/dispatch", icon: Truck, label: "Dispatch" },
  { to: "/conversations", icon: MessageSquare, label: "Inbox" },
  { to: "/customers", icon: Users, label: "Customers" },
  { to: "/technicians", icon: Wrench, label: "Technicians" },
  { to: "/quotes", icon: FileText, label: "Quotes" },
  { to: "/campaigns", icon: Megaphone, label: "Campaigns" },
  { to: "/reports", icon: BarChart3, label: "Reports" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export const adminNavItems = [
  { to: "/admin", icon: LayoutDashboard, label: "Overview" },
  { to: "/admin/tenants", icon: Building2, label: "Tenants" },
];

export function Sidebar() {
  const { user, logout, isSuperAdmin } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = isSuperAdmin ? adminNavItems : tenantNavItems;

  return (
    <aside 
      className={cn(
        "fixed left-0 top-0 h-full bg-card border-r border-border flex-col transition-all duration-300 z-50 hidden md:flex",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">FO</span>
            </div>
            <span className="font-heading font-bold text-lg tracking-tight">FieldOS</span>
          </div>
        )}
        <Button 
          variant="ghost" 
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
          className="h-8 w-8"
          data-testid="sidebar-toggle"
        >
          <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "sidebar-link",
                isActive && "active",
                collapsed && "justify-center px-2"
              )
            }
            data-testid={`nav-${item.label.toLowerCase()}`}
          >
            <item.icon className="h-5 w-5 flex-shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="p-3 border-t border-border">
        {!collapsed && (
          <div className="mb-3 px-3">
            <p className="text-sm font-medium truncate">{user?.name}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
          </div>
        )}
        <Button
          variant="ghost"
          className={cn("w-full", collapsed ? "justify-center px-2" : "justify-start")}
          onClick={handleLogout}
          data-testid="logout-button"
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && <span className="ml-2">Logout</span>}
        </Button>
      </div>
    </aside>
  );
}
