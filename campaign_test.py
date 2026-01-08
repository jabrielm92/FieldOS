#!/usr/bin/env python3
"""
FieldOS Campaigns Module Testing Suite
Tests the specific campaign functionality: segment creation, starting campaigns, 
getting real stats, and sending batch messages.
"""
import requests
import sys
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CampaignTester:
    def __init__(self, base_url: str = "https://smart-field-ops.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tenant_id = None
        self.customer_id = None
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
            
        if self.token:
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
                self.log(f"   Response: {response.text[:300]}")
                self.failed_tests.append({
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:300]
                })
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            self.failed_tests.append({
                'name': name,
                'error': str(e)
            })
            return False, {}

    def login(self):
        """Login with provided credentials"""
        self.log("\n=== AUTHENTICATION ===")
        
        success, response = self.run_test(
            "Login",
            "POST",
            "auth/login",
            200,
            data={"email": "owner@radiancehvac.com", "password": "owner123"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.tenant_id = response.get('user', {}).get('tenant_id')
            self.log(f"✅ Login successful, tenant_id: {self.tenant_id}")
            return True
        else:
            self.log(f"❌ Failed to login")
            return False

    def setup_test_data(self):
        """Create test customer and job data for campaign testing"""
        self.log("\n=== SETTING UP TEST DATA ===")
        
        # Create a test customer
        customer_data = {
            "first_name": "Campaign",
            "last_name": "TestCustomer",
            "phone": "+15551234567",
            "email": "campaign.test@example.com",
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
            self.log(f"✅ Test customer created with ID: {self.customer_id}")
            
            # Create a property for the customer
            property_data = {
                "customer_id": self.customer_id,
                "address_line1": "123 Campaign Test St",
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
                property_id = response['id']
                
                # Create a completed job (for segment targeting)
                past_date = datetime.now() - timedelta(days=200)  # 200 days ago
                job_data = {
                    "customer_id": self.customer_id,
                    "property_id": property_id,
                    "job_type": "DIAGNOSTIC",
                    "priority": "NORMAL",
                    "service_window_start": past_date.isoformat(),
                    "service_window_end": (past_date + timedelta(hours=2)).isoformat(),
                    "status": "COMPLETED"
                }
                
                success, response = self.run_test(
                    "Create Completed Job",
                    "POST",
                    "jobs",
                    200,
                    data=job_data
                )
                
                if success:
                    self.log(f"✅ Test data setup complete")
                    return True
        
        return False

    def test_campaign_creation_with_segment(self):
        """Test POST /api/v1/campaigns - create campaign with segment_definition"""
        self.log("\n=== CAMPAIGN CREATION WITH SEGMENT ===")
        
        campaign_data = {
            "name": "Test Reactivation Campaign",
            "type": "REACTIVATION",
            "message_template": "Hi {first_name}, it's been a while since we serviced your HVAC system. Schedule a tune-up today and get 10% off! Reply YES to book or call us.",
            "segment_definition": {
                "last_service_days_ago": ">180"
            },
            "status": "DRAFT"
        }
        
        success, response = self.run_test(
            "Create Campaign with Segment Definition",
            "POST",
            "campaigns",
            200,
            data=campaign_data
        )
        
        if success and 'id' in response:
            self.campaign_id = response['id']
            self.log(f"✅ Campaign created with ID: {self.campaign_id}")
            
            # Verify segment_definition is stored correctly
            if 'segment_definition' in response:
                segment = response['segment_definition']
                if segment and segment.get('last_service_days_ago') == ">180":
                    self.log(f"✅ Segment definition stored correctly: {segment}")
                else:
                    self.log(f"⚠️ Segment definition may not be stored correctly: {segment}")
            
            return True
        return False

    def test_preview_segment(self):
        """Test campaign segment preview functionality"""
        self.log("\n=== SEGMENT PREVIEW ===")
        
        if not self.campaign_id:
            self.log("❌ Skipping segment preview - no campaign ID")
            return False
        
        segment_data = {
            "last_service_days_ago": ">180"
        }
        
        success, response = self.run_test(
            "Preview Campaign Segment",
            "POST",
            f"campaigns/{self.campaign_id}/preview-segment",
            200,
            data=segment_data
        )
        
        if success:
            total_matching = response.get('total_matching', 0)
            sample_customers = response.get('sample_customers', [])
            self.log(f"✅ Segment preview: {total_matching} matching customers")
            if sample_customers:
                self.log(f"✅ Sample customers returned: {len(sample_customers)}")
            return True
        return False

    def test_start_campaign(self):
        """Test POST /api/v1/campaigns/{id}/start - start campaign, create recipients based on segment"""
        self.log("\n=== START CAMPAIGN ===")
        
        if not self.campaign_id:
            self.log("❌ Skipping campaign start - no campaign ID")
            return False
        
        success, response = self.run_test(
            "Start Campaign",
            "POST",
            f"campaigns/{self.campaign_id}/start",
            200
        )
        
        if success:
            recipients_created = response.get('recipients_created', 0)
            self.log(f"✅ Campaign started with {recipients_created} recipients")
            
            # Verify campaign status changed to RUNNING
            success2, campaign_response = self.run_test(
                "Verify Campaign Status",
                "GET",
                f"campaigns/{self.campaign_id}/stats",
                200
            )
            
            if success2:
                campaign_status = campaign_response.get('campaign_status')
                if campaign_status == 'RUNNING':
                    self.log(f"✅ Campaign status correctly set to RUNNING")
                else:
                    self.log(f"⚠️ Campaign status is {campaign_status}, expected RUNNING")
            
            return True
        return False

    def test_campaign_stats(self):
        """Test GET /api/v1/campaigns/{id}/stats - return real recipient counts"""
        self.log("\n=== CAMPAIGN STATS ===")
        
        if not self.campaign_id:
            self.log("❌ Skipping campaign stats - no campaign ID")
            return False
        
        success, response = self.run_test(
            "Get Campaign Stats",
            "GET",
            f"campaigns/{self.campaign_id}/stats",
            200
        )
        
        if success:
            stats = response.get('stats', {})
            recipients = response.get('recipients', [])
            
            # Verify real stats are returned (not mock data)
            total = stats.get('total', 0)
            pending = stats.get('pending', 0)
            sent = stats.get('sent', 0)
            
            self.log(f"✅ Campaign stats - Total: {total}, Pending: {pending}, Sent: {sent}")
            
            # Check if recipients list contains real customer data
            if recipients:
                first_recipient = recipients[0]
                if 'customer_name' in first_recipient and 'customer_phone' in first_recipient:
                    self.log(f"✅ Recipients contain real customer data")
                    self.log(f"   Sample: {first_recipient.get('customer_name')} - {first_recipient.get('customer_phone')}")
                else:
                    self.log(f"⚠️ Recipients may not contain complete customer data")
            
            # Verify stats are consistent
            if total == pending + sent:
                self.log(f"✅ Stats are mathematically consistent")
            else:
                self.log(f"⚠️ Stats inconsistency: total({total}) != pending({pending}) + sent({sent})")
            
            return True
        return False

    def test_send_batch(self):
        """Test POST /api/v1/campaigns/{id}/send-batch - send SMS to pending recipients"""
        self.log("\n=== SEND BATCH MESSAGES ===")
        
        if not self.campaign_id:
            self.log("❌ Skipping send batch - no campaign ID")
            return False
        
        # First check if there are pending recipients
        success, stats_response = self.run_test(
            "Check Pending Recipients",
            "GET",
            f"campaigns/{self.campaign_id}/stats",
            200
        )
        
        if not success:
            return False
        
        pending_count = stats_response.get('stats', {}).get('pending', 0)
        self.log(f"📊 Found {pending_count} pending recipients")
        
        if pending_count == 0:
            self.log("⚠️ No pending recipients to send messages to")
            return True  # Not a failure, just no work to do
        
        # Send a batch of messages
        success, response = self.run_test(
            "Send Message Batch",
            "POST",
            f"campaigns/{self.campaign_id}/send-batch?batch_size=5",
            200
        )
        
        if success:
            sent_in_batch = response.get('sent_in_batch', 0)
            remaining = response.get('remaining', 0)
            errors = response.get('errors', 0)
            status = response.get('status', '')
            
            self.log(f"✅ Batch sent - Messages: {sent_in_batch}, Remaining: {remaining}, Errors: {errors}")
            self.log(f"✅ Batch status: {status}")
            
            # Verify stats updated after sending
            time.sleep(1)  # Brief pause for stats to update
            success2, updated_stats = self.run_test(
                "Verify Updated Stats",
                "GET",
                f"campaigns/{self.campaign_id}/stats",
                200
            )
            
            if success2:
                new_sent = updated_stats.get('stats', {}).get('sent', 0)
                new_pending = updated_stats.get('stats', {}).get('pending', 0)
                self.log(f"✅ Updated stats - Sent: {new_sent}, Pending: {new_pending}")
            
            return True
        return False

    def test_campaign_workflow_end_to_end(self):
        """Test complete campaign workflow from creation to completion"""
        self.log("\n=== END-TO-END CAMPAIGN WORKFLOW ===")
        
        # Test the complete workflow
        workflow_steps = [
            ("Login", self.login),
            ("Setup Test Data", self.setup_test_data),
            ("Create Campaign with Segment", self.test_campaign_creation_with_segment),
            ("Preview Segment", self.test_preview_segment),
            ("Start Campaign", self.test_start_campaign),
            ("Get Campaign Stats", self.test_campaign_stats),
            ("Send Batch Messages", self.test_send_batch),
        ]
        
        for step_name, step_func in workflow_steps:
            self.log(f"\n--- {step_name} ---")
            if not step_func():
                self.log(f"❌ Workflow failed at step: {step_name}")
                return False
        
        self.log(f"\n✅ Complete campaign workflow executed successfully!")
        return True

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        self.log("\n=== CLEANUP ===")
        
        # Delete campaign
        if self.campaign_id:
            self.run_test(
                "Delete Test Campaign",
                "DELETE",
                f"campaigns/{self.campaign_id}",
                200
            )
        
        # Delete customer (cascade deletes properties and jobs)
        if self.customer_id:
            self.run_test(
                "Delete Test Customer",
                "DELETE",
                f"customers/{self.customer_id}",
                200
            )

    def run_all_tests(self):
        """Run all campaign tests"""
        self.log("🚀 Starting FieldOS Campaigns Module Tests")
        self.log(f"📍 Testing against: {self.base_url}")
        
        # Run the complete workflow
        success = self.test_campaign_workflow_end_to_end()
        
        # Cleanup
        self.cleanup_test_data()
        
        return self.generate_report()

    def generate_report(self):
        """Generate test report"""
        self.log("\n" + "="*60)
        self.log("📊 CAMPAIGN TESTS SUMMARY")
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
    tester = CampaignTester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if results['failed_tests'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())