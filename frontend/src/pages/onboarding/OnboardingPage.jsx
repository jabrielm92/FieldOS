import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import axios from "axios";
import {
  Thermometer,
  Droplets,
  Zap,
  Leaf,
  Sparkles,
  Car,
  Heart,
  Home,
  Wrench,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Plus,
  X,
} from "lucide-react";

const INDUSTRIES = [
  { slug: "hvac", name: "HVAC", tagline: "Heating, cooling & air quality", icon: Thermometer },
  { slug: "plumbing", name: "Plumbing", tagline: "Pipes, drains & water systems", icon: Droplets },
  { slug: "electrical", name: "Electrical", tagline: "Wiring, panels & fixtures", icon: Zap },
  { slug: "landscaping", name: "Landscaping", tagline: "Lawn care & outdoor services", icon: Leaf },
  { slug: "cleaning", name: "Cleaning", tagline: "Residential & commercial cleaning", icon: Sparkles },
  { slug: "auto_repair", name: "Auto Repair", tagline: "Vehicle maintenance & repair", icon: Car },
  { slug: "med_spa", name: "Med Spa", tagline: "Aesthetics & wellness services", icon: Heart },
  { slug: "home_care", name: "Home Care", tagline: "In-home care & support", icon: Home },
  { slug: "general", name: "General Contractor", tagline: "Construction & home improvement", icon: Wrench },
];

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

