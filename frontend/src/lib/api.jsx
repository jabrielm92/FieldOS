import axios from 'axios';
import { authStorage } from './authStorage';

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || '').trim();
const API_BASE = BACKEND_URL ? `${BACKEND_URL}/api/v1` : '/api/v1';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = authStorage.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      authStorage.clearAll();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
};

// Admin APIs (Superadmin)
export const adminAPI = {
  getTenants: () => api.get('/admin/tenants'),
  createTenant: (data) => api.post('/admin/tenants', data),
  getTenantDetail: (tenantId) => api.get(`/admin/tenants/${tenantId}`),
  updateTenant: (tenantId, data) => api.put(`/admin/tenants/${tenantId}`, data),
  deleteTenant: (tenantId) => api.delete(`/admin/tenants/${tenantId}`),
  getTenantStorage: (tenantId) => api.get(`/admin/tenants/${tenantId}/storage`),
  testVoiceAI: (tenantId) => api.post(`/admin/tenants/${tenantId}/test-voice`),
};

// Settings APIs
export const settingsAPI = {
  getTenantSettings: () => api.get('/settings/tenant'),
  updateTenantSettings: (data) => api.put('/settings/tenant', data),
  getReviewSettings: () => api.get('/settings/reviews'),
  updateReviewSettings: (data) => api.put('/settings/reviews', data),
  getBrandingSettings: () => api.get('/settings/branding'),
  updateBrandingSettings: (data) => api.put('/settings/branding', data),
};

// Customer APIs
export const customerAPI = {
  list: (filters = {}) => api.get('/customers', { params: filters }),
  get: (id) => api.get(`/customers/${id}`),
  create: (data) => api.post('/customers', data),
  update: (id, data) => api.put(`/customers/${id}`, data),
  delete: (id) => api.delete(`/customers/${id}`),
  bulkDelete: (ids) => api.post('/customers/bulk-delete', ids),
};

// Property APIs
export const propertyAPI = {
  list: (customerId) => api.get('/properties', { params: { customer_id: customerId } }),
  get: (id) => api.get(`/properties/${id}`),
  create: (data) => api.post('/properties', data),
  update: (id, data) => api.put(`/properties/${id}`, data),
  delete: (id) => api.delete(`/properties/${id}`),
};

// Technician APIs
export const technicianAPI = {
  list: () => api.get('/technicians'),
  create: (data) => api.post('/technicians', data),
  update: (id, data) => api.put(`/technicians/${id}`, data),
};

// Lead APIs
export const leadAPI = {
  list: (filters = {}) => api.get('/leads', { params: filters }),
  get: (id) => api.get(`/leads/${id}`),
  getWithConversation: (id) => api.get(`/leads/${id}`), // Returns lead with customer, conversation, and messages
  create: (data) => api.post('/leads', data),
  update: (id, data) => api.put(`/leads/${id}`, data),
  delete: (id) => api.delete(`/leads/${id}`),
  bulkDelete: (ids) => api.post('/leads/bulk-delete', ids),
};

// Job APIs
export const jobAPI = {
  list: (filters = {}) => api.get('/jobs', { params: filters }),
  get: (id) => api.get(`/jobs/${id}`),
  create: (data) => api.post('/jobs', data),
  update: (id, data) => api.put(`/jobs/${id}`, data),
  markEnRoute: (id, data = {}) => api.post(`/jobs/${id}/en-route`, data),
  markArrived: (id) => api.post(`/jobs/${id}/arrived`),
  complete: (id, data) => api.post(`/jobs/${id}/complete`, data),
  bulkDelete: (ids) => api.post('/jobs/bulk-delete', ids),
  sendOnMyWay: (id, data) => api.post(`/jobs/${id}/on-my-way`, data),
  requestReview: (id, data) => api.post(`/jobs/${id}/request-review`, data),
};

// Quote APIs
export const quoteAPI = {
  list: (filters = {}) => api.get('/quotes', { params: filters }),
  get: (id) => api.get(`/quotes/${id}`),
  create: (data) => api.post('/quotes', data),
  update: (id, data) => api.put(`/quotes/${id}`, data),
  convertToInvoice: (id, data) => api.post(`/quotes/${id}/convert-to-invoice`, data),
};

