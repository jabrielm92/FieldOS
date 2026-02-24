import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { toast } from "sonner";
import {
  Phone, Calendar, Users, BarChart3, MessageSquare, Zap,
  Shield, Clock, Star, Check,
  Headphones, Bot, FileText, Send, Target, TrendingUp,
  Menu, X, ArrowRight, Loader2, Sparkles, ChevronRight,
  Wrench, Bolt, Droplets, Leaf, Wind, Car, Activity
} from "lucide-react";

const API_URL = import.meta.env.VITE_BACKEND_URL;
const DEMO_URL = "https://calendly.com/jabriel-arisolutionsinc/30min";

/* ─── Data ─────────────────────────────────────────────────────────────── */

const features = [
  {
    icon: Phone,
    title: "AI Voice Receptionist",
    description: "24/7 AI answers every call, books appointments, and captures leads — never puts a customer on hold.",
    color: "from-blue-500/20 to-blue-600/10",
    glow: "group-hover:shadow-blue-500/20",
    size: "lg",
  },
  {
    icon: Bot,
    title: "AI SMS Assistant",
    description: "Qualify inbound texts, answer FAQs, and book jobs automatically — without lifting a finger.",
    color: "from-violet-500/20 to-violet-600/10",
    glow: "group-hover:shadow-violet-500/20",
    size: "lg",
  },
  {
    icon: Calendar,
    title: "Dispatch Board",
    description: "Drag-and-drop scheduling with real-time technician tracking and smart job assignment.",
    color: "from-cyan-500/20 to-cyan-600/10",
    glow: "group-hover:shadow-cyan-500/20",
    size: "sm",
  },
  {
    icon: MessageSquare,
    title: "Unified Inbox",
    description: "SMS, calls, and lead conversations in one place with automated follow-ups.",
    color: "from-emerald-500/20 to-emerald-600/10",
    glow: "group-hover:shadow-emerald-500/20",
    size: "sm",
  },
  {
    icon: FileText,
    title: "Quotes & Invoicing",
    description: "Send professional quotes in minutes. One-click to invoice. Collect payment via Stripe.",
    color: "from-amber-500/20 to-amber-600/10",
    glow: "group-hover:shadow-amber-500/20",
    size: "sm",
  },
  {
    icon: Target,
    title: "SMS Campaigns",
    description: "Drip sequences, seasonal promos, and re-engagement campaigns sent automatically.",
    color: "from-rose-500/20 to-rose-600/10",
    glow: "group-hover:shadow-rose-500/20",
    size: "sm",
  },
  {
    icon: BarChart3,
    title: "Revenue Analytics",
    description: "Live dashboards for revenue, job completion rates, technician performance, and CSV export.",
    color: "from-blue-500/20 to-purple-500/10",
    glow: "group-hover:shadow-blue-500/20",
    size: "sm",
  },
  {
    icon: Users,
    title: "Customer Portal",
    description: "Branded self-service portal — customers book, view history, and pay invoices online.",
    color: "from-teal-500/20 to-teal-600/10",
    glow: "group-hover:shadow-teal-500/20",
    size: "sm",
  },
  {
    icon: Zap,
    title: "Workflow Automation",
    description: "Visual workflow builder to automate follow-ups, status changes, and notifications.",
    color: "from-yellow-500/20 to-yellow-600/10",
    glow: "group-hover:shadow-yellow-500/20",
    size: "sm",
  },
  {
    icon: TrendingUp,
    title: "Technician Mobile App",
    description: "Field techs get their schedule, job details, and status updates on any device.",
    color: "from-indigo-500/20 to-indigo-600/10",
    glow: "group-hover:shadow-indigo-500/20",
    size: "sm",
  },
];

