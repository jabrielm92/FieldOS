import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api/v1`;

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fieldos_token');
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
      localStorage.removeItem('fieldos_token');
      localStorage.removeItem('fieldos_user');
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
};

// Customer APIs
export const customerAPI = {
  list: () => api.get('/customers'),
  get: (id) => api.get(`/customers/${id}`),
  create: (data) => api.post('/customers', data),
  update: (id, data) => api.put(`/customers/${id}`, data),
};

// Property APIs
export const propertyAPI = {
  list: (customerId) => api.get('/properties', { params: { customer_id: customerId } }),
  create: (data) => api.post('/properties', data),
  update: (id, data) => api.put(`/properties/${id}`, data),
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
  create: (data) => api.post('/leads', data),
  update: (id, data) => api.put(`/leads/${id}`, data),
  delete: (id) => api.delete(`/leads/${id}`),
};

// Job APIs
export const jobAPI = {
  list: (filters = {}) => api.get('/jobs', { params: filters }),
  get: (id) => api.get(`/jobs/${id}`),
  create: (data) => api.post('/jobs', data),
  update: (id, data) => api.put(`/jobs/${id}`, data),
  markEnRoute: (id) => api.post(`/jobs/${id}/en-route`),
};

// Quote APIs
export const quoteAPI = {
  list: (filters = {}) => api.get('/quotes', { params: filters }),
  get: (id) => api.get(`/quotes/${id}`),
  create: (data) => api.post('/quotes', data),
  update: (id, data) => api.put(`/quotes/${id}`, data),
};

// Invoice APIs
export const invoiceAPI = {
  list: (filters = {}) => api.get('/invoices', { params: filters }),
  get: (id) => api.get(`/invoices/${id}`),
  create: (data) => api.post('/invoices', data),
  update: (id, data) => api.put(`/invoices/${id}`, data),
  markPaid: (id) => api.post(`/invoices/${id}/mark-paid`),
};

// Conversation APIs
export const conversationAPI = {
  list: (filters = {}) => api.get('/conversations', { params: filters }),
  get: (id) => api.get(`/conversations/${id}`),
  getMessages: (id) => api.get(`/conversations/${id}/messages`),
  sendMessage: (data) => api.post('/messages', data),
};

// Campaign APIs
export const campaignAPI = {
  list: () => api.get('/campaigns'),
  create: (data) => api.post('/campaigns', data),
  update: (id, data) => api.put(`/campaigns/${id}`, data),
};

// Dispatch APIs
export const dispatchAPI = {
  getBoard: (date) => api.get('/dispatch/board', { params: { date } }),
  assignJob: (jobId, technicianId) => api.post('/dispatch/assign', { job_id: jobId, technician_id: technicianId }),
};

// Dashboard & Reports APIs
export const dashboardAPI = {
  get: () => api.get('/dashboard'),
  getReports: (params = {}) => api.get('/reports/summary', { params }),
};

export default api;