// Invoice APIs
export const invoiceAPI = {
  list: (filters = {}) => api.get('/invoices', { params: filters }),
  get: (id) => api.get(`/invoices/${id}`),
  create: (data) => api.post('/invoices', data),
  update: (id, data) => api.put(`/invoices/${id}`, data),
  markPaid: (id) => api.post(`/invoices/${id}/mark-paid`),
  createPaymentLink: (id) => api.post(`/invoices/${id}/payment-link`),
  sendPaymentLink: (id) => api.post(`/invoices/${id}/send-payment-link`),
  getOverdue: () => api.get('/invoices/overdue'),
  getInvoiceSettings: () => api.get('/settings/invoice'),
  updateInvoiceSettings: (data) => api.put('/settings/invoice', data),
  send: (id) => api.post(`/invoices/${id}/send`),
  remind: (id) => api.post(`/invoices/${id}/remind`),
  recordPayment: (id, data) => api.post(`/invoices/${id}/record-payment`, data),
  voidInvoice: (id) => api.post(`/invoices/${id}/void`),
  deleteInvoice: (id) => api.delete(`/invoices/${id}`),
};

// Public invoice payment (no auth)
export const publicInvoiceAPI = {
  getByToken: (token) =>
    axios.get(`${BACKEND_URL || ''}/api/v1/invoices/public/${token}`),
};

// Reports APIs
export const reportsAPI = {
  getRevenue: (params = {}) => api.get('/reports/revenue', { params }),
};

// Templates APIs
export const templatesAPI = {
  getIndustries: () => api.get('/templates/industries'),
  getIndustry: (industry) => api.get(`/templates/industries/${industry}`),
};

// Custom Fields APIs
export const customFieldsAPI = {
  list: () => api.get('/settings/custom-fields'),
  create: (data) => api.post('/settings/custom-fields', data),
  update: (id, data) => api.put(`/settings/custom-fields/${id}`, data),
  delete: (id) => api.delete(`/settings/custom-fields/${id}`),
};

// Industry Settings APIs
export const industryAPI = {
  getSettings: () => api.get('/settings/industry'),
  updateSettings: (data) => api.put('/settings/industry', data),
  getTemplates: () => api.get('/templates/industries'),
  getTemplate: (slug) => api.get(`/templates/industries/${slug}`),
};

// Conversation APIs
export const conversationAPI = {
  list: (filters = {}) => api.get('/conversations', { params: filters }),
  get: (id) => api.get(`/conversations/${id}`),
  getMessages: (id) => api.get(`/conversations/${id}/messages`),
  sendMessage: (data) => api.post('/messages', data),
  delete: (id) => api.delete(`/conversations/${id}`),
  bulkDelete: (ids) => api.post('/conversations/bulk-delete', ids),
};

// Campaign APIs
export const campaignAPI = {
  list: () => api.get('/campaigns'),
  create: (data) => api.post('/campaigns', data),
  update: (id, data) => api.put(`/campaigns/${id}`, data),
  delete: (id) => api.delete(`/campaigns/${id}`),
  bulkDelete: (ids) => api.post('/campaigns/bulk-delete', ids),
  previewSegment: (id, segment) => api.post(`/campaigns/${id}/preview-segment`, segment),
  start: (id) => api.post(`/campaigns/${id}/start`),
  startWithCustomers: (id, customerIds) => api.post(`/campaigns/${id}/start-with-customers`, customerIds),
  sendBatch: (id, batchSize = 10) => api.post(`/campaigns/${id}/send-batch`, null, { params: { batch_size: batchSize } }),
  getStats: (id) => api.get(`/campaigns/${id}/stats`),
  getMessages: (id) => api.get(`/campaigns/${id}/messages`),
  getCustomersForSelection: (params) => api.get('/campaigns/customers-for-selection', { params }),
};

// Dispatch APIs
export const dispatchAPI = {
  getBoard: (date) => api.get('/dispatch/board', { params: { date } }),
  assignJob: (jobId, technicianId) => api.post('/dispatch/assign', null, { params: { job_id: jobId, technician_id: technicianId } }),
};

// Dashboard & Reports APIs
export const dashboardAPI = {
  get: () => api.get('/dashboard'),
  getReports: (params = {}) => api.get('/reports/summary', { params }),
};

// Voice AI Settings APIs
export const voiceSettingsAPI = {
  get: () => api.get('/settings/voice'),
  update: (data) => api.put('/settings/voice', data),
};

// Public APIs (no auth)
const BACKEND_URL_PUBLIC = (import.meta.env.VITE_BACKEND_URL || '').trim();
export const publicAPI = {
  getTracking: (token) =>
    axios.get(`${BACKEND_URL_PUBLIC || ''}/api/track/${token}`),
};

export default api;
