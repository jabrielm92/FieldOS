import { Bell, Search, Sun, Moon, Menu, X, ExternalLink, Briefcase, Users, FileText, LogOut } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { useState, useEffect, useRef } from "react";
import { useNavigate, NavLink } from "react-router-dom";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { dashboardAPI } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { tenantNavItems, adminNavItems } from "./Sidebar";
import { cn } from "../../lib/utils";

const searchRoutes = [
  { label: "Dashboard", path: "/dashboard", keywords: ["home", "overview", "stats"] },
  { label: "Jobs", path: "/jobs", keywords: ["work", "appointments", "schedule"] },
  { label: "Customers", path: "/customers", keywords: ["clients", "contacts", "people"] },
  { label: "Leads", path: "/leads", keywords: ["prospects", "opportunities", "calls"] },
  { label: "Quotes", path: "/quotes", keywords: ["estimates", "pricing", "proposals"] },
  { label: "Inbox", path: "/conversations", keywords: ["messages", "sms", "chat"] },
  { label: "Settings", path: "/settings", keywords: ["config", "preferences", "company"] },
  { label: "Reports", path: "/reports", keywords: ["analytics", "revenue", "metrics"] },
];

export function Header({ title, subtitle }) {
  const [isDark, setIsDark] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [search, setSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const searchRef = useRef(null);
  const navigate = useNavigate();
  const { user, logout, isSuperAdmin } = useAuth();

  const navItems = isSuperAdmin ? adminNavItems : tenantNavItems;

  useEffect(() => {
    const stored = localStorage.getItem("fieldos_theme");
    if (stored === "dark") {
      setIsDark(true);
      document.documentElement.classList.add("dark");
    }
    fetchNotifications();
  }, []);

  useEffect(() => {
    if (search.trim()) {
      const query = search.toLowerCase();
      const results = searchRoutes.filter(r => 
        r.label.toLowerCase().includes(query) || 
        r.keywords.some(k => k.includes(query))
      );
      setSearchResults(results);
      setShowSearch(true);
    } else {
      setSearchResults([]);
      setShowSearch(false);
    }
  }, [search]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowSearch(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fetchNotifications = async () => {
    try {
      const res = await dashboardAPI.getMetrics();
      const metrics = res.data.metrics || {};
      const notifs = [];
      
      if (metrics.leads_this_week > 0) {
        notifs.push({ id: 1, type: "lead", title: "New Leads", message: `${metrics.leads_this_week} new leads this week`, link: "/leads", icon: Users });
      }
      if (metrics.jobs_this_week > 0) {
        notifs.push({ id: 2, type: "job", title: "Jobs Scheduled", message: `${metrics.jobs_this_week} jobs this week`, link: "/jobs", icon: Briefcase });
      }
      if (metrics.potential_revenue > 0) {
        notifs.push({ id: 3, type: "revenue", title: "Potential Revenue", message: `$${metrics.potential_revenue.toLocaleString()} pending`, link: "/quotes", icon: FileText });
      }
      
      setNotifications(notifs);
      setUnreadCount(notifs.length);
    } catch (error) {
      console.error("Failed to fetch notifications");
    }
  };

  const toggleTheme = () => {
    setIsDark(!isDark);
    if (isDark) {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("fieldos_theme", "light");
    } else {
      document.documentElement.classList.add("dark");
      localStorage.setItem("fieldos_theme", "dark");
    }
  };

  const handleSearchSelect = (path) => {
    navigate(path);
    setSearch("");
    setShowSearch(false);
  };

  const handleNotificationClick = (link) => {
    navigate(link);
    setShowNotifications(false);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
    setShowMobileMenu(false);
  };

  const handleMobileNavClick = (path) => {
    navigate(path);
    setShowMobileMenu(false);
  };

  return (
    <>
      <header className="h-16 glass-header sticky top-0 z-40 flex items-center justify-between px-4 md:px-6">
        {/* Mobile: Menu button + Title */}
        <div className="flex items-center gap-3">
          {/* Mobile menu button */}
          <Button 
            variant="ghost" 
            size="icon"
            className="md:hidden"
            onClick={() => setShowMobileMenu(true)}
            data-testid="mobile-menu-button"
          >
            <Menu className="h-5 w-5" />
          </Button>
          
          <div>
            <h1 className="font-heading text-lg md:text-xl font-bold tracking-tight">{title}</h1>
            {subtitle && (
              <p className="text-xs md:text-sm text-muted-foreground hidden sm:block">{subtitle}</p>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2 md:gap-3">
          {/* Search - hidden on mobile */}
          <div className="relative hidden lg:block" ref={searchRef}>
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Search pages..." 
              className="pl-9 w-48 xl:w-64 bg-background"
              data-testid="header-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onFocus={() => search && setShowSearch(true)}
            />
            {showSearch && searchResults.length > 0 && (
              <div className="absolute top-full mt-1 w-full bg-background border rounded-md shadow-lg z-50">
                {searchResults.map((result) => (
                  <button
                    key={result.path}
                    className="w-full px-4 py-2 text-left hover:bg-muted flex items-center gap-2 text-sm"
                    onClick={() => handleSearchSelect(result.path)}
                  >
                    <ExternalLink className="h-4 w-4 text-muted-foreground" />
                    {result.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          
          <Button 
            variant="ghost" 
            size="icon"
            onClick={toggleTheme}
            data-testid="theme-toggle"
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
          
          {/* Notifications button with badge */}
          <Button 
            variant="ghost" 
            size="icon" 
            className="relative"
            onClick={() => setShowNotifications(true)}
            data-testid="notifications-button"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 h-4 w-4 md:h-5 md:w-5 bg-red-500 text-white text-[10px] md:text-xs rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </Button>
        </div>
      </header>

      {/* Mobile Navigation Menu */}
      <Dialog open={showMobileMenu} onOpenChange={setShowMobileMenu}>
        <DialogContent className="sm:max-w-sm h-[85vh] flex flex-col p-0">
          <DialogHeader className="p-4 border-b">
            <DialogTitle className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary rounded-md flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-sm">FO</span>
              </div>
              FieldOS
            </DialogTitle>
          </DialogHeader>
          
          {/* Nav items */}
          <nav className="flex-1 overflow-y-auto p-2">
            {navItems.map((item) => (
              <button
                key={item.to}
                onClick={() => handleMobileNavClick(item.to)}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors",
                  "hover:bg-muted active:bg-muted/80"
                )}
              >
                <item.icon className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </nav>
          
          {/* User section */}
          <div className="p-4 border-t">
            <div className="mb-3 px-2">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Notifications Modal */}
      <Dialog open={showNotifications} onOpenChange={setShowNotifications}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No new notifications</p>
            ) : (
              notifications.map((notif) => (
                <button
                  key={notif.id}
                  className="w-full p-3 border rounded-lg hover:bg-muted text-left flex items-start gap-3 transition-colors"
                  onClick={() => handleNotificationClick(notif.link)}
                >
                  <div className="p-2 bg-primary/10 rounded-full">
                    <notif.icon className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{notif.title}</p>
                    <p className="text-xs text-muted-foreground">{notif.message}</p>
                  </div>
                  <ExternalLink className="h-4 w-4 text-muted-foreground" />
                </button>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
