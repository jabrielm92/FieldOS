# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

#====================================================================================================
# Testing Data
#====================================================================================================

user_problem_statement: >
  FieldOS - Multi-tenant Revenue & Operations OS for field service companies.
  Bug fixes and enhancements needed:
  1. Campaign creation failure - Fixed by sending segment_definition as object instead of string
  2. Property edit functionality - Added edit button and form to customer detail modal
  3. Reports page chart labels - Added axis labels and improved tooltips
  4. Jobs page - Already has unassign and status change functionality

backend:
  - task: "Campaign Creation API Fix"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/campaigns/CampaignsPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Fixed segment_definition to send as object, not string"

  - task: "Property Update API"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "PUT /properties/{id} endpoint already exists and working"

frontend:
  - task: "Campaign Creation UI"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/campaigns/CampaignsPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Campaign creation now works - tested via UI, creates and displays campaigns"

  - task: "Property Edit UI"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/customers/CustomersPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Added PropertyCard component with edit functionality"

  - task: "Reports Page Labels"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/reports/ReportsPage.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Added axis labels (Count, Date, Jobs Completed) to charts"

metadata:
  created_by: "main_agent"
  version: "5.0"
  test_sequence: 6
  run_ui: true

test_plan:
  current_focus: "Test Campaign creation, Property editing, Reports labels"
  blocked_features: []
  test_all: true

credentials:
  tenant_owner:
    email: "owner@radiancehvac.com"
    password: "owner123"
