#!/usr/bin/env python3
"""
FieldOS Backend API Testing Suite - Quote Generation and Revenue Tracking
Tests specific quote generation and revenue tracking functionality
"""
import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class QuoteRevenueAPITester:
    def __init__(self, base_url: str = "https://fieldos-service.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tenant_id = None
        self.customer_id = None
        self.property_id = None
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
            
        if self.token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.token}'

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

    def test_login(self):
        """Test login with existing tenant credentials"""
        self.log("\n=== AUTHENTICATION ===")
        
        success, response = self.run_test(
            "Login with Existing Tenant",
            "POST",
            "auth/login",
            200,
            data={"email": "owner@radiancehvac.com", "password": "owner123"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.log(f"✅ Token obtained")
            # Get tenant ID from user response
            if 'user' in response and 'tenant_id' in response['user']:
                self.tenant_id = response['user']['tenant_id']
                self.log(f"✅ Using tenant ID: {self.tenant_id}")
            return True
        return False

    def setup_test_data(self):
        """Create test customer and property for testing"""
        self.log("\n=== SETUP TEST DATA ===")
        
        # Create customer
        customer_data = {
            "first_name": "Quote",
            "last_name": "TestCustomer",
            "phone": "+1234567890",
            "email": "quote.test@example.com",
            "preferred_channel": "SMS"
        }
        
        success, response = self.run_test(
            "Create Test Customer",
            "POST",
            "customers",
            200,
            data=customer_data
        )
        
        if success and 'id' in response:
            self.customer_id = response['id']
            self.log(f"✅ Test customer created: {self.customer_id}")
        else:
            return False
        
        # Create property
        property_data = {
            "customer_id": self.customer_id,
            "address_line1": "123 Quote Test St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "property_type": "RESIDENTIAL"
        }
        
        success, response = self.run_test(
            "Create Test Property",
            "POST",
            "properties",
            200,
            data=property_data
        )
        
        if success and 'id' in response:
            self.property_id = response['id']
            self.log(f"✅ Test property created: {self.property_id}")
            return True
        
        return False

    def test_quote_calculation(self):
        """Test quote calculation with different job types and urgencies"""
        self.log("\n=== QUOTE CALCULATION TESTS ===")
        
        if not self.customer_id or not self.property_id:
            self.log("❌ Skipping quote tests - missing test data")
            return
        
        # Test cases: (job_type, urgency, expected_base_price, expected_multiplier)
        test_cases = [
            ("DIAGNOSTIC", "EMERGENCY", 89.00, 1.5),
            ("DIAGNOSTIC", "URGENT", 89.00, 1.25),
            ("DIAGNOSTIC", "ROUTINE", 89.00, 1.0),
            ("REPAIR", "EMERGENCY", 250.00, 1.5),
            ("REPAIR", "URGENT", 250.00, 1.25),
            ("REPAIR", "ROUTINE", 250.00, 1.0),
            ("MAINTENANCE", "EMERGENCY", 149.00, 1.5),
            ("MAINTENANCE", "ROUTINE", 149.00, 1.0),
            ("INSTALLATION", "EMERGENCY", 1500.00, 1.5),
            ("INSTALLATION", "ROUTINE", 1500.00, 1.0)
        ]
        
        quote_tests_passed = 0
        
        for job_type, urgency, base_price, multiplier in test_cases:
            expected_quote = round(base_price * multiplier, 2)
            
            # Create lead with specific urgency
            lead_data = {
                "customer_id": self.customer_id,
                "property_id": self.property_id,
                "source": "MANUAL",
                "channel": "FORM",
                "issue_type": f"{job_type} Test",
                "urgency": urgency,
                "description": f"Test {job_type} with {urgency} urgency"
            }
            
            success, lead_response = self.run_test(
                f"Create Lead {job_type}-{urgency}",
                "POST",
                "leads",
                200,
                data=lead_data
            )
            
            if success and 'id' in lead_response:
                lead_id = lead_response['id']
                
                # Create job linked to this lead
                start_time = datetime.now() + timedelta(days=1)
                end_time = start_time + timedelta(hours=2)
                
                job_data = {
                    "customer_id": self.customer_id,
                    "property_id": self.property_id,
                    "lead_id": lead_id,
                    "job_type": job_type,
                    "priority": "EMERGENCY" if urgency == "EMERGENCY" else "HIGH" if urgency == "URGENT" else "NORMAL",
                    "service_window_start": start_time.isoformat(),
                    "service_window_end": end_time.isoformat(),
                    "status": "BOOKED"
                }
                
                success, job_response = self.run_test(
                    f"Create Job {job_type}-{urgency}",
                    "POST",
                    "jobs",
                    200,
                    data=job_data
                )
                
                if success and 'quote_amount' in job_response:
                    quote_amount = job_response['quote_amount']
                    self.log(f"✅ {job_type}-{urgency}: Quote ${quote_amount} (expected ${expected_quote})")
                    
                    if abs(quote_amount - expected_quote) < 0.01:
                        self.log(f"✅ Quote calculation CORRECT")
                        quote_tests_passed += 1
                    else:
                        self.log(f"❌ Quote calculation INCORRECT: expected ${expected_quote}, got ${quote_amount}")
                        self.failed_tests.append({
                            'name': f'Quote Calculation {job_type}-{urgency}',
                            'expected': expected_quote,
                            'actual': quote_amount,
                            'error': 'Quote amount mismatch'
                        })
                else:
                    self.log(f"❌ No quote amount in response for {job_type}-{urgency}")
                    self.failed_tests.append({
                        'name': f'Quote Generation {job_type}-{urgency}',
                        'error': 'No quote_amount field in response'
                    })
        
        self.log(f"\n📊 Quote Calculation Results: {quote_tests_passed}/{len(test_cases)} passed")

    def test_dashboard_revenue_metrics(self):
        """Test dashboard revenue metrics endpoint"""
        self.log("\n=== DASHBOARD REVENUE METRICS ===")
        
        success, response = self.run_test(
            "Dashboard Revenue Metrics",
            "GET",
            "dashboard",
            200
        )
        
        if success:
            metrics = response.get('metrics', {})
            required_fields = ['potential_revenue', 'completed_revenue', 'invoiced_revenue', 'total_estimated_revenue']
            
            missing_fields = []
            for field in required_fields:
                if field in metrics:
                    value = metrics[field]
                    self.log(f"✅ Dashboard has {field}: ${value}")
                else:
                    self.log(f"❌ Dashboard missing {field}")
                    missing_fields.append(field)
            
            if missing_fields:
                self.failed_tests.append({
                    'name': 'Dashboard Revenue Fields',
                    'error': f'Missing fields: {missing_fields}'
                })
            else:
                self.log("✅ All required dashboard revenue fields present")

    def test_analytics_revenue_breakdown(self):
        """Test analytics revenue breakdown endpoint"""
        self.log("\n=== ANALYTICS REVENUE BREAKDOWN ===")
        
        success, response = self.run_test(
            "Analytics Revenue Breakdown",
            "GET",
            "analytics/overview?period=30d",
            200
        )
        
        if success:
            summary = response.get('summary', {})
            required_fields = ['potential_revenue', 'job_completed_revenue', 'invoiced_revenue', 'total_revenue']
            
            missing_fields = []
            for field in required_fields:
                if field in summary:
                    value = summary[field]
                    self.log(f"✅ Analytics has {field}: ${value}")
                else:
                    self.log(f"❌ Analytics missing {field}")
                    missing_fields.append(field)
            
            if missing_fields:
                self.failed_tests.append({
                    'name': 'Analytics Revenue Fields',
                    'error': f'Missing fields: {missing_fields}'
                })
            else:
                self.log("✅ All required analytics revenue fields present")

    def test_job_creation_without_lead(self):
        """Test job creation without lead (should still calculate quote)"""
        self.log("\n=== JOB CREATION WITHOUT LEAD ===")
        
        if not self.customer_id or not self.property_id:
            self.log("❌ Skipping job creation test - missing test data")
            return
        
        # Create job without lead_id
        start_time = datetime.now() + timedelta(days=3)
        end_time = start_time + timedelta(hours=2)
        
        job_data = {
            "customer_id": self.customer_id,
            "property_id": self.property_id,
            "job_type": "REPAIR",
            "priority": "HIGH",  # Should map to URGENT urgency
            "service_window_start": start_time.isoformat(),
            "service_window_end": end_time.isoformat(),
            "status": "BOOKED"
        }
        
        success, response = self.run_test(
            "Create Job Without Lead",
            "POST",
            "jobs",
            200,
            data=job_data
        )
        
        if success and 'quote_amount' in response:
            quote_amount = response['quote_amount']
            # HIGH priority should map to URGENT (1.25 multiplier)
            expected_quote = round(250.00 * 1.25, 2)  # REPAIR base price * URGENT multiplier
            
            self.log(f"✅ Job without lead: Quote ${quote_amount} (expected ${expected_quote})")
            
            if abs(quote_amount - expected_quote) < 0.01:
                self.log(f"✅ Quote calculation for job without lead CORRECT")
            else:
                self.log(f"❌ Quote calculation INCORRECT: expected ${expected_quote}, got ${quote_amount}")
                self.failed_tests.append({
                    'name': 'Job Without Lead Quote Calculation',
                    'expected': expected_quote,
                    'actual': quote_amount,
                    'error': 'Quote amount mismatch for job without lead'
                })
        else:
            self.log(f"❌ No quote amount for job without lead")
            self.failed_tests.append({
                'name': 'Job Without Lead Quote Generation',
                'error': 'No quote_amount field in response'
            })

    def cleanup_test_data(self):
        """Clean up test data"""
        self.log("\n=== CLEANUP TEST DATA ===")
        
        if self.customer_id:
            success, response = self.run_test(
                "Delete Test Customer",
                "DELETE",
                f"customers/{self.customer_id}",
                200
            )
            if success:
                self.log("✅ Test customer deleted")

    def run_all_tests(self):
        """Run all quote and revenue tracking tests"""
        self.log("🚀 Starting Quote Generation & Revenue Tracking Tests")
        self.log(f"📍 Testing against: {self.base_url}")
        
        if not self.test_login():
            self.log("❌ Cannot proceed without authentication")
            return self.generate_report()
        
        if not self.setup_test_data():
            self.log("❌ Cannot proceed without test data setup")
            return self.generate_report()
        
        # Run specific tests
        self.test_quote_calculation()
        self.test_dashboard_revenue_metrics()
        self.test_analytics_revenue_breakdown()
        self.test_job_creation_without_lead()
        
        # Cleanup
        self.cleanup_test_data()
        
        return self.generate_report()

    def generate_report(self):
        """Generate test report"""
        self.log("\n" + "="*60)
        self.log("📊 QUOTE & REVENUE TRACKING TEST RESULTS")
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
    tester = QuoteRevenueAPITester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if results['failed_tests'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())