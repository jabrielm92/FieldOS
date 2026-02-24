import { Link } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Zap, ArrowLeft } from "lucide-react";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#0a0f1a] text-white">
      {/* Navigation */}
      <nav className="border-b border-white/10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold">FieldOS</span>
            </Link>
            <Link to="/">
              <Button variant="ghost" className="text-gray-300 hover:text-white">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h1 className="text-4xl font-black mb-8">Terms of Service</h1>
        <p className="text-gray-400 mb-8">Last updated: January 2026</p>

        <div className="prose prose-invert prose-gray max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">1. Agreement to Terms</h2>
            <p className="text-gray-300 leading-relaxed">
              By accessing or using FieldOS, a service provided by Ari Solutions Inc., you agree to be 
              bound by these Terms of Service. If you do not agree to these terms, please do not use 
              our service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">2. Description of Service</h2>
            <p className="text-gray-300 leading-relaxed">
              FieldOS is a cloud-based field service management platform that provides AI-powered 
              call handling, scheduling, customer management, quoting, invoicing, and marketing 
              automation tools for field service businesses.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">3. User Accounts</h2>
            <p className="text-gray-300 leading-relaxed mb-4">When creating an account, you agree to:</p>
            <ul className="list-disc pl-6 space-y-2 text-gray-300">
              <li>Provide accurate and complete information</li>
              <li>Maintain the security of your account credentials</li>
              <li>Notify us immediately of any unauthorized access</li>
              <li>Accept responsibility for all activities under your account</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">4. Acceptable Use</h2>
            <p className="text-gray-300 leading-relaxed mb-4">You agree not to:</p>
            <ul className="list-disc pl-6 space-y-2 text-gray-300">
              <li>Use the service for any illegal purpose</li>
              <li>Violate any laws or regulations</li>
              <li>Infringe on intellectual property rights</li>
              <li>Transmit malware or malicious code</li>
              <li>Attempt to gain unauthorized access to our systems</li>
              <li>Interfere with or disrupt the service</li>
              <li>Use the service to send spam or unsolicited communications</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">5. Payment Terms</h2>
            <p className="text-gray-300 leading-relaxed">
              Subscription fees are billed in advance on a monthly basis. All fees are non-refundable 
              except as required by law. We reserve the right to change pricing with 30 days notice. 
              Failure to pay may result in suspension or termination of service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">6. Data Ownership</h2>
            <p className="text-gray-300 leading-relaxed">
              You retain all rights to your data. By using our service, you grant us a limited license 
              to use your data solely to provide and improve our services. We will not sell or share 
              your data with third parties except as described in our Privacy Policy.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">7. Service Availability</h2>
            <p className="text-gray-300 leading-relaxed">
              We strive to maintain 99.9% uptime but do not guarantee uninterrupted service. We may 
              perform maintenance that temporarily affects availability. We are not liable for any 
              damages resulting from service interruptions.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">8. Limitation of Liability</h2>
            <p className="text-gray-300 leading-relaxed">
              To the maximum extent permitted by law, Ari Solutions Inc. shall not be liable for any 
              indirect, incidental, special, consequential, or punitive damages, including loss of 
              profits, data, or business opportunities, arising from your use of the service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">9. Indemnification</h2>
            <p className="text-gray-300 leading-relaxed">
              You agree to indemnify and hold harmless Ari Solutions Inc. and its officers, directors, 
              employees, and agents from any claims, damages, losses, or expenses arising from your 
              use of the service or violation of these terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">10. Termination</h2>
            <p className="text-gray-300 leading-relaxed">
              Either party may terminate this agreement with 30 days written notice. We may suspend 
              or terminate your account immediately for violation of these terms. Upon termination, 
              your right to use the service ceases, and we may delete your data after a reasonable 
              retention period.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">11. Changes to Terms</h2>
            <p className="text-gray-300 leading-relaxed">
              We may modify these terms at any time. We will notify you of material changes via email 
              or through the service. Continued use after changes constitutes acceptance of the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">12. Governing Law</h2>
            <p className="text-gray-300 leading-relaxed">
              These terms shall be governed by the laws of the State of Delaware, without regard to 
              conflict of law principles. Any disputes shall be resolved in the courts of Delaware.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold mb-4 text-white">13. Contact</h2>
            <p className="text-gray-300 leading-relaxed">
              For questions about these Terms of Service, please contact us at:
            </p>
            <p className="text-blue-400 mt-2">
              <a href="mailto:fieldos@arisolutionsinc.com">fieldos@arisolutionsinc.com</a>
            </p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-500">
          © {new Date().getFullYear()} Ari Solutions Inc. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
