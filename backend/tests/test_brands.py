"""Tests for Brand CRUD operations (Python object layer only)."""

import pytest
import uuid
from datetime import datetime
from app.database.models import Brand
from app.database.crud import (
    create_brand,
    get_user_brands,
    get_brand,
    update_brand,
    delete_brand
)


# Mock database session for testing
class MockDB:
    """Mock database session for testing CRUD functions."""

    def __init__(self):
        self.brands = []
        self.committed = False
        self.rolled_back = False

    def add(self, brand):
        brand.id = uuid.uuid4()
        brand.created_at = datetime.utcnow()
        brand.updated_at = datetime.utcnow()
        self.brands.append(brand)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def refresh(self, brand):
        pass

    def query(self, model):
        return MockQuery(self.brands)

    def delete(self, brand):
        if brand in self.brands:
            self.brands.remove(brand)


class MockQuery:
    """Mock query object."""

    def __init__(self, brands):
        self.brands = brands
        self.filters = []

    def filter(self, *args):
        # Simple filtering (just return self for chaining)
        return self

    def order_by(self, *args):
        return self

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    def first(self):
        return self.brands[0] if self.brands else None

    def all(self):
        return self.brands


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MockDB()


@pytest.fixture
def test_user_id():
    """Test user UUID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def test_brand_data():
    """Test brand data."""
    return {
        "company_name": "Test Company",
        "brand_name": "Test Brand",
        "description": "A test brand description",
        "guidelines": "Brand guidelines text",
        "logo_urls": {"urls": ["https://s3.amazonaws.com/logo1.png"]}
    }


# ============================================================================
# CRUD Function Tests
# ============================================================================

def test_create_brand_success(mock_db, test_user_id, test_brand_data):
    """Test creating a brand successfully."""
    brand = create_brand(
        db=mock_db,
        user_id=test_user_id,
        **test_brand_data
    )

    assert brand is not None
    assert brand.company_name == test_brand_data["company_name"]
    assert brand.brand_name == test_brand_data["brand_name"]
    assert brand.description == test_brand_data["description"]
    assert brand.guidelines == test_brand_data["guidelines"]
    assert brand.user_id == test_user_id
    assert mock_db.committed is True


def test_create_brand_minimal_fields():
    """Test creating a brand with only required fields."""
    minimal_data = {"company_name": "Minimal Company"}

    response = client.post("/api/brands/", json=minimal_data)

    assert response.status_code == 201
    data = response.json()

    assert data["company_name"] == "Minimal Company"
    assert data["brand_name"] is None
    assert data["description"] is None
    assert data["guidelines"] is None
    assert data["logo_urls"] is None


def test_create_brand_missing_required_field():
    """Test creating a brand without required company_name."""
    invalid_data = {
        "brand_name": "Test Brand",
        "description": "Test description"
    }

    response = client.post("/api/brands/", json=invalid_data)

    assert response.status_code == 422  # Validation error


def test_create_brand_company_name_too_long():
    """Test creating a brand with company_name exceeding max length."""
    invalid_data = {
        "company_name": "A" * 201,  # Max is 200
        "brand_name": "Test"
    }

    response = client.post("/api/brands/", json=invalid_data)

    assert response.status_code == 422  # Validation error


# ============================================================================
# GET /api/brands - List Brands Tests
# ============================================================================

def test_list_brands_empty():
    """Test listing brands when none exist."""
    response = client.get("/api/brands/")

    assert response.status_code == 200
    data = response.json()

    assert data == []


def test_list_brands_with_data(test_brand_data):
    """Test listing brands after creating some."""
    # Create 3 brands
    for i in range(3):
        brand_data = test_brand_data.copy()
        brand_data["company_name"] = f"Company {i}"
        client.post("/api/brands/", json=brand_data)

    # List brands
    response = client.get("/api/brands/")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3
    # Verify they're sorted by created_at DESC (newest first)
    assert data[0]["company_name"] == "Company 2"
    assert data[1]["company_name"] == "Company 1"
    assert data[2]["company_name"] == "Company 0"


def test_list_brands_pagination(test_brand_data):
    """Test pagination with limit and offset."""
    # Create 5 brands
    for i in range(5):
        brand_data = test_brand_data.copy()
        brand_data["company_name"] = f"Company {i}"
        client.post("/api/brands/", json=brand_data)

    # Get first page (limit 2)
    response = client.get("/api/brands/?limit=2&offset=0")
    data = response.json()

    assert len(data) == 2
    assert data[0]["company_name"] == "Company 4"  # Newest first
    assert data[1]["company_name"] == "Company 3"

    # Get second page (offset 2)
    response = client.get("/api/brands/?limit=2&offset=2")
    data = response.json()

    assert len(data) == 2
    assert data[0]["company_name"] == "Company 2"
    assert data[1]["company_name"] == "Company 1"


# ============================================================================
# GET /api/brands/{brand_id} - Get Brand Tests
# ============================================================================

def test_get_brand_success(test_brand_data):
    """Test getting a single brand by ID."""
    # Create brand
    create_response = client.post("/api/brands/", json=test_brand_data)
    brand_id = create_response.json()["id"]

    # Get brand
    response = client.get(f"/api/brands/{brand_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == brand_id
    assert data["company_name"] == test_brand_data["company_name"]


def test_get_brand_not_found():
    """Test getting a brand that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000099"

    response = client.get(f"/api/brands/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_brand_invalid_uuid():
    """Test getting a brand with invalid UUID format."""
    invalid_id = "not-a-uuid"

    response = client.get(f"/api/brands/{invalid_id}")

    assert response.status_code == 422  # Validation error


# ============================================================================
# PUT /api/brands/{brand_id} - Update Brand Tests
# ============================================================================

def test_update_brand_success(test_brand_data):
    """Test updating a brand successfully."""
    # Create brand
    create_response = client.post("/api/brands/", json=test_brand_data)
    brand_id = create_response.json()["id"]

    # Update brand
    update_data = {
        "company_name": "Updated Company",
        "description": "Updated description"
    }

    response = client.put(f"/api/brands/{brand_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()

    assert data["company_name"] == "Updated Company"
    assert data["description"] == "Updated description"
    # brand_name should remain unchanged
    assert data["brand_name"] == test_brand_data["brand_name"]


def test_update_brand_partial():
    """Test partial update (only one field)."""
    # Create brand
    create_data = {"company_name": "Original Company", "description": "Original description"}
    create_response = client.post("/api/brands/", json=create_data)
    brand_id = create_response.json()["id"]

    # Update only description
    update_data = {"description": "New description"}

    response = client.put(f"/api/brands/{brand_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()

    assert data["company_name"] == "Original Company"  # Unchanged
    assert data["description"] == "New description"  # Changed


def test_update_brand_not_found():
    """Test updating a brand that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000099"
    update_data = {"company_name": "Updated"}

    response = client.put(f"/api/brands/{fake_id}", json=update_data)

    assert response.status_code == 404


def test_update_brand_no_fields():
    """Test updating with no fields provided."""
    # Create brand
    create_response = client.post("/api/brands/", json={"company_name": "Test"})
    brand_id = create_response.json()["id"]

    # Try to update with empty dict
    response = client.put(f"/api/brands/{brand_id}", json={})

    assert response.status_code == 400
    assert "no fields" in response.json()["detail"].lower()


# ============================================================================
# DELETE /api/brands/{brand_id} - Delete Brand Tests
# ============================================================================

def test_delete_brand_success(test_brand_data):
    """Test deleting a brand successfully."""
    # Create brand
    create_response = client.post("/api/brands/", json=test_brand_data)
    brand_id = create_response.json()["id"]

    # Delete brand
    response = client.delete(f"/api/brands/{brand_id}")

    assert response.status_code == 204
    assert response.content == b""

    # Verify it's deleted
    get_response = client.get(f"/api/brands/{brand_id}")
    assert get_response.status_code == 404


def test_delete_brand_not_found():
    """Test deleting a brand that doesn't exist."""
    fake_id = "00000000-0000-0000-0000-000000000099"

    response = client.delete(f"/api/brands/{fake_id}")

    assert response.status_code == 404


def test_delete_brand_cascade_to_products():
    """Test that deleting a brand cascades to products (CASCADE delete)."""
    # Note: This test requires Product model and table to exist
    # For now, we just verify the delete succeeds
    # Full cascade testing will be done in Story 1-3 (Product API)

    create_response = client.post("/api/brands/", json={"company_name": "Test"})
    brand_id = create_response.json()["id"]

    response = client.delete(f"/api/brands/{brand_id}")

    assert response.status_code == 204


# ============================================================================
# Authentication Tests (Simplified for Story 1-2)
# ============================================================================

def test_all_endpoints_work_without_auth_in_development():
    """Test that all endpoints work without auth header in development mode."""
    # In development mode, endpoints should fall back to test user ID

    # Create
    response = client.post("/api/brands/", json={"company_name": "Test"})
    assert response.status_code == 201

    # List
    response = client.get("/api/brands/")
    assert response.status_code == 200

    # Get
    brand_id = client.post("/api/brands/", json={"company_name": "Test2"}).json()["id"]
    response = client.get(f"/api/brands/{brand_id}")
    assert response.status_code == 200

    # Update
    response = client.put(f"/api/brands/{brand_id}", json={"company_name": "Updated"})
    assert response.status_code == 200

    # Delete
    response = client.delete(f"/api/brands/{brand_id}")
    assert response.status_code == 204


# ============================================================================
# Schema Validation Tests
# ============================================================================

def test_response_schema_matches():
    """Test that response matches BrandResponse schema exactly."""
    create_response = client.post("/api/brands/", json={"company_name": "Test"})
    data = create_response.json()

    # Verify all required fields exist
    required_fields = ["id", "user_id", "company_name", "brand_name", "description",
                      "guidelines", "logo_urls", "created_at", "updated_at"]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Verify types
    assert isinstance(data["id"], str)
    assert isinstance(data["user_id"], str)
    assert isinstance(data["company_name"], str)
    assert isinstance(data["created_at"], str)
    assert isinstance(data["updated_at"], str)