const testimonials = [
  {
    name: "Marcus Johnson",
    company: "Johnson HVAC Solutions",
    initials: "MJ",
    quote: "FieldOS transformed our business. We went from missing 40% of calls to capturing every single lead. Revenue is up 65% in 6 months.",
    rating: 5,
    color: "from-blue-600 to-blue-700",
  },
  {
    name: "Sarah Chen",
    company: "Premier Plumbing Co.",
    initials: "SC",
    quote: "The AI receptionist alone is worth the investment. It's like having a full-time employee who never sleeps and never misses a call.",
    rating: 5,
    color: "from-violet-600 to-violet-700",
  },
  {
    name: "David Martinez",
    company: "Elite Electrical Services",
    initials: "DM",
    quote: "We've tried every field service software out there. FieldOS is the only one that actually understands how service businesses work.",
    rating: 5,
    color: "from-emerald-600 to-emerald-700",
  },
];

const pricingPlans = [
  {
    name: "Starter",
    monthly: "149",
    setup: "497",
    tagline: "For solo operators & small crews",
    color: "border-white/10",
    features: [
      "Up to 3 technicians & 5 users",
      "Jobs, customers & scheduling",
      "Invoicing + Stripe payment collection",
      "Customer self-service portal",
      "Automated SMS reminders",
      "Dispatch board",
      "Revenue reports & CSV export",
      "Email support",
    ],
  },
  {
    name: "Pro",
    monthly: "299",
    setup: "797",
    tagline: "For growing field service companies",
    popular: true,
    color: "border-blue-500",
    features: [
      "Up to 10 technicians & 15 users",
      "Everything in Starter",
      "AI Voice receptionist (24/7)",
      "AI SMS assistant & lead qualification",
      "Automated booking & lead capture",
      "SMS marketing campaigns",
      "Priority support",
    ],
  },
  {
    name: "Enterprise",
    monthly: "549",
    setup: "1,497",
    tagline: "For multi-location & high-volume ops",
    color: "border-white/10",
    features: [
      "Unlimited technicians & users",
      "Everything in Pro",
      "White-label branding & custom domain",
      "Custom AI voice & SMS prompts",
      "Multi-location support",
      "Dedicated onboarding & training",
      "SLA-backed support",
    ],
  },
];

const industries = [
  { name: "HVAC", icon: Wind },
  { name: "Plumbing", icon: Droplets },
  { name: "Electrical", icon: Bolt },
  { name: "Landscaping", icon: Leaf },
  { name: "Cleaning", icon: Sparkles },
  { name: "Auto Repair", icon: Car },
  { name: "Med Spa", icon: Activity },
  { name: "Home Care", icon: Wrench },
  { name: "General Contracting", icon: Wrench },
];

const stats = [
  { value: 95, suffix: "%", label: "Lead Capture Rate" },
  { value: 60, suffix: "%", label: "Avg Revenue Increase" },
  { value: 24, suffix: "/7", label: "AI Availability" },
  { value: 48, suffix: "hrs", label: "Avg. Go-Live Time" },
];

/* ─── Hooks ─────────────────────────────────────────────────────────────── */

function useScrollReveal() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    const els = document.querySelectorAll(".reveal, .reveal-left, .reveal-right, .reveal-scale");
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
}

function useCounter(target, isVisible, duration = 1400) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!isVisible) return;
    let start = 0;
    const step = Math.ceil(target / (duration / 16));
    const timer = setInterval(() => {
      start = Math.min(start + step, target);
      setCount(start);
      if (start >= target) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [isVisible, target, duration]);
  return count;
}

/* ─── Sub-components ────────────────────────────────────────────────────── */

function StatCard({ value, suffix, label, delay }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  const count = useCounter(value, visible);

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.5 }
    );
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`reveal glass rounded-2xl p-6 text-center delay-${delay}`}
    >
      <div className="text-4xl sm:text-5xl font-black mb-1 bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
        {count}{suffix}
      </div>
      <div className="text-sm text-gray-400 font-medium">{label}</div>
    </div>
  );
}

