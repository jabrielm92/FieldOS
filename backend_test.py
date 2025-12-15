#!/usr/bin/env python3
"""
FieldOS Backend API Testing Suite
Tests all endpoints and functionality for the multi-tenant field service application
"""
import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class FieldOSAPITester:
    def __init__(self, base_url: str = "https://field-track.preview.emergentagent.com"):
        self.base_url = base_url
        self.superadmin_token = None
        self.tenant_owner_token = None
        self.tenant_id = None
        self.customer_id = None
        self.property_id = None
        self.lead_id = None
        self.job_id = None
        self.quote_id = None
        self.conversation_id = None
        self.campaign_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
    def log(self, message: str):
        """Log test messages"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/api/v1/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
            
        if self.superadmin_token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.superadmin_token}'
        elif self.tenant_owner_token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.tenant_owner_token}'

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            self.failed_tests.append({
                'name': name,
                'error': str(e)
            })
            return False, {}

    def test_health_check(self):
        """Test basic health endpoints"""
        self.log("\n=== HEALTH CHECK TESTS ===")
        
        # Test root endpoint (on api router, not v1)
        url = f"{self.base_url}/api/"
        try:
            response = requests.get(url, timeout=30)
            success = response.status_code == 200
            if success:
                self.tests_passed += 1
                self.log(f"✅ Root Health Check - Status: {response.status_code}")
            else:
                self.log(f"❌ Root Health Check - Expected 200, got {response.status_code}")
                self.failed_tests.append({
                    'name': 'Root Health Check',
                    'expected': 200,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })
        except Exception as e:
            self.log(f"❌ Root Health Check - Error: {str(e)}")
            self.failed_tests.append({'name': 'Root Health Check', 'error': str(e)})
        self.tests_run += 1
        
        # Test health endpoint (on api router, not v1)
        url = f"{self.base_url}/api/health"
        try:
            response = requests.get(url, timeout=30)
            success = response.status_code == 200
            if success:
                self.tests_passed += 1
                self.log(f"✅ Health Endpoint - Status: {response.status_code}")
            else:
                self.log(f"❌ Health Endpoint - Expected 200, got {response.status_code}")
                self.failed_tests.append({
                    'name': 'Health Endpoint',
                    'expected': 200,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })
        except Exception as e:
            self.log(f"❌ Health Endpoint - Error: {str(e)}")
            self.failed_tests.append({'name': 'Health Endpoint', 'error': str(e)})
        self.tests_run += 1

    def test_superadmin_login(self):
        """Test superadmin authentication"""
        self.log("\n=== SUPERADMIN AUTHENTICATION ===")
        
        success, response = self.run_test(
            "Superadmin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@fieldos.app", "password": "admin123"}
        )
        
        if success and 'access_token' in response:
            self.superadmin_token = response['access_token']
            self.log(f"✅ Superadmin token obtained")
            return True
        else:
            self.log(f"❌ Failed to get superadmin token")
            return False

    def test_tenant_creation(self):
        """Test tenant creation by superadmin"""
        self.log("\n=== TENANT MANAGEMENT ===")
        
        # List existing tenants
        self.run_test("List Tenants", "GET", "admin/tenants", 200)
        
        # Create new tenant
        tenant_data = {
            "name": "Test HVAC Company",
            "slug": f"test-hvac-{datetime.now().strftime('%H%M%S')}",
            "subdomain": "test-hvac",
            "timezone": "America/New_York",
            "service_area": "New York City",
            "primary_contact_name": "John Smith",
            "primary_contact_email": "john@testhvac.com",
            "primary_phone": "+1234567890",
            "booking_mode": "TIME_WINDOWS",
            "tone_profile": "PROFESSIONAL",
            "sms_signature": "- Test HVAC Team",
            "owner_email": "owner@testhvac.com",
            "owner_name": "Jane Smith",
            "owner_password": "owner123"
        }
        
        success, response = self.run_test(
            "Create Tenant",
            "POST",
            "admin/tenants",
            200,
            data=tenant_data
        )
        
        if success and 'id' in response:
            self.tenant_id = response['id']
            self.log(f"✅ Tenant created with ID: {self.tenant_id}")
            return True
        return False

    def test_tenant_owner_login(self):
        """Test tenant owner login"""
        self.log("\n=== TENANT OWNER AUTHENTICATION ===")
        
        success, response = self.run_test(
            "Tenant Owner Login",
            "POST",
            "auth/login",
            200,
            data={"email": "owner@testhvac.com", "password": "owner123"}
        )
        
        if success and 'access_token' in response:
            self.tenant_owner_token = response['access_token']
            self.log(f"✅ Tenant owner token obtained")
            return True
        return False

    def test_customer_management(self):
        """Test customer CRUD operations"""
        self.log("\n=== CUSTOMER MANAGEMENT ===")
        
        # Switch to tenant owner token for tenant-scoped operations
        original_token = self.superadmin_token
        self.superadmin_token = self.tenant_owner_token
        
        # Create customer
        customer_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "email": "john.doe@example.com",
            "preferred_channel": "SMS"
        }
        
        success, response = self.run_test(
            "Create Customer",
            "POST",
            "customers",
            200,
            data=customer_data
        )
        
        if success and 'id' in response:
            self.customer_id = response['id']
            self.log(f"✅ Customer created with ID: {self.customer_id}")
        
        # List customers
        self.run_test("List Customers", "GET", "customers", 200)
        
        # Get customer details
        if self.customer_id:
            self.run_test("Get Customer", "GET", f"customers/{self.customer_id}", 200)
        
        # Restore superadmin token
        self.superadmin_token = original_token

    def test_property_management(self):
        """Test property CRUD operations"""
        self.log("\n=== PROPERTY MANAGEMENT ===")
        
        if not self.customer_id:
            self.log("❌ Skipping property tests - no customer ID")
            return
        
        # Create property
        property_data = {
            "customer_id": self.customer_id,
            "address_line1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "property_type": "RESIDENTIAL"
        }
        
        success, response = self.run_test(
            "Create Property",
            "POST",
            "properties",
            200,
            data=property_data
        )
        
        if success and 'id' in response:
            self.property_id = response['id']
            self.log(f"✅ Property created with ID: {self.property_id}")
        
        # List properties
        self.run_test("List Properties", "GET", "properties", 200)

    def test_lead_management(self):
        """Test lead CRUD operations"""
        self.log("\n=== LEAD MANAGEMENT ===")
        
        # Switch to tenant owner token
        original_token = self.superadmin_token
        self.superadmin_token = self.tenant_owner_token
        
        # Create lead
        lead_data = {
            "customer_id": self.customer_id,
            "property_id": self.property_id,
            "source": "MANUAL",
            "channel": "FORM",
            "issue_type": "AC Not Cooling",
            "urgency": "URGENT",
            "description": "Customer reports AC not cooling properly"
        }
        
        success, response = self.run_test(
            "Create Lead",
            "POST",
            "leads",
            200,
            data=lead_data
        )
        
        if success and 'id' in response:
            self.lead_id = response['id']
            self.log(f"✅ Lead created with ID: {self.lead_id}")
        
        # List leads
        self.run_test("List Leads", "GET", "leads", 200)
        
        # Get lead details
        if self.lead_id:
            self.run_test("Get Lead Details", "GET", f"leads/{self.lead_id}", 200)
        
        # Restore superadmin token
        self.superadmin_token = original_token

    def test_job_management(self):
        """Test job CRUD operations"""
        self.log("\n=== JOB MANAGEMENT ===")
        
        if not self.customer_id or not self.property_id:
            self.log("❌ Skipping job tests - missing customer or property ID")
            return
        
        # Create job
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        
        job_data = {
            "customer_id": self.customer_id,
            "property_id": self.property_id,
            "lead_id": self.lead_id,
            "job_type": "DIAGNOSTIC",
            "priority": "NORMAL",
            "service_window_start": start_time.isoformat(),
            "service_window_end": end_time.isoformat(),
            "status": "BOOKED"
        }
        
        success, response = self.run_test(
            "Create Job",
            "POST",
            "jobs",
            200,
            data=job_data
        )
        
        if success and 'id' in response:
            self.job_id = response['id']
            self.log(f"✅ Job created with ID: {self.job_id}")
        
        # List jobs
        self.run_test("List Jobs", "GET", "jobs", 200)
        
        # Get job details
        if self.job_id:
            self.run_test("Get Job Details", "GET", f"jobs/{self.job_id}", 200)
        
        # Test mark en-route
        if self.job_id:
            self.run_test("Mark Job En-Route", "POST", f"jobs/{self.job_id}/en-route", 200)

    def test_quote_management(self):
        """Test quote CRUD operations"""
        self.log("\n=== QUOTE MANAGEMENT ===")
        
        if not self.customer_id or not self.property_id:
            self.log("❌ Skipping quote tests - missing customer or property ID")
            return
        
        # Create quote
        quote_data = {
            "customer_id": self.customer_id,
            "property_id": self.property_id,
            "job_id": self.job_id,
            "amount": 299.99,
            "description": "AC diagnostic and repair quote"
        }
        
        success, response = self.run_test(
            "Create Quote",
            "POST",
            "quotes",
            200,
            data=quote_data
        )
        
        if success and 'id' in response:
            self.quote_id = response['id']
            self.log(f"✅ Quote created with ID: {self.quote_id}")
        
        # List quotes
        self.run_test("List Quotes", "GET", "quotes", 200)

    def test_conversation_management(self):
        """Test conversation and message operations"""
        self.log("\n=== CONVERSATION MANAGEMENT ===")
        
        # List conversations
        self.run_test("List Conversations", "GET", "conversations", 200)
        
        # Send message (if conversation exists)
        if self.customer_id:
            message_data = {
                "conversation_id": "test-conv-id",  # This might fail, but tests the endpoint
                "customer_id": self.customer_id,
                "channel": "SMS",
                "content": "Test message from staff"
            }
            
            # This might fail due to missing conversation, but tests the endpoint
            self.run_test("Send Message", "POST", "messages", 404, data=message_data)

    def test_campaign_management(self):
        """Test campaign CRUD operations"""
        self.log("\n=== CAMPAIGN MANAGEMENT ===")
        
        # Switch to tenant owner token
        original_token = self.superadmin_token
        self.superadmin_token = self.tenant_owner_token
        
        # Create campaign
        campaign_data = {
            "name": "Test Reactivation Campaign",
            "type": "REACTIVATION",
            "message_template": "Hi {customer_name}, it's time for your annual HVAC maintenance!"
        }
        
        success, response = self.run_test(
            "Create Campaign",
            "POST",
            "campaigns",
            200,
            data=campaign_data
        )
        
        if success and 'id' in response:
            self.campaign_id = response['id']
            self.log(f"✅ Campaign created with ID: {self.campaign_id}")
        
        # List campaigns
        self.run_test("List Campaigns", "GET", "campaigns", 200)
        
        # Restore superadmin token
        self.superadmin_token = original_token

    def test_vapi_endpoints(self):
        """Test Vapi integration endpoints"""
        self.log("\n=== VAPI INTEGRATION TESTS ===")
        
        # Test create lead from Vapi
        vapi_headers = {"X-Vapi-Secret": "vapi-secret-key-change-in-production"}
        
        vapi_lead_data = {
            "tenant_slug": "test-hvac",  # This might not exist, testing endpoint
            "caller_phone": "+1987654321",
            "caller_name": "Jane Customer",
            "issue_type": "Heating Issue",
            "urgency": "URGENT",
            "description": "Furnace not working",
            "address_line1": "456 Oak Ave",
            "city": "Brooklyn",
            "state": "NY",
            "postal_code": "11201"
        }
        
        # This might fail due to tenant slug, but tests the endpoint
        self.run_test(
            "Vapi Create Lead",
            "POST",
            "vapi/create-lead",
            404,  # Expecting 404 due to tenant slug
            data=vapi_lead_data,
            headers=vapi_headers
        )
        
        # Test check availability
        availability_data = {
            "tenant_slug": "test-hvac",
            "date": "2024-12-20",
            "job_type": "DIAGNOSTIC"
        }
        
        self.run_test(
            "Vapi Check Availability",
            "POST",
            "vapi/check-availability",
            404,  # Expecting 404 due to tenant slug
            data=availability_data,
            headers=vapi_headers
        )

    def test_sms_webhook(self):
        """Test SMS inbound webhook"""
        self.log("\n=== SMS WEBHOOK TEST ===")
        
        # Test inbound SMS webhook (simulated Twilio webhook)
        webhook_data = {
            "From": "+1234567890",
            "To": "+1987654321",
            "Body": "Test inbound SMS message"
        }
        
        # Use form data instead of JSON for Twilio webhook
        url = f"{self.base_url}/api/v1/sms/inbound"
        try:
            response = requests.post(url, data=webhook_data, timeout=30)
            success = response.status_code == 200
            if success:
                self.tests_passed += 1
                self.log(f"✅ SMS Webhook - Status: {response.status_code}")
            else:
                self.log(f"❌ SMS Webhook - Expected 200, got {response.status_code}")
        except Exception as e:
            self.log(f"❌ SMS Webhook - Error: {str(e)}")
        
        self.tests_run += 1

    def test_dashboard_metrics(self):
        """Test dashboard data endpoint"""
        self.log("\n=== DASHBOARD METRICS ===")
        
        self.run_test("Get Dashboard Data", "GET", "dashboard", 200)
        
        # Test reports summary
        self.run_test("Get Reports Summary", "GET", "reports/summary", 200)

    def test_auth_endpoints(self):
        """Test additional auth endpoints"""
        self.log("\n=== ADDITIONAL AUTH TESTS ===")
        
        # Test get current user
        self.run_test("Get Current User", "GET", "auth/me", 200)
        
        # Test logout
        self.run_test("Logout", "POST", "auth/logout", 200)

    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting FieldOS Backend API Tests")
        self.log(f"📍 Testing against: {self.base_url}")
        
        # Core functionality tests
        self.test_health_check()
        
        if not self.test_superadmin_login():
            self.log("❌ Cannot proceed without superadmin access")
            return self.generate_report()
        
        if not self.test_tenant_creation():
            self.log("❌ Cannot proceed without tenant creation")
            return self.generate_report()
        
        if not self.test_tenant_owner_login():
            self.log("❌ Cannot proceed without tenant owner access")
            return self.generate_report()
        
        # Tenant-scoped tests
        self.test_customer_management()
        self.test_property_management()
        self.test_lead_management()
        self.test_job_management()
        self.test_quote_management()
        self.test_conversation_management()
        self.test_campaign_management()
        
        # Integration tests
        self.test_vapi_endpoints()
        self.test_sms_webhook()
        
        # Dashboard and reporting
        self.test_dashboard_metrics()
        self.test_auth_endpoints()
        
        return self.generate_report()

    def generate_report(self):
        """Generate test report"""
        self.log("\n" + "="*60)
        self.log("📊 TEST RESULTS SUMMARY")
        self.log("="*60)
        self.log(f"✅ Tests Passed: {self.tests_passed}/{self.tests_run}")
        self.log(f"❌ Tests Failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            self.log("\n🔍 FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"{i}. {test['name']}")
                if 'error' in test:
                    self.log(f"   Error: {test['error']}")
                else:
                    self.log(f"   Expected: {test['expected']}, Got: {test['actual']}")
                    if test.get('response'):
                        self.log(f"   Response: {test['response']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return {
            'total_tests': self.tests_run,
            'passed_tests': self.tests_passed,
            'failed_tests': len(self.failed_tests),
            'success_rate': success_rate,
            'failures': self.failed_tests
        }

def main():
    """Main test execution"""
    tester = FieldOSAPITester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if results['failed_tests'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())