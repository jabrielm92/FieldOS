import { createContext, useContext, useEffect, useState } from 'react';
import { settingsAPI } from '@/lib/api';

const BrandingContext = createContext(null);

const DEFAULTS = {
  logo_url: null,
  company_name: 'FieldOS',
  primary_color: '#0066CC',
  secondary_color: '#004499',
  accent_color: '#FF6600',
  text_on_primary: '#FFFFFF',
  portal_title: 'Customer Portal',
  portal_welcome_message: 'Welcome to your customer portal',
  white_label_enabled: false,
};

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState(DEFAULTS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadBranding = async () => {
      try {
        const res = await settingsAPI.getBrandingSettings();
        const data = { ...DEFAULTS, ...res.data };
        setBranding(data);
        applyBrandingCSS(data);
      } catch {
        // Use defaults on error
      } finally {
        setLoading(false);
      }
    };
    loadBranding();
  }, []);

  const applyBrandingCSS = (data) => {
    const root = document.documentElement;
    if (data.primary_color) root.style.setProperty('--brand-primary', data.primary_color);
    if (data.secondary_color) root.style.setProperty('--brand-secondary', data.secondary_color);
    if (data.accent_color) root.style.setProperty('--brand-accent', data.accent_color);
    if (data.text_on_primary) root.style.setProperty('--brand-text-on-primary', data.text_on_primary);
  };

  return (
    <BrandingContext.Provider value={{ branding, setBranding, applyBrandingCSS }}>
      {children}
    </BrandingContext.Provider>
  );
}

export const useBranding = () => useContext(BrandingContext);