function FeatureCard({ feature, index }) {
  const isLarge = feature.size === "lg";
  return (
    <div
      className={`group gradient-border rounded-2xl p-6 transition-all duration-500 reveal delay-${Math.min(index * 100, 600)} cursor-default
        ${isLarge ? "md:col-span-1 lg:col-span-1" : ""}
        hover:shadow-2xl ${feature.glow}`}
      style={{ transitionDelay: `${index * 60}ms` }}
    >
      <div
        className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4
          group-hover:scale-110 transition-transform duration-300`}
      >
        <feature.icon className="h-6 w-6 text-white" />
      </div>
      <h3 className="text-base font-bold mb-2 text-white">{feature.title}</h3>
      <p className="text-sm text-gray-400 leading-relaxed">{feature.description}</p>
    </div>
  );
}

function TestimonialCard({ t, index }) {
  return (
    <div
      className={`reveal gradient-border rounded-2xl p-7 flex flex-col gap-5 delay-${index * 200}`}
    >
      <div className="flex gap-1">
        {Array.from({ length: t.rating }).map((_, i) => (
          <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
        ))}
      </div>
      <p className="text-gray-300 leading-relaxed text-[15px] flex-1">
        <span className="text-blue-400 text-2xl font-black leading-none mr-1">"</span>
        {t.quote}
        <span className="text-blue-400 text-2xl font-black leading-none ml-1">"</span>
      </p>
      <div className="flex items-center gap-3">
        <div
          className={`w-11 h-11 rounded-full bg-gradient-to-br ${t.color} flex items-center justify-center text-white font-bold text-sm shrink-0`}
        >
          {t.initials}
        </div>
        <div>
          <div className="font-semibold text-white text-sm">{t.name}</div>
          <div className="text-xs text-gray-500">{t.company}</div>
        </div>
      </div>
    </div>
  );
}

/* ─── Main Component ────────────────────────────────────────────────────── */

export default function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [contactForm, setContactForm] = useState({ name: "", email: "", phone: "", company: "", message: "" });
  const [submitting, setSubmitting] = useState(false);

  useScrollReveal();

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  const handleContactSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/api/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(contactForm),
      });
      if (res.ok) {
        toast.success("Thanks! We'll be in touch within 24 hours.");
        setContactForm({ name: "", email: "", phone: "", company: "", message: "" });
      } else {
        toast.error("Something went wrong. Please try again.");
      }
    } catch {
      toast.error("Failed to submit. Please email us directly.");
    } finally {
      setSubmitting(false);
    }
  };

  /* Duplicate industry list for seamless marquee */
  const marqueeItems = [...industries, ...industries];

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white overflow-x-hidden">
      {/* ── Floating background orbs ─────────────────────────────────── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden z-0">
        <div className="animate-float absolute -top-32 -left-32 w-[600px] h-[600px] rounded-full bg-blue-600/10 blur-[120px]" />
        <div className="animate-float-alt absolute top-1/3 -right-40 w-[500px] h-[500px] rounded-full bg-violet-600/10 blur-[120px]" />
        <div className="animate-float absolute bottom-0 left-1/3 w-[400px] h-[400px] rounded-full bg-blue-500/8 blur-[100px]" />
        <div className="dot-grid absolute inset-0 opacity-40" />
      </div>

      {/* ── Navigation ───────────────────────────────────────────────── */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500
          ${scrolled ? "bg-[#0a0f1a]/80 backdrop-blur-xl border-b border-white/8 shadow-2xl shadow-black/20" : ""}`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 md:h-20">
            {/* Logo */}
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-black tracking-tight">FieldOS</span>
            </div>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-8">
              {["Features", "Testimonials", "Pricing", "Contact"].map((item) => (
                <a
                  key={item}
                  href={`#${item.toLowerCase()}`}
                  className="text-sm text-gray-400 hover:text-white transition-colors duration-200 font-medium"
                >
                  {item}
                </a>
              ))}
            </div>

            <div className="hidden md:flex items-center gap-3">
              <Link to="/login">
                <Button variant="ghost" className="text-gray-400 hover:text-white text-sm">
                  Sign In
                </Button>
              </Link>
              <a href={DEMO_URL} target="_blank" rel="noopener noreferrer">
                <Button
                  className="bg-blue-600 hover:bg-blue-500 text-white text-sm px-5 rounded-xl shadow-lg shadow-blue-600/25 transition-all duration-300 hover:shadow-blue-500/40 hover:-translate-y-px"
                >
                  Book a Demo
                  <ArrowRight className="ml-1.5 h-4 w-4" />
                </Button>
              </a>
            </div>

            <button className="md:hidden p-2 text-gray-400 hover:text-white" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        <div
          className={`md:hidden transition-all duration-300 overflow-hidden
            ${mobileMenuOpen ? "max-h-96 border-t border-white/10" : "max-h-0"}`}
        >
          <div className="bg-[#0a0f1a]/95 backdrop-blur-xl px-4 py-4 flex flex-col gap-3">
            {["features", "testimonials", "pricing", "contact"].map((id) => (
              <a
                key={id}
                href={`#${id}`}
                onClick={() => setMobileMenuOpen(false)}
                className="capitalize text-gray-300 hover:text-white py-2 text-sm font-medium"
              >
                {id}
              </a>
            ))}
            <Link to="/login" className="text-gray-300 hover:text-white py-2 text-sm font-medium" onClick={() => setMobileMenuOpen(false)}>
              Sign In
            </Link>
            <a href={DEMO_URL} target="_blank" rel="noopener noreferrer">
              <Button className="w-full bg-blue-600 hover:bg-blue-500 rounded-xl mt-1">Book a Demo</Button>
            </a>
          </div>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative pt-36 pb-24 md:pt-48 md:pb-36">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">

          {/* Badge */}
          <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-2 mb-8 reveal">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
            </span>
            <span className="text-xs text-gray-300 font-medium tracking-wide">
              AI-Powered · Voice · SMS · Dispatch · Analytics
            </span>
          </div>

          {/* Headline */}
          <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-black tracking-tight leading-[0.95] mb-6 reveal delay-100">
            Run Your Entire
            <span
              className="block animate-shimmer bg-gradient-to-r from-blue-400 via-violet-400 to-blue-400 bg-clip-text text-transparent"
            >
              Field Business
            </span>
            <span className="block text-white">From One Place.</span>
          </h1>

          <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed reveal delay-200">
            FieldOS replaces your receptionist, dispatcher, and marketing team.
            AI that captures every lead, fills every schedule, and grows your revenue — automatically.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12 reveal delay-300">
            <a href={DEMO_URL} target="_blank" rel="noopener noreferrer">
              <Button
                size="lg"
                className="animate-glow-pulse bg-blue-600 hover:bg-blue-500 text-white px-8 py-6 text-base rounded-2xl font-semibold shadow-xl shadow-blue-600/30 transition-all duration-300 hover:-translate-y-1"
              >
                Schedule Your Free Demo
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </a>
            <a href="#features">
              <Button
                size="lg"
                variant="outline"
                className="border-white/15 text-white hover:bg-white/8 px-8 py-6 text-base rounded-2xl font-semibold backdrop-blur-sm transition-all duration-300"
              >
                See How It Works
              </Button>
            </a>
          </div>

          {/* Trust badges */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-gray-500 reveal delay-400">
            {["No credit card required", "Live in 48 hours", "Cancel anytime"].map((t) => (
              <div key={t} className="flex items-center gap-2">
                <Check className="h-4 w-4 text-green-500 shrink-0" />
                <span>{t}</span>
              </div>
            ))}
          </div>

          {/* Hero dashboard preview */}
          <div className="mt-20 max-w-4xl mx-auto reveal delay-500">
            <div className="glass rounded-2xl border border-white/10 overflow-hidden shadow-2xl shadow-black/40">
              {/* Fake toolbar */}
              <div className="flex items-center gap-2 px-4 py-3 bg-white/5 border-b border-white/8">
                <div className="w-3 h-3 rounded-full bg-red-500/70" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
                <div className="w-3 h-3 rounded-full bg-green-500/70" />
                <span className="ml-3 text-xs text-gray-500 font-mono">FieldOS — Operations Dashboard</span>
              </div>
              {/* Dashboard grid */}
              <div className="p-4 sm:p-6 grid grid-cols-3 sm:grid-cols-4 gap-3">
                {[
                  { label: "Today's Jobs", value: "12", sub: "+3 new", color: "text-blue-400" },
                  { label: "Open Leads", value: "8", sub: "2 urgent", color: "text-violet-400" },
                  { label: "Revenue (MTD)", value: "$24.8k", sub: "↑ 18%", color: "text-emerald-400" },
                  { label: "AI Calls Today", value: "47", sub: "100% answered", color: "text-amber-400" },
                ].map((card) => (
                  <div key={card.label} className="rounded-xl bg-white/5 border border-white/8 p-3 sm:p-4">
                    <div className="text-[10px] text-gray-500 font-medium mb-1 uppercase tracking-wider">{card.label}</div>
                    <div className={`text-xl sm:text-2xl font-black ${card.color}`}>{card.value}</div>
                    <div className="text-[10px] text-gray-500 mt-0.5">{card.sub}</div>
                  </div>
                ))}
                {/* Fake activity feed */}
                <div className="col-span-3 sm:col-span-4 rounded-xl bg-white/5 border border-white/8 p-3 sm:p-4">
                  <div className="text-[10px] text-gray-500 font-medium mb-3 uppercase tracking-wider">Live Activity</div>
                  <div className="space-y-2">
                    {[
                      { icon: "📞", text: "AI answered call from (555) 821-4490 — HVAC tune-up booked", time: "just now", dot: "bg-green-500" },
                      { icon: "💬", text: "AI SMS qualified lead from web form — dispatched to Mike T.", time: "2m ago", dot: "bg-blue-500" },
                      { icon: "💵", text: "Invoice #1082 paid — $340 collected via Stripe", time: "5m ago", dot: "bg-emerald-500" },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center gap-3 text-xs text-gray-400">
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${item.dot}`} />
                        <span className="flex-1 truncate">{item.text}</span>
                        <span className="text-gray-600 shrink-0">{item.time}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Industry Marquee ──────────────────────────────────────────── */}
      <div className="relative py-8 border-y border-white/8 overflow-hidden bg-white/3">
        <div className="flex animate-marquee whitespace-nowrap" style={{ width: "max-content" }}>
          {marqueeItems.map((ind, i) => (
            <div key={i} className="inline-flex items-center gap-2.5 mx-8 text-gray-500">
              <ind.icon className="h-4 w-4 text-gray-600 shrink-0" />
              <span className="text-sm font-medium tracking-wide">{ind.name}</span>
              <span className="ml-8 text-gray-700">·</span>
            </div>
          ))}
        </div>
        <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-[#0a0f1a] to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-[#0a0f1a] to-transparent z-10 pointer-events-none" />
      </div>

      {/* ── Stats ────────────────────────────────────────────────────── */}
      <section className="py-20 relative z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map((s, i) => (
              <StatCard key={i} {...s} delay={(i + 1) * 100} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────── */}
      <section id="features" className="py-20 md:py-32 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 mb-5 reveal">
              <Sparkles className="h-3.5 w-3.5 text-blue-400" />
              <span className="text-xs text-blue-300 font-medium">10 Powerful Modules</span>
            </div>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-4 reveal delay-100">
              Everything to{" "}
              <span className="bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
                Dominate
              </span>{" "}
              Your Market
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto reveal delay-200">
              A complete operating system for field service businesses — built by people who understand how you work.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {features.map((feature, i) => (
              <FeatureCard key={i} feature={feature} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ─────────────────────────────────────────────── */}
      <section className="py-20 md:py-32 relative z-10">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-950/15 to-transparent pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-4 reveal">
              Like Hiring a{" "}
              <span className="bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
                Full Team
              </span>
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto reveal delay-100">
              FieldOS replaces the work of 5+ employees. Focus on delivering great service — we'll handle everything else.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 relative">
            {/* Connector line (desktop) */}
            <div className="hidden md:block absolute top-14 left-[33.33%] right-[33.33%] h-px bg-gradient-to-r from-blue-600/40 via-violet-600/40 to-blue-600/40" />

            {[
              {
                num: "01",
                icon: Headphones,
                title: "Replaces Your Receptionist",
                description: "AI answers every call, books appointments, qualifies leads, and sends confirmations — 24/7, zero hold times.",
                delay: "delay-100",
              },
              {
                num: "02",
                icon: Clock,
                title: "Replaces Your Dispatcher",
                description: "Smart scheduling assigns jobs by location, skills, and availability. Technicians get instant updates on any device.",
                delay: "delay-300",
              },
              {
                num: "03",
                icon: Send,
                title: "Replaces Your Marketing Team",
                description: "Automated campaigns, seasonal promos, review requests, and re-engagement sequences that run themselves.",
                delay: "delay-500",
              },
            ].map((item, i) => (
              <div key={i} className={`relative reveal ${item.delay}`}>
                <div className="gradient-border rounded-2xl p-8 h-full hover:shadow-2xl hover:shadow-blue-500/10 transition-all duration-500">
                  {/* Step number */}
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center font-black text-sm mb-6 shadow-lg shadow-blue-600/30">
                    {item.num}
                  </div>
                  <item.icon className="h-8 w-8 text-blue-400 mb-4" />
                  <h3 className="text-xl font-bold mb-3 text-white">{item.title}</h3>
                  <p className="text-gray-400 leading-relaxed">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ─────────────────────────────────────────────── */}
      <section id="testimonials" className="py-20 md:py-32 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-4 reveal">
              Trusted by{" "}
              <span className="bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
                Industry Leaders
              </span>
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto reveal delay-100">
              See why top field service companies choose FieldOS to power their operations.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t, i) => (
              <TestimonialCard key={i} t={t} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────────────── */}
      <section id="pricing" className="py-20 md:py-32 relative z-10">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-violet-950/10 to-transparent pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-4 reveal">
              Simple,{" "}
              <span className="bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
                Transparent
              </span>{" "}
              Pricing
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto reveal delay-100">
              No hidden fees. Every plan includes our core platform. Book a call to find your perfect fit.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {pricingPlans.map((plan, i) => (
              <div
                key={i}
                className={`reveal relative rounded-2xl border p-8 transition-all duration-500 delay-${i * 150}
                  ${plan.popular
                    ? "bg-gradient-to-b from-blue-600/15 to-violet-600/10 border-blue-500 animate-glow-pulse"
                    : "glass border-white/10 hover:border-white/20"
                  }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-blue-600 to-violet-600 text-white text-xs font-bold px-5 py-1.5 rounded-full shadow-lg shadow-blue-600/30 whitespace-nowrap">
                    ✦ Most Popular
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-xl font-black mb-1">{plan.name}</h3>
                  <p className="text-xs text-gray-500">{plan.tagline}</p>
                </div>

                <div className="mb-2">
                  <span className="text-4xl font-black">${plan.monthly}</span>
                  <span className="text-gray-400 text-sm">/mo</span>
                </div>
                <div className="inline-flex items-center gap-1.5 bg-white/5 border border-white/8 rounded-lg px-3 py-1 mb-7">
                  <span className="text-gray-500 text-xs">+</span>
                  <span className="text-white text-xs font-bold">${plan.setup}</span>
                  <span className="text-gray-500 text-xs">one-time setup</span>
                </div>

                <ul className="space-y-3 mb-8">
                  {plan.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-3 text-sm">
                      <Check className="h-4 w-4 text-green-400 shrink-0 mt-0.5" />
                      <span className="text-gray-300">{f}</span>
                    </li>
                  ))}
                </ul>

                <a href={DEMO_URL} target="_blank" rel="noopener noreferrer" className="block">
                  <Button
                    className={`w-full rounded-xl font-semibold transition-all duration-300
                      ${plan.popular
                        ? "bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white shadow-lg shadow-blue-600/25 hover:-translate-y-px"
                        : "bg-white/8 hover:bg-white/15 text-white border border-white/10"
                      }`}
                  >
                    Book a Call
                    <ChevronRight className="ml-1.5 h-4 w-4" />
                  </Button>
                </a>
              </div>
            ))}
          </div>

          <p className="text-center mt-8 text-gray-500 text-sm reveal">
            All plans include onboarding & go-live support.{" "}
            <Link to="/pricing" className="text-blue-400 hover:text-blue-300 underline underline-offset-2">
              Sign up to subscribe directly →
            </Link>
          </p>
        </div>
      </section>

      {/* ── Contact ──────────────────────────────────────────────────── */}
      <section id="contact" className="py-20 md:py-32 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">

            {/* Left */}
            <div className="reveal-left">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-6">
                Let's Talk About
                <span className="block bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
                  Your Business
                </span>
              </h2>
              <p className="text-lg text-gray-400 mb-10 leading-relaxed">
                Every field service business is unique. Tell us about your challenges and we'll show you
                exactly how FieldOS can be tailored to fit your workflow.
              </p>

              <div className="space-y-5">
                {[
                  { icon: Clock, title: "Quick Response", desc: "We reply to all inquiries within 24 hours" },
                  { icon: Shield, title: "No Pressure", desc: "An honest conversation about whether we're the right fit" },
                  { icon: Target, title: "Custom Solutions", desc: "We adapt FieldOS to match your exact workflow" },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl glass border border-white/10 flex items-center justify-center shrink-0">
                      <item.icon className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-white mb-0.5">{item.title}</h4>
                      <p className="text-sm text-gray-500">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right — form */}
            <div className="reveal-right">
              <div className="gradient-border rounded-2xl p-8">
                <form onSubmit={handleContactSubmit} className="space-y-5">
                  <div className="grid sm:grid-cols-2 gap-4">
                    {[
                      { label: "Name *", field: "name", placeholder: "John Smith", required: true },
                      { label: "Email *", field: "email", placeholder: "john@company.com", required: true, type: "email" },
                    ].map(({ label, field, placeholder, required, type }) => (
                      <div key={field}>
                        <label className="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">{label}</label>
                        <Input
                          required={required}
                          type={type || "text"}
                          value={contactForm[field]}
                          onChange={(e) => setContactForm({ ...contactForm, [field]: e.target.value })}
                          placeholder={placeholder}
                          className="bg-white/5 border-white/10 text-white placeholder:text-gray-600 focus:border-blue-500 rounded-xl"
                        />
                      </div>
                    ))}
                  </div>

                  <div className="grid sm:grid-cols-2 gap-4">
                    {[
                      { label: "Phone", field: "phone", placeholder: "(555) 123-4567" },
                      { label: "Company", field: "company", placeholder: "Your Company" },
                    ].map(({ label, field, placeholder }) => (
                      <div key={field}>
                        <label className="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">{label}</label>
                        <Input
                          value={contactForm[field]}
                          onChange={(e) => setContactForm({ ...contactForm, [field]: e.target.value })}
                          placeholder={placeholder}
                          className="bg-white/5 border-white/10 text-white placeholder:text-gray-600 focus:border-blue-500 rounded-xl"
                        />
                      </div>
                    ))}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">Message *</label>
                    <Textarea
                      required
                      rows={4}
                      value={contactForm.message}
                      onChange={(e) => setContactForm({ ...contactForm, message: e.target.value })}
                      placeholder="Tell us about your business and what you're looking to achieve..."
                      className="bg-white/5 border-white/10 text-white placeholder:text-gray-600 focus:border-blue-500 resize-none rounded-xl"
                    />
                  </div>

                  <Button
                    type="submit"
                    disabled={submitting}
                    className="w-full bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white py-6 rounded-xl font-semibold text-base shadow-lg shadow-blue-600/20 transition-all duration-300 hover:-translate-y-px"
                  >
                    {submitting ? (
                      <><Loader2 className="mr-2 h-5 w-5 animate-spin" />Sending...</>
                    ) : (
                      <><Send className="mr-2 h-5 w-5" />Send Message</>
                    )}
                  </Button>

                  <p className="text-center text-xs text-gray-600">
                    Or email us at{" "}
                    <a href="mailto:fieldos@arisolutionsinc.com" className="text-blue-400 hover:text-blue-300 underline-offset-2 underline">
                      fieldos@arisolutionsinc.com
                    </a>
                  </p>
                </form>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────── */}
      <section className="py-24 md:py-36 relative z-10 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-950/40 via-violet-950/30 to-blue-950/40 pointer-events-none" />
        {/* Decorative ring */}
        <div className="absolute -top-1/2 left-1/2 -translate-x-1/2 w-[800px] h-[800px] rounded-full border border-blue-500/8 animate-spin-slow pointer-events-none" />
        <div className="absolute -top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full border border-violet-500/8 animate-spin-slow pointer-events-none" style={{ animationDirection: "reverse" }} />

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative">
          <h2 className="text-4xl sm:text-5xl md:text-6xl font-black mb-6 reveal">
            Ready to Transform
            <span className="block bg-gradient-to-r from-blue-400 via-violet-400 to-blue-400 bg-clip-text text-transparent animate-shimmer">
              Your Business?
            </span>
          </h2>
          <p className="text-lg text-gray-400 mb-10 max-w-xl mx-auto reveal delay-100">
            Join hundreds of field service companies using FieldOS to capture more leads, fill more schedules, and grow revenue — on autopilot.
          </p>
          <a href={DEMO_URL} target="_blank" rel="noopener noreferrer" className="reveal delay-200 inline-block">
            <Button
              size="lg"
              className="animate-glow-pulse bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white px-10 py-6 text-lg rounded-2xl font-semibold shadow-2xl shadow-blue-600/30 transition-all duration-300 hover:-translate-y-1"
            >
              Schedule Your Free Demo
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </a>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="border-t border-white/8 bg-[#060a12] py-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-10 mb-12">
            <div>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-violet-600 rounded-xl flex items-center justify-center">
                  <Zap className="h-5 w-5 text-white" />
                </div>
                <span className="text-lg font-black">FieldOS</span>
              </div>
              <p className="text-sm text-gray-500 mb-4 leading-relaxed">
                The complete AI-powered operating system for field service businesses.
              </p>
              <p className="text-xs text-gray-600">
                A product by <strong className="text-gray-400">Ari Solutions Inc.</strong>
              </p>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Product</h4>
              <ul className="space-y-2.5 text-sm text-gray-500">
                {[["#features", "Features"], ["#pricing", "Pricing"], ["#testimonials", "Testimonials"]].map(([href, label]) => (
                  <li key={label}><a href={href} className="hover:text-white transition-colors">{label}</a></li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Legal</h4>
              <ul className="space-y-2.5 text-sm text-gray-500">
                <li><Link to="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
                <li><Link to="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-4">Contact</h4>
              <ul className="space-y-2.5 text-sm text-gray-500">
                <li>
                  <a href="mailto:fieldos@arisolutionsinc.com" className="hover:text-white transition-colors">
                    fieldos@arisolutionsinc.com
                  </a>
                </li>
                <li>
                  <a href={DEMO_URL} target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
                    Book a Demo →
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="pt-8 border-t border-white/8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-600">
            <p>© {new Date().getFullYear()} Ari Solutions Inc. All rights reserved.</p>
            <div className="flex items-center gap-5">
              <Link to="/privacy" className="hover:text-white transition-colors">Privacy</Link>
              <Link to="/terms" className="hover:text-white transition-colors">Terms</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
