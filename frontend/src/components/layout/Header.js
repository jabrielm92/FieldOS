import { Bell, Search, Sun, Moon } from "lucide-react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { useState, useEffect } from "react";

export function Header({ title, subtitle }) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("fieldos_theme");
    if (stored === "dark") {
      setIsDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

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

  return (
    <header className="h-16 glass-header sticky top-0 z-40 flex items-center justify-between px-6">
      <div>
        <h1 className="font-heading text-xl font-bold tracking-tight">{title}</h1>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      
      <div className="flex items-center gap-3">
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search..." 
            className="pl-9 w-64 bg-background"
            data-testid="header-search"
          />
        </div>
        
        <Button 
          variant="ghost" 
          size="icon"
          onClick={toggleTheme}
          data-testid="theme-toggle"
        >
          {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
        
        <Button variant="ghost" size="icon" data-testid="notifications-button">
          <Bell className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
