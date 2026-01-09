"""
Phase 3 Testing: White-Label Branding & Enhanced Customer Portal
Tests for:
- GET/PUT /api/v1/settings/branding (authenticated)
- GET /api/v1/portal/{token}/branding (public)
- POST /api/v1/portal/{token}/request-service (public)
- GET /api/v1/portal/{token}/messages (public)
- GET /api/v1/portal/{token}/service-history (public)
- PUT /api/v1/portal/{token}/profile (public)
- GET /api/v1/service-requests (authenticated)
- POST /api/v1/service-requests/{id}/convert (authenticated)
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "owner@radiancehvac.com"
TEST_PASSWORD = "owner123"
PORTAL_TOKEN = "2279f98d-WJviWzBjvXf-mBSaQlwJjQ"


class TestAuthentication:
    """Test authentication for protected endpoints"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login successful for {TEST_EMAIL}")
        return data["access_token"]


class TestBrandingSettings:
    """Test branding settings endpoints (authenticated)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_get_branding_settings(self, auth_token):
        """GET /api/v1/settings/branding - Get branding settings"""
        response = requests.get(
            f"{BASE_URL}/api/v1/settings/branding",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed to get branding: {response.text}"
        data = response.json()
        
        # Verify expected fields exist
        expected_fields = [
            "primary_color", "secondary_color", "accent_color", 
            "text_on_primary", "font_family", "portal_title",
            "portal_welcome_message", "white_label_enabled"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ GET branding settings - primary_color: {data.get('primary_color')}")
        return data
    
    def test_update_branding_settings(self, auth_token):
        """PUT /api/v1/settings/branding - Update branding settings"""
        # First get current settings
        current = requests.get(
            f"{BASE_URL}/api/v1/settings/branding",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        
        # Update with new values
        new_branding = {
            "primary_color": "#FF5500",
            "secondary_color": "#CC4400",
            "accent_color": "#00AAFF",
            "text_on_primary": "#FFFFFF",
            "font_family": "Roboto",
            "portal_title": "Test Portal Title",
            "portal_welcome_message": "Welcome to our test portal!",
            "white_label_enabled": True
        }
        
        response = requests.put(
            f"{BASE_URL}/api/v1/settings/branding",
            json=new_branding,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed to update branding: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        # Verify changes persisted
        verify_response = requests.get(
            f"{BASE_URL}/api/v1/settings/branding",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        verify_data = verify_response.json()
        assert verify_data.get("primary_color") == "#FF5500"
        assert verify_data.get("white_label_enabled") == True
        
        # Restore original settings
        restore_branding = {
            "primary_color": current.get("primary_color", "#0066CC"),
            "secondary_color": current.get("secondary_color", "#004499"),
            "accent_color": current.get("accent_color", "#FF6600"),
            "white_label_enabled": current.get("white_label_enabled", False)
        }
        requests.put(
            f"{BASE_URL}/api/v1/settings/branding",
            json=restore_branding,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        print("✓ PUT branding settings - updated and verified")
    
    def test_branding_requires_auth(self):
        """Verify branding endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/v1/settings/branding")
        assert response.status_code == 401, "Should require authentication"
        print("✓ Branding endpoint correctly requires authentication")


class TestPortalBranding:
    """Test public portal branding endpoint"""
    
    def test_get_portal_branding(self):
        """GET /api/v1/portal/{token}/branding - Get portal branding (public)"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/branding")
        assert response.status_code == 200, f"Failed to get portal branding: {response.text}"
        data = response.json()
        
        # Verify expected fields
        expected_fields = ["primary_color", "company_name", "portal_title"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ GET portal branding - company: {data.get('company_name')}, color: {data.get('primary_color')}")
    
    def test_portal_branding_invalid_token(self):
        """Test portal branding with invalid token"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/invalid-token-12345/branding")
        assert response.status_code == 404, "Should return 404 for invalid token"
        print("✓ Portal branding correctly returns 404 for invalid token")


