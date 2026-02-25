import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
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
import OnboardingPage from "./pages/onboarding/OnboardingPage";
import SignupPage from "./pages/auth/SignupPage";
import PricingPage from "./pages/billing/PricingPage";
import BillingPage from "./pages/billing/BillingPage";
import BillingSuccessPage from "./pages/billing/BillingSuccessPage";
import TechAppPage from "./pages/tech/TechAppPage";

// Authenticated Layout - wraps BrandingProvider around protected routes
function AuthenticatedLayout({ children }) {
  const { user } = useAuth();
  if (!user) return children;
  return <BrandingProvider>{children}</BrandingProvider>;
}

// Protected Route Component
function ProtectedRoute({ children, requireSuperAdmin = false }) {
  const { user, loading, isSuperAdmin } = useAuth();
  const location = useLocation();

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

  // Onboarding gate (non-superadmin tenants only)
  const onboardingDone = user?.tenant?.onboarding_completed === true;
  if (!isSuperAdmin) {
    // Not yet done → send to onboarding (unless already there)
    if (!onboardingDone && location.pathname !== '/onboarding') {
      return <Navigate to="/onboarding" replace />;
    }
    // Already done → never show onboarding again
    if (onboardingDone && location.pathname === '/onboarding') {
      return <Navigate to="/dashboard" replace />;
    }
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
      <Route path="/signup" element={
        <PublicRoute>
          <SignupPage />
        </PublicRoute>
      } />

      {/* Onboarding Route */}
      <Route path="/onboarding" element={
        <ProtectedRoute>
          <OnboardingPage />
        </ProtectedRoute>
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

      {/* Pricing (Public) */}
      <Route path="/pricing" element={<PricingPage />} />

      {/* Billing Success (Public - post Stripe checkout) */}
      <Route path="/billing/success" element={<BillingSuccessPage />} />

      {/* Billing Management (Protected) */}
      <Route path="/billing" element={
        <ProtectedRoute>
          <AuthenticatedLayout>
            <BillingPage />
          </AuthenticatedLayout>
        </ProtectedRoute>
      } />

      {/* Technician Mobile App */}
      <Route path="/tech" element={
        <ProtectedRoute>
          <TechAppPage />
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
