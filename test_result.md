# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

#====================================================================================================
# Testing Data
#====================================================================================================

user_problem_statement: >
  FieldOS - Multi-tenant Revenue & Operations OS for field service companies.
  Features implemented:
  1. Calendar - Add/edit job functionality with modals
  2. Inbox/Conversations - Enhanced SMS view with Vapi call summaries
  3. Quotes - Import from Lead/Vapi Call integration

backend:
  - task: "All backend APIs"
    implemented: true
    working: true
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "All APIs working - campaigns, jobs, conversations, quotes"

frontend:
  - task: "Calendar Add/Edit Job"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/calendar/CalendarPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "CreateJobModal and EditJobModal added. Can schedule new jobs and edit existing ones."

  - task: "Inbox/Conversations Enhanced"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/conversations/ConversationsPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Enhanced with Vapi call summary display, auto-refresh, improved message bubbles"

  - task: "Quotes Lead Import"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/quotes/QuotesPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Added Import from Lead/Vapi Call feature to pre-fill quote description"

metadata:
  created_by: "main_agent"
  version: "6.0"
  test_sequence: 7
  run_ui: true

test_plan:
  current_focus: "Test Calendar job creation, Inbox messaging, Quote lead import"
  blocked_features: []
  test_all: true

credentials:
  tenant_owner:
    email: "owner@radiancehvac.com"
    password: "owner123"
