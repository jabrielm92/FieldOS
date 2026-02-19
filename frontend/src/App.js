import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { BrandingProvider } from "./contexts/BrandingContext";
import { Toaster } from "./components/ui/sonner";

// Pages
import LandingPage from "./pages/landing/LandingPage";
import LoginPage from "./pages/auth/LoginPage";
import PrivacyPage from "./pages/legal/PrivacyPage";
import TermsPage from "./pages/legal/TermsPage";
import DashboardPage from "./pages/dashboard/DashboardPage";
import LeadsPage from "./pages/leads/LeadsPage";
import JobsPage from "./pages/jobs/JobsPage";
import ConversationsPage from "./pages/conversations/ConversationsPage";
import CustomersPage from "./pages/customers/CustomersPage";
import TechniciansPage from "./pages/technicians/TechniciansPage";
import QuotesPage from "./pages/quotes/QuotesPage";
import CampaignsPage from "./pages/campaigns/CampaignsPage";
import SettingsPage from "./pages/settings/SettingsPage";
import WorkflowBuilderPage from "./pages/settings/WorkflowBuilderPage";
import AdminTenantsPage from "./pages/admin/AdminTenantsPage";
import DispatchBoard from "./pages/dispatch/DispatchBoard";
import ReportsPage from "./pages/reports/ReportsPage";
import RevenueReportsPage from "./pages/reports/RevenueReportsPage";
import CustomerPortal from "./pages/portal/CustomerPortal";
import CalendarPage from "./pages/calendar/CalendarPage";
import TrackingPage from "./pages/tracking/TrackingPage";
import InvoicesPage from "./pages/invoices/InvoicesPage";
import PaymentPage from "./pages/payment/PaymentPage";

// Authenticated Layout - wraps BrandingProvider around protected routes
function AuthenticatedLayout({ children }) {
  const { user } = useAuth();
  if (!user) return children;
  return <BrandingProvider>{children}</BrandingProvider>;
}

// Protected Route Component
function ProtectedRoute({ children, requireSuperAdmin = false }) {
  const { user, loading, isSuperAdmin } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0f1a]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requireSuperAdmin && !isSuperAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

// Public Route (redirect if logged in)
function PublicRoute({ children }) {
  const { user, loading, isSuperAdmin } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0f1a]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (user) {
    return <Navigate to={isSuperAdmin ? "/admin/tenants" : "/dashboard"} replace />;
  }

  return children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public Landing & Legal Pages */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/terms" element={<TermsPage />} />
      
      {/* Auth Routes */}
      <Route path="/login" element={
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      } />

      {/* Tenant Routes - wrapped in BrandingProvider via AuthenticatedLayout */}
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <DashboardPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/leads" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <LeadsPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/jobs" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <JobsPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/conversations" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <ConversationsPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/customers" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <CustomersPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/technicians" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <TechniciansPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/quotes" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <QuotesPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/campaigns" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <CampaignsPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/dispatch" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <DispatchBoard />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/reports" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <ReportsPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/reports/revenue" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <RevenueReportsPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/calendar" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <CalendarPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/settings" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <SettingsPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/settings/workflows" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <WorkflowBuilderPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />

      {/* Invoices */}
      <Route path="/invoices" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <InvoicesPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />

      {/* Customer Portal (Public) */}
      <Route path="/portal/:token" element={<CustomerPortal />} />

      {/* Technician Tracking (Public) */}
      <Route path="/track/:token" element={<TrackingPage />} />

      {/* Public Invoice Payment Page */}
      <Route path="/pay/:token" element={<PaymentPage />} />

      {/* Admin Routes */}
      <Route path="/admin" element={
        <ProtectedRoute requireSuperAdmin>
          <AuthenticatedLayout>
            <Navigate to="/admin/tenants" replace />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin/tenants" element={
        <ProtectedRoute requireSuperAdmin>
          <AuthenticatedLayout>
            <AdminTenantsPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
