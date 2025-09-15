"""Unified configuration manager combining all domain managers."""

from typing import Any, Dict, List, Optional, Union
from .data_source_manager import DataSourceManager
from .feature_manager import FeatureManager
from .function_manager import FunctionManager
from .rules_manager import RulesManager
from .system_manager import SystemManager


class UnifiedConfigurationManager(DataSourceManager, FeatureManager,
                                  FunctionManager, RulesManager,
                                  SystemManager):
    """Unified configuration manager with all domain functionality.

    This class combines all domain managers using multiple inheritance
    to provide a single interface for configuration operations while
    maintaining the modular architecture internally.
    """

    def __init__(self, ini_file_name: Optional[str] = None, verbose_logging: bool = False):
        """Initialize the unified configuration manager.

        Args:
            ini_file_name: Optional path to sz_engine_config.ini file
            verbose_logging: Enable verbose logging on SzAbstractFactory
        """
        # Initialize the base manager (all others inherit from it)
        super().__init__(ini_file_name, verbose_logging)

    def apply_filter(self, records: List[Dict[str, Any]], filter_expression: str) -> List[Dict[str, Any]]:
        """Apply a filter expression to a list of records.

        Args:
            records: List of records to filter
            filter_expression: Filter expression (basic implementation)

        Returns:
            Filtered list of records
        """
        if not filter_expression or not records:
            return records

        # Basic filter implementation - case-insensitive substring match
        # against all string values in the record
        filter_lower = filter_expression.lower()
        filtered_records = []

        for record in records:
            # Check if any value in the record matches the filter
            for value in record.values():
                if isinstance(value, str) and filter_lower in value.lower():
                    filtered_records.append(record)
                    break

        return filtered_records

    def get_statistics(self) -> Dict[str, Any]:
        """Get configuration statistics.

        Returns:
            Dictionary with configuration statistics
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return {}

        g2_config = config_data['G2_CONFIG']

        stats = {
            'dataSources': len(g2_config.get('CFG_DSRC', [])),
            'features': len(g2_config.get('CFG_FTYPE', [])),
            'attributes': len(g2_config.get('CFG_ATTR', [])),
            'elements': len(g2_config.get('CFG_FELEM', [])),
            'comparisonFunctions': len(g2_config.get('CFG_CFUNC', [])),
            'expressionFunctions': len(g2_config.get('CFG_EFUNC', [])),
            'standardizeFunctions': len(g2_config.get('CFG_SFUNC', [])),
            'distinctFunctions': len(g2_config.get('CFG_DFUNC', [])),
            'rules': len(g2_config.get('CFG_RULE', [])),
            'genericPlans': len(g2_config.get('CFG_GPLAN', [])),
            'behaviorOverrides': len(g2_config.get('CFG_BOVER', [])),
            'configId': self.current_config_id,
            'hasChanges': self.config_updated
        }

        return stats

    def reset_configuration(self) -> bool:
        """Reset to a clean configuration.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a new config from template
            if not self._sz_config_mgr:
                return False

            sz_config = self._sz_config_mgr.create_config_from_template()
            if sz_config:
                self._sz_config = sz_config
                self.config_updated = True
                self._clear_config_cache()
                return True
            else:
                return False

        except Exception as e:
            if self._verbose_logging:
                print(f"Failed to reset configuration: {e}")
            return False

    def __str__(self) -> str:
        """String representation of the configuration manager."""
        stats = self.get_statistics()
        return (f"ConfigurationManager(id={stats.get('configId', 'None')}, "
                f"features={stats.get('features', 0)}, "
                f"dataSources={stats.get('dataSources', 0)}, "
                f"hasChanges={stats.get('hasChanges', False)})")

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"UnifiedConfigurationManager(config_id={self.current_config_id}, " \
               f"initialized={self.is_initialized()}, updated={self.config_updated})"