import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { Toaster } from "../ui/sonner";

export function Layout({ children, title, subtitle }) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="ml-64 min-h-screen transition-all duration-300">
        <Header title={title} subtitle={subtitle} />
        <div className="p-6">
          {children}
        </div>
      </main>
      <Toaster position="top-right" richColors />
    </div>
  );
}
