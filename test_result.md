# Testing Data

user_problem_statement: >
  FieldOS - Multi-tenant app. Added bulk delete functionality with checkboxes:
  - Leads page: checkbox selection + bulk delete
  - Jobs page: checkbox selection + bulk delete
  - Customers page: checkbox selection + bulk delete (cascade deletes related data)
  - Calendar: uses jobs so already covered

backend:
  - task: "Bulk Delete APIs"
    implemented: true
    working: true
    priority: "high"
    needs_retesting: true

frontend:
  - task: "Leads Bulk Delete UI"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/leads/LeadsPage.js"
    priority: "high"
    needs_retesting: true

  - task: "Jobs Bulk Delete UI"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/jobs/JobsPage.js"
    priority: "high"
    needs_retesting: true

  - task: "Customers Bulk Delete UI"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/customers/CustomersPage.js"
    priority: "high"
    needs_retesting: true

metadata:
  created_by: "main_agent"
  version: "7.0"
  test_sequence: 8
  run_ui: true

test_plan:
  current_focus: "Test bulk delete functionality on Leads, Jobs, Customers pages"
  blocked_features: []
  test_all: true

credentials:
  tenant_owner:
    email: "owner@radiancehvac.com"
    password: "owner123"
