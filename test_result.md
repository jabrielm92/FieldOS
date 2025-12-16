# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

#====================================================================================================
# Testing Data
#====================================================================================================

user_problem_statement: >
  FieldOS - Multi-tenant Revenue & Operations OS for field service companies.
  New modules implemented:
  1. Quotes & Invoices page with tabs, stats, CRUD, detail modals, status updates
  2. Campaigns module with types (Reactivation, Tuneup, Special Offer), multi-step creation, recipient tracking, analytics

backend:
  - task: "Invoice CRUD API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET/POST /invoices, PUT /invoices/{id}, POST /invoices/{id}/mark-paid"

  - task: "Campaign API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET/POST /campaigns, PUT /campaigns/{id} for status changes"

frontend:
  - task: "Quotes & Invoices Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/quotes/QuotesPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Tabs for Quotes/Invoices, stats cards, create dialogs, detail modals, status updates, mark paid"

  - task: "Campaigns Page"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/campaigns/CampaignsPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Campaign cards with progress, multi-step creation, detail modal with tabs (Overview/Recipients/Analytics)"

metadata:
  created_by: "main_agent"
  version: "4.0"
  test_sequence: 5
  run_ui: true

test_plan:
  current_focus: "Test Quotes & Invoices module and Campaigns module"
  blocked_features: []
  test_all: true

credentials:
  tenant_owner:
    email: "owner@radiancehvac.com"
    password: "owner123"
