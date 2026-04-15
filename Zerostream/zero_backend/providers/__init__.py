"""
Data Providers Module

Provides independent data access implementations:
- Lakebase: PostgreSQL-compatible low-latency access
- Zerobus: Databricks SQL Warehouse access

Each provider is self-contained with its own configuration and implementation.
"""

from .lakebase_provider import LakebaseProvider, LakebaseConfig
# Import from lakeflow_provider but expose as Zerobus naming
from .lakeflow_provider import LakeflowProvider as ZerobusProvider
from .lakeflow_provider import LakeflowConfig as ZerobusConfig

__all__ = [
    'LakebaseProvider',
    'LakebaseConfig',
    'ZerobusProvider',
    'ZerobusConfig',
    'get_provider',
]


def get_provider(source_type: str):
    """
    Factory function to get the appropriate data provider.

    Args:
        source_type: Either 'zerobus' or 'lakebase'

    Returns:
        DataProvider instance (initialized with config from environment)

    Raises:
        ValueError: If source_type is not recognized
    """
    if source_type == 'zerobus':
        config = ZerobusConfig.from_env()
        return ZerobusProvider(config)
    elif source_type == 'lakebase':
        config = LakebaseConfig.from_env()
        return LakebaseProvider(config)
    else:
        raise ValueError(
            f"Unknown data source '{source_type}'. "
            f"Valid options: zerobus, lakebase"
        )
