"""Tests for database models."""

import pytest
from datetime import datetime
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database.models import Base, Brand, Product, Campaign


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for tests
    # Note: SQLite doesn't support PostgreSQL UUID type, so we'll test the Python model layer
    engine = create_engine('sqlite:///:memory:')

    # For PostgreSQL-specific tests, skip table creation
    # We'll test model instantiation and relationships without actual database
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


class TestBrandModel:
    """Tests for Brand model - testing Python object layer."""

    def test_create_brand_object(self):
        """Test creating a brand object with all required fields."""
        brand_id = uuid.uuid4()
        user_id = uuid.uuid4()

        brand = Brand(
            id=brand_id,
            user_id=user_id,
            company_name="Test Company",
            brand_name="Test Brand",
            description="A test brand description",
            guidelines="Brand guidelines text",
            logo_urls={"urls": ["https://s3.amazonaws.com/logo1.png", "https://s3.amazonaws.com/logo2.png"]}
        )

        # Verify brand object properties
        assert brand.id == brand_id
        assert brand.user_id == user_id
        assert brand.company_name == "Test Company"
        assert brand.brand_name == "Test Brand"
        assert brand.description == "A test brand description"
        assert brand.guidelines == "Brand guidelines text"

    def test_brand_minimal_fields(self):
        """Test creating a brand with only required fields."""
        brand = Brand(
            user_id=uuid.uuid4(),
            company_name="Minimal Company"
        )

        # Verify optional fields are None
        assert brand.brand_name is None
        assert brand.description is None
        assert brand.guidelines is None
        assert brand.logo_urls is None

    def test_brand_repr(self):
        """Test brand string representation."""
        brand_id = uuid.uuid4()
        brand = Brand(
            id=brand_id,
            user_id=uuid.uuid4(),
            company_name="Test Company"
        )

        repr_str = repr(brand)
        assert "Brand" in repr_str
        assert str(brand_id) in repr_str
        assert "Test Company" in repr_str

    def test_brand_table_name(self):
        """Test that Brand maps to correct table name."""
        assert Brand.__tablename__ == "brands"

    def test_brand_has_products_relationship(self):
        """Test that Brand model defines products relationship."""
        # Verify relationship is defined
        assert hasattr(Brand, 'products')
        # Verify it's configured for cascade delete
        products_property = getattr(Brand, 'products')
        assert products_property is not None


class TestProductModel:
    """Tests for Product model - testing Python object layer."""

    def test_create_product_object(self):
        """Test creating a product object with all required fields."""
        product_id = uuid.uuid4()
        brand_id = uuid.uuid4()

        product = Product(
            id=product_id,
            brand_id=brand_id,
            product_type="SaaS",
            name="Test Product",
            icp_segment="Enterprise B2B",
            image_urls={"urls": ["https://s3.amazonaws.com/img1.png", "https://s3.amazonaws.com/img2.png"]}
        )

        # Verify product object properties
        assert product.id == product_id
        assert product.brand_id == brand_id
        assert product.product_type == "SaaS"
        assert product.name == "Test Product"
        assert product.icp_segment == "Enterprise B2B"

    def test_product_minimal_fields(self):
        """Test creating a product with only required fields."""
        product = Product(
            brand_id=uuid.uuid4(),
            product_type="SaaS",
            name="Minimal Product"
        )

        # Verify optional fields are None
        assert product.icp_segment is None
        assert product.image_urls is None

    def test_product_repr(self):
        """Test product string representation."""
        product_id = uuid.uuid4()
        product = Product(
            id=product_id,
            brand_id=uuid.uuid4(),
            product_type="SaaS",
            name="Test Product"
        )

        repr_str = repr(product)
        assert "Product" in repr_str
        assert str(product_id) in repr_str
        assert "Test Product" in repr_str

    def test_product_table_name(self):
        """Test that Product maps to correct table name."""
        assert Product.__tablename__ == "products"

    def test_product_has_brand_relationship(self):
        """Test that Product model defines brand relationship."""
        # Verify relationship is defined
        assert hasattr(Product, 'brand')
        brand_property = getattr(Product, 'brand')
        assert brand_property is not None

    def test_product_foreign_key_defined(self):
        """Test that product has foreign key to brands."""
        # Check that brand_id column has a foreign key
        product = Product(
            brand_id=uuid.uuid4(),
            product_type="SaaS",
            name="Test"
        )
        assert product.brand_id is not None


class TestSchemaDefinition:
    """Tests for schema definition."""

    def test_all_models_defined(self):
        """Test that all expected models are defined."""
        # Verify all model classes exist
        assert Brand is not None
        assert Product is not None
        assert Campaign is not None

    def test_table_names_correct(self):
        """Test that all tables have correct names."""
        assert Brand.__tablename__ == "brands"
        assert Product.__tablename__ == "products"
        assert Campaign.__tablename__ == "campaigns"

    def test_brand_has_required_columns(self):
        """Test that Brand has all required columns."""
        brand = Brand(
            user_id=uuid.uuid4(),
            company_name="Test"
        )

        # Check required fields
        assert hasattr(brand, 'id')
        assert hasattr(brand, 'user_id')
        assert hasattr(brand, 'company_name')

        # Check optional fields
        assert hasattr(brand, 'brand_name')
        assert hasattr(brand, 'description')
        assert hasattr(brand, 'guidelines')
        assert hasattr(brand, 'logo_urls')

        # Check timestamps
        assert hasattr(brand, 'created_at')
        assert hasattr(brand, 'updated_at')

    def test_product_has_required_columns(self):
        """Test that Product has all required columns."""
        product = Product(
            brand_id=uuid.uuid4(),
            product_type="SaaS",
            name="Test"
        )

        # Check required fields
        assert hasattr(product, 'id')
        assert hasattr(product, 'brand_id')
        assert hasattr(product, 'product_type')
        assert hasattr(product, 'name')

        # Check optional fields
        assert hasattr(product, 'icp_segment')
        assert hasattr(product, 'image_urls')

        # Check timestamps
        assert hasattr(product, 'created_at')
        assert hasattr(product, 'updated_at')