export default function OnboardingPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  // Wizard state
  const [step, setStep] = useState(1);
  const [selectedIndustry, setSelectedIndustry] = useState(null);
  const [jobTypes, setJobTypes] = useState([]); // { name, checked }
  const [customInput, setCustomInput] = useState("");
  const [loadingTemplate, setLoadingTemplate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  // Step 1 → Step 2: fetch template
  const handleContinue = async () => {
    if (!selectedIndustry) return;
    setLoadingTemplate(true);
    setError(null);
    try {
      const token = localStorage.getItem("fieldos_token");
      const res = await axios.get(
        `${BACKEND_URL}/api/v1/templates/industries/${selectedIndustry.slug}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const template = res.data;
      const fetchedJobTypes = (template?.job_types || []).map((jt) => ({
        name: typeof jt === "string" ? jt : jt.name || jt,
        checked: true,
      }));
      setJobTypes(fetchedJobTypes);
      setStep(2);
    } catch (err) {
      // If template fetch fails, still proceed with empty list
      setJobTypes([]);
      setStep(2);
    } finally {
      setLoadingTemplate(false);
    }
  };

  // Toggle a job type checkbox
  const toggleJobType = (index) => {
    setJobTypes((prev) =>
      prev.map((jt, i) => (i === index ? { ...jt, checked: !jt.checked } : jt))
    );
  };

  // Add custom job type
  const addCustomJobType = () => {
    const trimmed = customInput.trim();
    if (!trimmed) return;
    setJobTypes((prev) => [...prev, { name: trimmed, checked: true }]);
    setCustomInput("");
  };

  // Remove a job type
  const removeJobType = (index) => {
    setJobTypes((prev) => prev.filter((_, i) => i !== index));
  };

  // Step 2 → Save
  const handleFinish = async () => {
    setSaving(true);
    setError(null);
    try {
      const token = localStorage.getItem("fieldos_token");
      const checkedJobTypes = jobTypes.filter((jt) => jt.checked).map((jt) => jt.name);
      await axios.put(
        `${BACKEND_URL}/api/v1/settings/industry`,
        { industry_slug: selectedIndustry.slug, custom_job_types: checkedJobTypes },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // Show success screen, then refresh user data and navigate.
      // refreshUser fetches /auth/me which now returns onboarding_completed: true,
      // so ProtectedRoute will allow /dashboard on the very next render.
      setStep(3);
      setSuccess(true);
      await refreshUser();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError("Failed to save settings. Please try again.");
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0f1a] flex flex-col items-center justify-center px-4 py-12">
      {/* Logo / Brand */}
      <div className="mb-8 text-center">
        <span className="text-2xl font-bold text-white tracking-tight">
          Field<span className="text-blue-500">OS</span>
        </span>
      </div>

      {/* Step Indicator */}
      {step < 3 && (
        <div className="flex items-center gap-2 mb-8">
          {[1, 2].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
                  step === s
                    ? "bg-blue-600 text-white"
                    : step > s
                    ? "bg-blue-500/30 text-blue-400"
                    : "bg-white/10 text-white/40"
                }`}
              >
                {step > s ? <CheckCircle2 className="w-4 h-4" /> : s}
              </div>
              {s < 2 && (
                <div
                  className={`w-12 h-0.5 rounded ${
                    step > s ? "bg-blue-500/50" : "bg-white/10"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* ───── STEP 1: Industry Selection ───── */}
      {step === 1 && (
        <div className="w-full max-w-3xl">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">
              What type of field service business do you run?
            </h1>
            <p className="text-white/50 text-lg">
              We'll customize FieldOS for your industry
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
            {INDUSTRIES.map((industry) => {
              const Icon = industry.icon;
              const isSelected = selectedIndustry?.slug === industry.slug;
              return (
                <button
                  key={industry.slug}
                  onClick={() => setSelectedIndustry(industry)}
                  className={`relative flex flex-col items-center text-center p-5 rounded-xl border transition-all duration-200 cursor-pointer group
                    ${
                      isSelected
                        ? "border-blue-500 bg-blue-600/20 shadow-lg shadow-blue-900/30"
                        : "border-white/10 bg-white/5 hover:border-blue-500/50 hover:bg-blue-600/10"
                    }`}
                >
                  {isSelected && (
                    <div className="absolute top-2 right-2">
                      <CheckCircle2 className="w-4 h-4 text-blue-400" />
                    </div>
                  )}
                  <div
                    className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 transition-colors ${
                      isSelected ? "bg-blue-600/40" : "bg-white/10 group-hover:bg-blue-600/20"
                    }`}
                  >
                    <Icon
                      className={`w-6 h-6 transition-colors ${
                        isSelected ? "text-blue-300" : "text-white/60 group-hover:text-blue-400"
                      }`}
                    />
                  </div>
                  <span
                    className={`text-sm font-semibold mb-1 transition-colors ${
                      isSelected ? "text-white" : "text-white/80"
                    }`}
                  >
                    {industry.name}
                  </span>
                  <span
                    className={`text-xs leading-snug transition-colors ${
                      isSelected ? "text-blue-200/70" : "text-white/40"
                    }`}
                  >
                    {industry.tagline}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="flex justify-center">
            <button
              onClick={handleContinue}
              disabled={!selectedIndustry || loadingTemplate}
              className={`flex items-center gap-2 px-8 py-3 rounded-xl font-semibold text-base transition-all duration-200
                ${
                  selectedIndustry && !loadingTemplate
                    ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/40 cursor-pointer"
                    : "bg-white/10 text-white/30 cursor-not-allowed"
                }`}
            >
              {loadingTemplate ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  Continue
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ───── STEP 2: Confirm Job Types ───── */}
      {step === 2 && selectedIndustry && (
        <div className="w-full max-w-lg">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">
              Confirm your service types
            </h1>
            <p className="text-white/50 text-base">
              These are the services we've pre-loaded for{" "}
              <span className="text-blue-400 font-medium">{selectedIndustry.name}</span>.
              You can customize them anytime in Settings.
            </p>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-5 mb-4">
            {jobTypes.length === 0 && (
              <p className="text-white/40 text-sm text-center py-4">
                No service types loaded. Add your own below.
              </p>
            )}
            <ul className="space-y-2">
              {jobTypes.map((jt, index) => (
                <li
                  key={index}
                  className="flex items-center gap-3 group"
                >
                  <button
                    onClick={() => toggleJobType(index)}
                    className={`flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                      jt.checked
                        ? "bg-blue-600 border-blue-500"
                        : "border-white/30 bg-transparent hover:border-blue-400"
                    }`}
                  >
                    {jt.checked && (
                      <svg
                        className="w-3 h-3 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={3}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    )}
                  </button>
                  <span
                    className={`flex-1 text-sm transition-colors ${
                      jt.checked ? "text-white" : "text-white/40 line-through"
                    }`}
                  >
                    {jt.name}
                  </span>
                  <button
                    onClick={() => removeJobType(index)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-white/30 hover:text-red-400"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </li>
              ))}
            </ul>

            {/* Add custom type */}
            <div className="mt-4 pt-4 border-t border-white/10">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customInput}
                  onChange={(e) => setCustomInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") addCustomJobType();
                  }}
                  placeholder="Add a custom service type..."
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-blue-500/60 transition-colors"
                />
                <button
                  onClick={addCustomJobType}
                  disabled={!customInput.trim()}
                  className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    customInput.trim()
                      ? "bg-blue-600/30 text-blue-300 hover:bg-blue-600/50 cursor-pointer"
                      : "bg-white/5 text-white/20 cursor-not-allowed"
                  }`}
                >
                  <Plus className="w-4 h-4" />
                  Add
                </button>
              </div>
            </div>
          </div>

          {error && (
            <p className="text-red-400 text-sm text-center mb-4">{error}</p>
          )}

          <div className="flex items-center gap-3 justify-between">
            <button
              onClick={() => setStep(1)}
              className="text-sm text-white/40 hover:text-white/70 transition-colors"
            >
              ← Back
            </button>
            <button
              onClick={handleFinish}
              disabled={saving}
              className={`flex items-center gap-2 px-8 py-3 rounded-xl font-semibold text-base transition-all duration-200
                ${
                  !saving
                    ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/40 cursor-pointer"
                    : "bg-blue-600/50 text-white/50 cursor-not-allowed"
                }`}
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  Finish Setup
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ───── STEP 3: Success ───── */}
      {step === 3 && (
        <div className="flex flex-col items-center text-center gap-4">
          <div className="w-20 h-20 rounded-full bg-blue-600/20 flex items-center justify-center mb-2 animate-pulse">
            <CheckCircle2 className="w-10 h-10 text-blue-400" />
          </div>
          <h1 className="text-3xl font-bold text-white">You're all set!</h1>
          <p className="text-white/50 text-lg">
            Taking you to your dashboard...
          </p>
          <Loader2 className="w-5 h-5 text-blue-400 animate-spin mt-2" />
        </div>
      )}
    </div>
  );
}
