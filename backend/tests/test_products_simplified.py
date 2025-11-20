"""Simplified tests for Product CRUD operations."""

import pytest
import uuid
from app.database.models import Product


def test_product_model_creation():
    """Test creating a product model object."""
    product_id = uuid.uuid4()
    brand_id = uuid.uuid4()

    product = Product(
        id=product_id,
        brand_id=brand_id,
        product_type="SaaS",
        name="Analytics Platform",
        icp_segment="Mid-market B2B companies",
        image_urls=["https://s3.amazonaws.com/product1.png", "https://s3.amazonaws.com/product2.png"]
    )

    assert product.id == product_id
    assert product.brand_id == brand_id
    assert product.product_type == "SaaS"
    assert product.name == "Analytics Platform"
    assert product.icp_segment == "Mid-market B2B companies"
    assert len(product.image_urls) == 2


def test_product_model_minimal():
    """Test creating a product with only required fields."""
    product = Product(
        brand_id=uuid.uuid4(),
        product_type="Physical Product",
        name="Minimal Product"
    )

    assert product.product_type == "Physical Product"
    assert product.name == "Minimal Product"
    assert product.icp_segment is None
    assert product.image_urls is None


def test_product_table_name():
    """Test that Product maps to correct table name."""
    assert Product.__tablename__ == "products"


def test_product_repr():
    """Test product string representation."""
    product = Product(
        id=uuid.uuid4(),
        brand_id=uuid.uuid4(),
        product_type="SaaS",
        name="Test Product"
    )

    repr_str = repr(product)
    assert "Product" in repr_str
    assert "Test Product" in repr_str


def test_product_has_brand_relationship():
    """Test that Product model defines brand relationship."""
    assert hasattr(Product, 'brand')


def test_product_max_image_urls():
    """Test product with maximum allowed image URLs (10)."""
    product = Product(
        brand_id=uuid.uuid4(),
        product_type="Physical Product",
        name="Product with Many Images",
        image_urls=[f"https://s3.amazonaws.com/image{i}.png" for i in range(10)]
    )

    assert len(product.image_urls) == 10


def test_product_foreign_key_relationship():
    """Test that Product has brand_id foreign key."""
    product = Product(
        brand_id=uuid.uuid4(),
        product_type="Service",
        name="Consulting Service"
    )

    assert product.brand_id is not None
    assert isinstance(product.brand_id, uuid.UUID)
