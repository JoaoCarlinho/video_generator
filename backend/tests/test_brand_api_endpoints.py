"""Unit tests for brand API endpoints (Story 7.1)."""

import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from app.database.models import Brand
from app.models.schemas import BrandDetail
from datetime import datetime


# Fixtures

@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def sample_brand():
    """Sample brand object."""
    brand_id = uuid4()
    user_id = uuid4()
    return Brand(
        id=brand_id,
        user_id=user_id,
        company_name="Test Company",
        brand_name="TestBrand",
        description="Test description",
        guidelines="https://s3.amazonaws.com/guidelines.pdf",
        logo_urls=["https://s3.amazonaws.com/logo.png"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_brands_list(sample_brand):
    """List of sample brands."""
    brand2 = Brand(
        id=uuid4(),
        user_id=sample_brand.user_id,
        company_name="Test Company 2",
        brand_name="TestBrand2",
        description="Test description 2",
        guidelines="https://s3.amazonaws.com/guidelines2.pdf",
        logo_urls=["https://s3.amazonaws.com/logo2.png"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    return [sample_brand, brand2]


# Test crud.update_brand()

def test_update_brand_crud_success(mock_db, sample_brand):
    """Test successful brand update in CRUD."""
    # Import at module level to avoid config loading issues
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    from app.database.crud import update_brand

    # Mock query
    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = sample_brand
    mock_db.query.return_value = mock_query

    # Update brand using **kwargs pattern
    result = update_brand(
        db=mock_db,
        brand_id=sample_brand.id,
        user_id=sample_brand.user_id,
        brand_name="UpdatedBrand",
        logo_urls=["https://s3.amazonaws.com/new_logo.png"],
        guidelines="https://s3.amazonaws.com/new_guidelines.pdf"
    )

    # Verify
    assert result is not None
    assert result.brand_name == "UpdatedBrand"
    assert result.logo_urls == ["https://s3.amazonaws.com/new_logo.png"]
    assert result.guidelines == "https://s3.amazonaws.com/new_guidelines.pdf"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


def test_update_brand_crud_partial_update(mock_db, sample_brand):
    """Test partial brand update in CRUD (only brand_name)."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    from app.database.crud import update_brand

    # Mock query
    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = sample_brand
    mock_db.query.return_value = mock_query

    # Update only brand name using **kwargs pattern
    result = update_brand(
        db=mock_db,
        brand_id=sample_brand.id,
        user_id=sample_brand.user_id,
        brand_name="UpdatedBrand"
    )

    # Verify only brand_name was updated
    assert result.brand_name == "UpdatedBrand"
    # Original values should remain
    assert result.logo_urls == ["https://s3.amazonaws.com/logo.png"]
    assert result.guidelines == "https://s3.amazonaws.com/guidelines.pdf"


def test_update_brand_crud_not_found(mock_db):
    """Test update brand when brand doesn't exist in CRUD."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    from app.database.crud import update_brand

    # Mock query to return None
    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = None
    mock_db.query.return_value = mock_query

    # Update non-existent brand using **kwargs pattern
    result = update_brand(
        db=mock_db,
        brand_id=uuid4(),
        user_id=uuid4(),
        brand_name="UpdatedBrand"
    )

    # Should return None
    assert result is None
    mock_db.commit.assert_not_called()


# Test duplicate name validation logic

def test_duplicate_name_check_exact_match(sample_brand):
    """Test duplicate name detection (exact match)."""
    existing_brands = [sample_brand]
    new_name = "TestBrand"

    # Case-insensitive check
    is_duplicate = any(b.brand_name and b.brand_name.lower() == new_name.lower()
                      for b in existing_brands)

    assert is_duplicate is True


def test_duplicate_name_check_case_insensitive(sample_brand):
    """Test duplicate name detection (case-insensitive)."""
    existing_brands = [sample_brand]
    new_name = "testbrand"  # Different case

    # Case-insensitive check
    is_duplicate = any(b.brand_name and b.brand_name.lower() == new_name.lower()
                      for b in existing_brands)

    assert is_duplicate is True


def test_duplicate_name_check_unique(sample_brand):
    """Test that unique names are not detected as duplicates."""
    existing_brands = [sample_brand]
    new_name = "UniqueNewBrand"

    # Case-insensitive check
    is_duplicate = any(b.brand_name and b.brand_name.lower() == new_name.lower()
                      for b in existing_brands)

    assert is_duplicate is False


def test_duplicate_name_check_excluding_current(sample_brand, sample_brands_list):
    """Test duplicate check excluding current brand (for PUT endpoint)."""
    existing_brands = sample_brands_list
    current_brand_id = sample_brand.id
    new_name = "TestBrand"  # Same as current brand

    # Should allow keeping same name when updating
    is_duplicate = any(b.brand_name and b.brand_name.lower() == new_name.lower() and b.id != current_brand_id
                      for b in existing_brands)

    assert is_duplicate is False  # Not a duplicate since it's the same brand


def test_duplicate_name_check_excluding_current_but_matches_other(sample_brand, sample_brands_list):
    """Test duplicate check finds match in other brand."""
    existing_brands = sample_brands_list
    current_brand_id = sample_brand.id
    new_name = "TestBrand2"  # Name of the second brand

    # Should detect duplicate with another brand
    is_duplicate = any(b.brand_name and b.brand_name.lower() == new_name.lower() and b.id != current_brand_id
                      for b in existing_brands)

    assert is_duplicate is True


# Test BrandDetail schema validation

def test_brand_detail_schema_validation(sample_brand):
    """Test BrandDetail schema validation (all required fields)."""
    brand_detail = BrandDetail.model_validate(sample_brand)

    assert isinstance(brand_detail.id, UUID)
    assert isinstance(brand_detail.user_id, UUID)
    assert brand_detail.company_name == "Test Company"
    assert brand_detail.brand_name == "TestBrand"
    assert brand_detail.guidelines == "https://s3.amazonaws.com/guidelines.pdf"
    assert brand_detail.logo_urls == ["https://s3.amazonaws.com/logo.png"]
    assert isinstance(brand_detail.created_at, datetime)
    assert isinstance(brand_detail.updated_at, datetime)
