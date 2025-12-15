# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: 
##
## test_plan:
##   current_focus: "What is currently being tested"
##   blocked_features: ["List of features that can't be tested yet"]
##   test_all: false
##
# Usage Guidelines:
# 1. Main Agent Updates:
#    - Update this file before calling the testing agent
#    - Set `needs_retesting: true` for tasks that need verification
#    - Add detailed comments in status_history
#
# 2. Testing Agent Updates:
#    - Record test results in status_history
#    - Update `working` status based on test outcomes
#    - Increment stuck_count if the same issue persists
# 
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: >
  FieldOS - Multi-tenant Revenue & Operations OS for field service companies.
  Four new features being implemented:
  1. Background Job Reminders (day-before & morning-of SMS notifications)
  2. Tech Dispatch Board (visual job assignment UI with drag-and-drop)
  3. Reports/Analytics page (metrics and insights)
  4. Customer Self-Service Portal (view jobs, pay invoices, leave reviews/notes)

backend:
  - task: "Background Job Scheduler"
    implemented: true
    working: "NA"
    file: "/app/backend/scheduler.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Scheduler with day-before (4 PM), morning-of (7 AM) reminders implemented. Uses APScheduler with Twilio SMS."

  - task: "Dispatch Board API"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/v1/dispatch/board and POST /api/v1/dispatch/assign endpoints implemented"

  - task: "Analytics/Reports API"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/v1/analytics/overview endpoint with summary, conversion rates, daily trends, tech performance"

  - task: "Customer Portal API"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Portal endpoints: GET /portal/{token}, POST /portal/{token}/quote/respond, POST /portal/{token}/reschedule-request, POST /portal/{token}/review, POST /portal/{token}/add-note"

  - task: "Invoice CRUD API"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Full CRUD for invoices: GET/POST /api/v1/invoices, GET/PUT /api/v1/invoices/{id}, POST /api/v1/invoices/{id}/mark-paid"

frontend:
  - task: "Dispatch Board UI"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/dispatch/DispatchBoard.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Drag-and-drop dispatch board with technician columns, date picker, job cards with priority indicators"

  - task: "Reports/Analytics UI"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/reports/ReportsPage.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Full analytics page with KPI cards, conversion rates, line/bar/pie charts using Recharts"

  - task: "Customer Portal UI"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/portal/CustomerPortal.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Portal page with upcoming/past appointments, pending invoices, quotes, reviews (star rating), send message/note feature"

  - task: "Route and Navigation Updates"
    implemented: true
    working: true
    file: "/app/frontend/src/App.js, /app/frontend/src/components/layout/Sidebar.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Routes added for /dispatch, /reports, /portal/:token. Sidebar updated with Dispatch and Reports links. Verified via screenshots."

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 3
  run_ui: true

test_plan:
  current_focus: "Test all 4 new features: Dispatch Board, Reports, Customer Portal, and Background Reminders"
  blocked_features: []
  test_all: true

credentials:
  superadmin:
    email: "admin@fieldos.app"
    password: "admin123"
  tenant_owner:
    email: "owner@radiancehvac.com"
    password: "owner123"