class TestPortalServiceRequest:
    """Test portal service request endpoint"""
    
    def test_request_service_from_portal(self):
        """POST /api/v1/portal/{token}/request-service - Submit service request"""
        response = requests.post(
            f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/request-service",
            params={
                "issue_description": "TEST_Air conditioner not cooling properly",
                "urgency": "ROUTINE",
                "preferred_date": "2025-01-15",
                "preferred_time_slot": "morning"
            }
        )
        assert response.status_code == 200, f"Failed to submit service request: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "service_request_id" in data
        assert "lead_id" in data
        
        print(f"✓ POST service request - ID: {data.get('service_request_id')}")
        return data.get("service_request_id")
    
    def test_request_service_emergency(self):
        """Test emergency service request"""
        response = requests.post(
            f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/request-service",
            params={
                "issue_description": "TEST_Heating system completely broken - no heat!",
                "urgency": "EMERGENCY"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ POST emergency service request successful")
    
    def test_request_service_invalid_token(self):
        """Test service request with invalid token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/portal/invalid-token/request-service",
            params={"issue_description": "Test"}
        )
        assert response.status_code == 404
        print("✓ Service request correctly returns 404 for invalid token")


class TestPortalMessages:
    """Test portal messages endpoint"""
    
    def test_get_portal_messages(self):
        """GET /api/v1/portal/{token}/messages - Get customer messages"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/messages")
        assert response.status_code == 200, f"Failed to get messages: {response.text}"
        data = response.json()
        
        # Should have messages array (may be empty)
        assert "messages" in data
        assert isinstance(data["messages"], list)
        
        print(f"✓ GET portal messages - count: {len(data.get('messages', []))}")
    
    def test_messages_invalid_token(self):
        """Test messages with invalid token"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/invalid-token/messages")
        assert response.status_code == 404
        print("✓ Messages endpoint correctly returns 404 for invalid token")


class TestPortalServiceHistory:
    """Test portal service history endpoint"""
    
    def test_get_service_history(self):
        """GET /api/v1/portal/{token}/service-history - Get service history"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/service-history")
        assert response.status_code == 200, f"Failed to get service history: {response.text}"
        data = response.json()
        
        assert "service_history" in data
        assert isinstance(data["service_history"], list)
        
        # If there are jobs, verify structure
        if data["service_history"]:
            job = data["service_history"][0]
            assert "job_type" in job or "id" in job
        
        print(f"✓ GET service history - count: {len(data.get('service_history', []))}")
    
    def test_service_history_invalid_token(self):
        """Test service history with invalid token"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/invalid-token/service-history")
        assert response.status_code == 404
        print("✓ Service history correctly returns 404 for invalid token")


class TestPortalProfile:
    """Test portal profile update endpoint"""
    
    def test_update_profile(self):
        """PUT /api/v1/portal/{token}/profile - Update customer profile"""
        # First get current data
        portal_response = requests.get(f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}")
        if portal_response.status_code != 200:
            pytest.skip("Could not get portal data")
        
        current_data = portal_response.json().get("customer", {})
        original_email = current_data.get("email")
        
        # Update profile
        response = requests.put(
            f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/profile",
            params={
                "first_name": current_data.get("first_name", "Test"),
                "last_name": current_data.get("last_name", "User"),
                "email": "test_updated@example.com",
                "phone": current_data.get("phone", "+15551234567")
            }
        )
        assert response.status_code == 200, f"Failed to update profile: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        # Verify update
        verify_response = requests.get(f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}")
        verify_data = verify_response.json().get("customer", {})
        assert verify_data.get("email") == "test_updated@example.com"
        
        # Restore original email
        if original_email:
            requests.put(
                f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/profile",
                params={"email": original_email}
            )
        
        print("✓ PUT profile update - updated and verified")
    
    def test_profile_update_invalid_token(self):
        """Test profile update with invalid token"""
        response = requests.put(
            f"{BASE_URL}/api/v1/portal/invalid-token/profile",
            params={"first_name": "Test"}
        )
        assert response.status_code == 404
        print("✓ Profile update correctly returns 404 for invalid token")


class TestServiceRequests:
    """Test service requests management endpoints (authenticated)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_list_service_requests(self, auth_token):
        """GET /api/v1/service-requests - List service requests"""
        response = requests.get(
            f"{BASE_URL}/api/v1/service-requests",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed to list service requests: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        
        # If there are requests, verify structure
        if data:
            req = data[0]
            assert "id" in req
            assert "issue_description" in req or "status" in req
        
        print(f"✓ GET service requests - count: {len(data)}")
        return data
    
    def test_convert_service_request_to_job(self, auth_token):
        """POST /api/v1/service-requests/{id}/convert - Convert to job"""
        # First create a service request via portal
        create_response = requests.post(
            f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/request-service",
            params={
                "issue_description": "TEST_Convert_to_job test request",
                "urgency": "ROUTINE"
            }
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create service request")
        
        request_id = create_response.json().get("service_request_id")
        
        # Convert to job
        response = requests.post(
            f"{BASE_URL}/api/v1/service-requests/{request_id}/convert",
            params={
                "job_type": "DIAGNOSTIC",
                "scheduled_date": "2025-01-20",
                "scheduled_time_slot": "morning"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Failed to convert: {response.text}"
        data = response.json()
        
        assert "job_id" in data or "id" in data
        print(f"✓ POST convert service request to job - success")
    
    def test_service_requests_requires_auth(self):
        """Verify service requests endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/v1/service-requests")
        assert response.status_code == 401
        print("✓ Service requests endpoint correctly requires authentication")


class TestPortalData:
    """Test main portal data endpoint"""
    
    def test_get_portal_data(self):
        """GET /api/v1/portal/{token} - Get full portal data"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}")
        assert response.status_code == 200, f"Failed to get portal data: {response.text}"
        data = response.json()
        
        # Verify expected sections
        assert "customer" in data
        assert "company" in data
        
        # Customer should have basic info
        customer = data.get("customer", {})
        assert "first_name" in customer or "id" in customer
        
        print(f"✓ GET portal data - customer: {customer.get('first_name')} {customer.get('last_name')}")
    
    def test_portal_data_invalid_token(self):
        """Test portal data with invalid token"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/invalid-token-xyz")
        assert response.status_code == 404
        print("✓ Portal data correctly returns 404 for invalid token")


class TestPortalInvoices:
    """Test portal invoices endpoint"""
    
    def test_get_portal_invoices(self):
        """GET /api/v1/portal/{token}/invoices - Get customer invoices"""
        response = requests.get(f"{BASE_URL}/api/v1/portal/{PORTAL_TOKEN}/invoices")
        assert response.status_code == 200, f"Failed to get invoices: {response.text}"
        data = response.json()
        
        assert "invoices" in data
        assert isinstance(data["invoices"], list)
        
        print(f"✓ GET portal invoices - count: {len(data.get('invoices', []))}")


# Cleanup function to remove test data
def cleanup_test_data():
    """Clean up TEST_ prefixed data after tests"""
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get and delete test service requests
            requests_resp = requests.get(
                f"{BASE_URL}/api/v1/service-requests",
                headers=headers
            )
            if requests_resp.status_code == 200:
                for req in requests_resp.json():
                    if req.get("issue_description", "").startswith("TEST_"):
                        # Service requests don't have delete endpoint, just leave them
                        pass
            
            # Get and delete test leads
            leads_resp = requests.get(f"{BASE_URL}/api/v1/leads", headers=headers)
            if leads_resp.status_code == 200:
                test_leads = [l for l in leads_resp.json() if l.get("description", "").startswith("TEST_") or l.get("issue_type", "").startswith("TEST_")]
                if test_leads:
                    lead_ids = [l["id"] for l in test_leads]
                    requests.post(
                        f"{BASE_URL}/api/v1/leads/bulk-delete",
                        json=lead_ids,
                        headers=headers
                    )
            print("✓ Cleanup completed")
    except Exception as e:
        print(f"Cleanup warning: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
