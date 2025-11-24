"""Configuration package for product types and related configs."""

from .product_types import (
    ProductTypeConfig,
    PRODUCT_TYPES,
    get_product_type_config,
    get_all_product_types,
)

__all__ = [
    "ProductTypeConfig",
    "PRODUCT_TYPES",
    "get_product_type_config",
    "get_all_product_types",
]
