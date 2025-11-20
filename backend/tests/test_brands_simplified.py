"""Simplified tests for Brand CRUD operations."""

import pytest
import uuid
from app.database.models import Brand


def test_brand_model_creation():
    """Test creating a brand model object."""
    brand_id = uuid.uuid4()
    user_id = uuid.uuid4()

    brand = Brand(
        id=brand_id,
        user_id=user_id,
        company_name="Test Company",
        brand_name="Test Brand",
        description="A test brand",
        guidelines="Brand guidelines",
        logo_urls={"urls": ["https://s3.amazonaws.com/logo.png"]}
    )

    assert brand.id == brand_id
    assert brand.user_id == user_id
    assert brand.company_name == "Test Company"
    assert brand.brand_name == "Test Brand"
    assert brand.description == "A test brand"
    assert brand.guidelines == "Brand guidelines"


def test_brand_model_minimal():
    """Test creating a brand with only required fields."""
    brand = Brand(
        user_id=uuid.uuid4(),
        company_name="Minimal Company"
    )

    assert brand.company_name == "Minimal Company"
    assert brand.brand_name is None
    assert brand.description is None
    assert brand.guidelines is None
    assert brand.logo_urls is None


def test_brand_table_name():
    """Test that Brand maps to correct table name."""
    assert Brand.__tablename__ == "brands"


def test_brand_repr():
    """Test brand string representation."""
    brand = Brand(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        company_name="Test Company"
    )

    repr_str = repr(brand)
    assert "Brand" in repr_str
    assert "Test Company" in repr_str


def test_brand_has_products_relationship():
    """Test that Brand model defines products relationship."""
    assert hasattr(Brand, 'products')
