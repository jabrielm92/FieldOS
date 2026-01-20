import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { toast } from "sonner";
import { 
  Phone, Calendar, Users, BarChart3, MessageSquare, Zap, 
  Shield, Clock, DollarSign, ChevronRight, Star, Check,
  Headphones, Bot, FileText, Send, Target, TrendingUp,
  Menu, X, ArrowRight, Mail, Loader2
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const features = [
  {
    icon: Phone,
    title: "AI Phone Receptionist",
    description: "24/7 intelligent call handling that books appointments, answers questions, and never misses a lead."
  },
  {
    icon: Bot,
    title: "Smart Lead Capture",
    description: "Automatically capture and qualify leads from calls, web forms, and SMS conversations."
  },
  {
    icon: Calendar,
    title: "Intelligent Scheduling",
    description: "Drag-and-drop dispatch board with route optimization and real-time technician tracking."
  },
  {
    icon: MessageSquare,
    title: "Unified Communications",
    description: "SMS, email, and call management in one inbox. Automated follow-ups and reminders."
  },
  {
    icon: FileText,
    title: "Quotes & Invoicing",
    description: "Professional quotes in minutes. Convert to invoices with one click. Get paid faster."
  },
  {
    icon: Target,
    title: "Marketing Campaigns",
    description: "Automated drip campaigns, seasonal promotions, and customer re-engagement."
  },
  {
    icon: BarChart3,
    title: "Revenue Analytics",
    description: "Real-time dashboards showing revenue, conversion rates, and technician performance."
  },
  {
    icon: Users,
    title: "Customer Portal",
    description: "Self-service portal for customers to book, view history, and pay invoices online."
  }
];

const testimonials = [
  {
    name: "Marcus Johnson",
    company: "Johnson HVAC Solutions",
    image: "MJ",
    quote: "FieldOS transformed our business. We went from missing 40% of calls to capturing every single lead. Revenue is up 65% in 6 months.",
    rating: 5
  },
  {
    name: "Sarah Chen",
    company: "Premier Plumbing Co.",
    image: "SC",
    quote: "The AI receptionist alone is worth the investment. It's like having a full-time employee who never sleeps and never misses a call.",
    rating: 5
  },
  {
    name: "David Martinez",
    company: "Elite Electrical Services",
    image: "DM",
    quote: "We've tried every field service software out there. FieldOS is the only one that actually understands how service businesses work.",
    rating: 5
  }
];

const pricingPlans = [
  {
    name: "Starter",
    price: "497",
    description: "Perfect for growing service businesses",
    features: [
      "Up to 5 users",
      "AI Phone Receptionist",
      "Lead management",
      "Job scheduling",
      "Basic reporting",
      "Email support"
    ]
  },
  {
    name: "Professional",
    price: "997",
    description: "For established businesses ready to scale",
    features: [
      "Up to 15 users",
      "Everything in Starter",
      "Advanced AI automation",
      "Quote & invoice system",
      "Marketing campaigns",
      "Customer portal",
      "Priority support"
    ],
    popular: true
  },
  {
    name: "Enterprise",
    price: "Custom",
    description: "Tailored solutions for large operations",
    features: [
      "Unlimited users",
      "Everything in Professional",
      "Custom integrations",
      "White-label options",
      "Dedicated success manager",
      "Custom AI training",
      "SLA guarantee"
    ]
  }
];

export default function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [contactForm, setContactForm] = useState({
    name: "",
    email: "",
    phone: "",
    company: "",
    message: ""
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleContactSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    
    try {
      const response = await fetch(`${API_URL}/api/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(contactForm)
      });
      
      if (response.ok) {
        toast.success("Thanks! We'll be in touch within 24 hours.");
        setContactForm({ name: "", email: "", phone: "", company: "", message: "" });
      } else {
        toast.error("Something went wrong. Please try again.");
      }
    } catch (error) {
      toast.error("Failed to submit. Please email us directly.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white">
      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-[#0a0f1a]/95 backdrop-blur-md border-b border-white/10' : ''}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 md:h-20">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight">FieldOS</span>
            </div>
            
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-gray-300 hover:text-white transition-colors">Features</a>
              <a href="#testimonials" className="text-sm text-gray-300 hover:text-white transition-colors">Testimonials</a>
              <a href="#pricing" className="text-sm text-gray-300 hover:text-white transition-colors">Pricing</a>
              <Link to="/login">
                <Button variant="ghost" className="text-gray-300 hover:text-white">Sign In</Button>
              </Link>
              <a href="https://calendly.com/jabriel-arisolutionsinc/30min" target="_blank" rel="noopener noreferrer">
                <Button className="bg-blue-600 hover:bg-blue-700 text-white">Book a Demo</Button>
              </a>
            </div>

            <button className="md:hidden p-2" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-[#0a0f1a] border-t border-white/10 py-4 px-4">
            <div className="flex flex-col gap-4">
              <a href="#features" className="text-gray-300 hover:text-white py-2">Features</a>
              <a href="#testimonials" className="text-gray-300 hover:text-white py-2">Testimonials</a>
              <a href="#pricing" className="text-gray-300 hover:text-white py-2">Pricing</a>
              <Link to="/login" className="text-gray-300 hover:text-white py-2">Sign In</Link>
              <a href="https://calendly.com/jabriel-arisolutionsinc/30min" target="_blank" rel="noopener noreferrer">
                <Button className="w-full bg-blue-600 hover:bg-blue-700">Book a Demo</Button>
              </a>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-32 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-transparent to-purple-600/10" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(59,130,246,0.15),transparent_70%)]" />
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-2 mb-8">
              <Zap className="h-4 w-4 text-blue-400" />
              <span className="text-sm text-blue-300">AI-Powered Field Service Platform</span>
            </div>
            
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-tight mb-6">
              Your Complete
              <span className="block bg-gradient-to-r from-blue-400 via-blue-500 to-purple-500 bg-clip-text text-transparent">
                Operations Team
              </span>
              In One Platform
            </h1>
            
            <p className="text-lg sm:text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
              FieldOS replaces your receptionist, dispatcher, office manager, and marketing team. 
              AI-powered automation that captures every lead and grows your revenue.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <a href="https://calendly.com/jabriel-arisolutionsinc/30min" target="_blank" rel="noopener noreferrer">
                <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-6 text-lg rounded-xl">
                  Schedule Your Demo
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </a>
              <a href="#features">
                <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10 px-8 py-6 text-lg rounded-xl">
                  See How It Works
                </Button>
              </a>
            </div>

            <div className="mt-12 flex flex-wrap items-center justify-center gap-8 text-sm text-gray-500">
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                <span>No credit card required</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                <span>Setup in 48 hours</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                <span>Cancel anytime</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 border-y border-white/10 bg-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: "95%", label: "Lead Capture Rate" },
              { value: "60%", label: "Revenue Increase" },
              { value: "24/7", label: "AI Availability" },
              { value: "2hrs", label: "Avg. Setup Time" }
            ].map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-3xl sm:text-4xl md:text-5xl font-black text-blue-400 mb-2">{stat.value}</div>
                <div className="text-sm text-gray-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-4">
              Everything You Need to
              <span className="text-blue-400"> Dominate</span>
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto">
              A complete operating system for field service businesses. Built by industry veterans who understand your challenges.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, i) => (
              <div 
                key={i} 
                className="group p-6 rounded-2xl bg-gradient-to-b from-white/5 to-transparent border border-white/10 hover:border-blue-500/50 transition-all duration-300"
              >
                <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center mb-4 group-hover:bg-blue-500/30 transition-colors">
                  <feature.icon className="h-6 w-6 text-blue-400" />
                </div>
                <h3 className="text-lg font-bold mb-2">{feature.title}</h3>
                <p className="text-sm text-gray-400">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 md:py-32 bg-gradient-to-b from-transparent via-blue-950/20 to-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-4">
              Like Hiring a
              <span className="text-blue-400"> Full Team</span>
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto">
              FieldOS handles the work of 5+ employees. Focus on what you do best—we'll handle the rest.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Headphones,
                title: "Replaces Your Receptionist",
                description: "Our AI answers every call, books appointments, and never puts customers on hold. Available 24/7/365."
              },
              {
                icon: Clock,
                title: "Replaces Your Dispatcher",
                description: "Smart scheduling assigns jobs based on location, skills, and availability. Automatic route optimization."
              },
              {
                icon: Send,
                title: "Replaces Your Marketing Team",
                description: "Automated campaigns, review requests, and follow-ups that keep customers coming back."
              }
            ].map((item, i) => (
              <div key={i} className="relative p-8 rounded-2xl bg-[#0d1424] border border-white/10">
                <div className="absolute -top-4 -left-4 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center font-bold text-sm">
                  {i + 1}
                </div>
                <item.icon className="h-10 w-10 text-blue-400 mb-4" />
                <h3 className="text-xl font-bold mb-3">{item.title}</h3>
                <p className="text-gray-400">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="py-20 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-4">
              Trusted by
              <span className="text-blue-400"> Industry Leaders</span>
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto">
              See why top field service companies choose FieldOS to power their operations.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, i) => (
              <div key={i} className="p-6 rounded-2xl bg-gradient-to-b from-white/5 to-transparent border border-white/10">
                <div className="flex items-center gap-1 mb-4">
                  {[...Array(testimonial.rating)].map((_, j) => (
                    <Star key={j} className="h-5 w-5 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                <p className="text-gray-300 mb-6 italic">"{testimonial.quote}"</p>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center font-bold">
                    {testimonial.image}
                  </div>
                  <div>
                    <div className="font-semibold">{testimonial.name}</div>
                    <div className="text-sm text-gray-400">{testimonial.company}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-20 md:py-32 bg-gradient-to-b from-transparent via-blue-950/20 to-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-4">
              Invest in
              <span className="text-blue-400"> Growth</span>
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto">
              Transparent pricing with no hidden fees. Every plan includes our core AI features.
              <strong className="text-white"> Book a call to see if we're the right fit.</strong>
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {pricingPlans.map((plan, i) => (
              <div 
                key={i} 
                className={`relative p-8 rounded-2xl border ${plan.popular ? 'bg-blue-600/10 border-blue-500' : 'bg-white/5 border-white/10'}`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-sm font-semibold px-4 py-1 rounded-full">
                    Most Popular
                  </div>
                )}
                <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
                <p className="text-sm text-gray-400 mb-4">{plan.description}</p>
                <div className="mb-6">
                  {plan.price === "Custom" ? (
                    <span className="text-4xl font-black">Custom</span>
                  ) : (
                    <>
                      <span className="text-4xl font-black">${plan.price}</span>
                      <span className="text-gray-400">/month</span>
                    </>
                  )}
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, j) => (
                    <li key={j} className="flex items-start gap-3 text-sm">
                      <Check className="h-5 w-5 text-green-500 shrink-0" />
                      <span className="text-gray-300">{feature}</span>
                    </li>
                  ))}
                </ul>
                <a href="https://calendly.com/jabriel-arisolutionsinc/30min" target="_blank" rel="noopener noreferrer" className="block">
                  <Button className={`w-full ${plan.popular ? 'bg-blue-600 hover:bg-blue-700' : 'bg-white/10 hover:bg-white/20'}`}>
                    Book a Call
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Button>
                </a>
              </div>
            ))}
          </div>

          <p className="text-center mt-8 text-gray-400 text-sm">
            * All plans can be customized to your specific needs. Contact us for a personalized quote.
          </p>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 md:py-32">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black mb-6">
            Ready to Transform
            <span className="block text-blue-400">Your Business?</span>
          </h2>
          <p className="text-lg text-gray-400 mb-10 max-w-2xl mx-auto">
            Join hundreds of field service companies using FieldOS to capture more leads, 
            close more jobs, and grow their revenue.
          </p>
          <a href="https://calendly.com/jabriel-arisolutionsinc/30min" target="_blank" rel="noopener noreferrer">
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white px-10 py-6 text-lg rounded-xl">
              Schedule Your Free Demo
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/10 bg-[#060a12]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                  <Zap className="h-6 w-6 text-white" />
                </div>
                <span className="text-xl font-bold">FieldOS</span>
              </div>
              <p className="text-sm text-gray-400 mb-4">
                The complete AI-powered operating system for field service businesses.
              </p>
              <p className="text-sm text-gray-500">
                A product by <strong className="text-gray-300">Ari Solutions Inc.</strong>
              </p>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#testimonials" className="hover:text-white transition-colors">Testimonials</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><Link to="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
                <li><Link to="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">Contact</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li>
                  <a href="mailto:fieldos@arisolutionsinc.com" className="hover:text-white transition-colors">
                    fieldos@arisolutionsinc.com
                  </a>
                </li>
                <li>
                  <a href="https://calendly.com/jabriel-arisolutionsinc/30min" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
                    Book a Demo
                  </a>
                </li>
              </ul>
            </div>
          </div>
          
          <div className="pt-8 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-gray-500">
              © {new Date().getFullYear()} Ari Solutions Inc. All rights reserved.
            </p>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <Link to="/privacy" className="hover:text-white transition-colors">Privacy</Link>
              <Link to="/terms" className="hover:text-white transition-colors">Terms</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
