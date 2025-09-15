"""Base configuration manager with common functionality."""

import json
import pathlib
from typing import Any, Dict, List, Optional, Union

from senzing import SzError
from senzing_core import SzAbstractFactoryCore
try:
    from ..._tool_helpers import get_engine_config
except (ImportError, ValueError):
    from _tool_helpers import get_engine_config


class BaseConfigurationManager:
    """Base configuration manager with common Senzing operations."""

    def __init__(self, ini_file_name: Optional[str] = None, verbose_logging: bool = False):
        """Initialize the configuration manager.

        Args:
            ini_file_name: Optional path to sz_engine_config.ini file
            verbose_logging: Enable verbose logging on SzAbstractFactory
        """
        self._ini_file_name = ini_file_name
        self._verbose_logging = verbose_logging
        self._sz_factory = None
        self._sz_config_mgr = None
        self._sz_config = None
        self._current_config_id = None

        # Full in-memory configuration data - this is the key for CRUD operations
        self.config_data = None
        self.config_updated = False

        # Cache for parsed configuration data to avoid repeated exports/parsing
        self._cached_config_data = None
        self._cached_config_json = None

    def initialize_senzing(self) -> bool:
        """Initialize Senzing components.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Get engine configuration like the original sz_configtool does
            engine_config = get_engine_config(self._ini_file_name)

            # Create factory with or without verbose logging
            if self._verbose_logging:
                self._sz_factory = SzAbstractFactoryCore("sz_configtool", engine_config, verbose_logging=True)
            else:
                self._sz_factory = SzAbstractFactoryCore("sz_configtool", engine_config)

            self._sz_config_mgr = self._sz_factory.create_configmanager()

            # Load configuration following the original pattern
            try:
                self.load_config()
                return True
            except Exception as e:
                if self._verbose_logging:
                    print(f"Configuration loading failed: {e}")
                    import traceback
                    traceback.print_exc()
                return False

        except (SzError, Exception) as e:
            if self._verbose_logging:
                print(f"Initialization failed with error: {e}")
                import traceback
                traceback.print_exc()
            return False

    def load_config(self, config_id: int = None) -> bool:
        """Load configuration from database following original pattern.

        Args:
            config_id: Optional specific configuration ID to load

        Returns:
            True if configuration loaded successfully, False otherwise
        """
        try:
            # Get the current configuration from the Senzing database if not specified
            if not config_id:
                config_id = self._sz_config_mgr.get_default_config_id()

            # If a default config isn't found, create a new default configuration
            if not config_id:
                sz_config = self._sz_config_mgr.create_config_from_template()
                default_config = sz_config.export()

                # Persist new default config to Senzing Repository
                config_id = self._sz_config_mgr.register_config(
                    default_config,
                    "New default configuration added by sz_configtool."
                )
                self._sz_config_mgr.set_default_config_id(config_id)

            # Create sz_config from the configuration ID
            sz_config = self._sz_config_mgr.create_config_from_config_id(config_id)

            # Verify we got a valid config
            if not sz_config:
                return False

            # Update instance configuration from the loaded config
            self._current_config_id = config_id
            self._sz_config = sz_config

            # Load the config data for CRUD operations
            self._clear_config_cache()
            return True

        except (SzError, Exception) as e:
            if self._verbose_logging:
                print(f"Failed to load configuration: {e}")
            return False

    def save_config(self, comment: str = None) -> Optional[int]:
        """Save the current configuration to the database.

        Args:
            comment: Optional comment for the configuration save

        Returns:
            New configuration ID if successful, None otherwise
        """
        if not comment:
            comment = "Updated by sz_configtool"

        try:
            if not self._sz_config:
                raise ValueError("No configuration loaded")

            # Export the current in-memory configuration as JSON
            config_json = self._sz_config.export()

            # Register the configuration in the database
            new_config_id = self._sz_config_mgr.register_config(config_json, comment)

            if new_config_id:
                # Update our tracked configuration ID
                self._current_config_id = new_config_id
                self.config_updated = False
                self._clear_config_cache()
                return new_config_id
            else:
                return None

        except (SzError, Exception) as e:
            if self._verbose_logging:
                print(f"Failed to save configuration: {e}")
            return None

    def get_default_config_id(self) -> Optional[int]:
        """Get the default configuration ID.

        Returns:
            Default configuration ID if available, None otherwise
        """
        try:
            if not self._sz_config_mgr:
                return None
            return self._sz_config_mgr.get_default_config_id()
        except (SzError, Exception):
            return None

    def get_config_registry(self) -> Optional[str]:
        """Get the configuration registry information.

        Returns:
            Configuration registry JSON string if successful, None otherwise
        """
        try:
            if not self._sz_config_mgr:
                return None
            return self._sz_config_mgr.get_configs()
        except (SzError, Exception):
            return None

    def get_current_config(self) -> Optional[str]:
        """Get the current configuration as JSON.

        Returns:
            Current configuration JSON string if available, None otherwise
        """
        try:
            if not self._sz_config:
                return None

            # Check if we have a cached export
            if self._cached_config_json is not None:
                return self._cached_config_json

            # Export and cache the configuration
            self._cached_config_json = self._sz_config.export()
            return self._cached_config_json

        except (SzError, Exception):
            return None

    def export_config_to_file(self, file_path: Union[str, pathlib.Path]) -> bool:
        """Export current configuration to a file.

        Args:
            file_path: Path where to save the configuration

        Returns:
            True if export successful, False otherwise
        """
        try:
            config_json = self.get_current_config()
            if not config_json:
                return False

            with open(file_path, 'w', encoding='utf-8') as f:
                # Pretty print the JSON for readability
                config_dict = json.loads(config_json)
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            return True

        except (IOError, json.JSONDecodeError, Exception):
            return False

    def import_config_from_file(self, file_path: Union[str, pathlib.Path]) -> bool:
        """Import configuration from a file.

        Args:
            file_path: Path to the configuration file

        Returns:
            True if import successful, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_json = f.read()

            # Validate JSON
            config_dict = json.loads(config_json)

            # Create new sz_config from the imported JSON
            sz_config = self._sz_config_mgr.create_config_from_json(config_json)
            if sz_config:
                self._sz_config = sz_config
                self.config_updated = True
                self._clear_config_cache()
                return True
            else:
                return False

        except (IOError, json.JSONDecodeError, SzError, Exception):
            return False

    @property
    def current_config_id(self) -> Optional[int]:
        """Get the current configuration ID."""
        return self._current_config_id

    def get_config_data(self) -> Optional[Dict[str, Any]]:
        """Get the current configuration data as a dictionary.

        Returns:
            Configuration data dictionary if available, None otherwise
        """
        # Check if we have a cached result (including None)
        if hasattr(self, '_config_cache_set') and self._config_cache_set:
            return self._cached_config_data

        config_json = self.get_current_config()
        if not config_json:
            return None

        try:
            self._cached_config_data = json.loads(config_json)
            self._config_cache_set = True
            return self._cached_config_data
        except json.JSONDecodeError:
            return None

    def _clear_config_cache(self) -> None:
        """Clear the configuration cache."""
        self._cached_config_data = None
        self._config_cache_set = False

    @property
    def config_data(self):
        """Get the current configuration data."""
        return self.get_config_data()

    @config_data.setter
    def config_data(self, value):
        """Set the configuration data directly."""
        self._cached_config_data = value
        self._config_cache_set = True

    def update_config_data(self, config_data: Dict[str, Any]) -> bool:
        """Update configuration data from dictionary.

        Args:
            config_data: New configuration data dictionary

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Convert dict back to JSON and load into sz_config
            config_json = json.dumps(config_data, indent=2)
            sz_config = self._sz_config_mgr.create_config_from_json(config_json)

            if sz_config:
                self._sz_config = sz_config
                self.config_updated = True
                self._clear_config_cache()
                # Update cached data with the new data
                self._cached_config_data = config_data
                return True
            else:
                return False

        except (json.JSONEncodeError, SzError, Exception) as e:
            if self._verbose_logging:
                print(f"Failed to update configuration: {e}")
            return False

    def get_record(self, table: str, field: str, value: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get a single record from the configuration by field value.

        Args:
            table: Configuration table name (e.g., 'CFG_DSRC', 'CFG_FTYPE')
            field: Field name to search by
            value: Value to search for

        Returns:
            Record dictionary if found, None otherwise
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return None

        # Get the table from configuration
        table_data = config_data['G2_CONFIG'].get(table, [])
        if not table_data:
            return None

        # Search for the record
        for record in table_data:
            if str(record.get(field, "")) == str(value):
                return record

        return None

    def get_record_by_fields(self, table: str, field_values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get a single record from the configuration by multiple field values.

        Args:
            table: Configuration table name
            field_values: Dictionary of field names and values to match

        Returns:
            Record dictionary if found, None otherwise
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return None

        # Get the table from configuration
        table_data = config_data['G2_CONFIG'].get(table, [])
        if not table_data:
            return None

        # Search for the record that matches all field values
        for record in table_data:
            if all(str(record.get(field, "")) == str(value) for field, value in field_values.items()):
                return record

        return None

    def get_record_list(self, table: str, field: str = None, value: Union[str, int] = None) -> List[Dict[str, Any]]:
        """Get a list of records from the configuration.

        Args:
            table: Configuration table name
            field: Optional field name to filter by
            value: Optional value to filter by

        Returns:
            List of record dictionaries
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return []

        # Get the table from configuration
        table_data = config_data['G2_CONFIG'].get(table, [])
        if not table_data:
            return []

        # Filter records if field and value are specified
        if field is not None and value is not None:
            return [record for record in table_data
                    if str(record.get(field, "")) == str(value)]

        return table_data

    def add_record(self, table: str, record: Dict[str, Any]) -> bool:
        """Add a new record to the configuration.

        Args:
            table: Configuration table name
            record: Record dictionary to add

        Returns:
            True if successful, False otherwise
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return False

        # Ensure the table exists
        if table not in config_data['G2_CONFIG']:
            config_data['G2_CONFIG'][table] = []

        # Add the record
        config_data['G2_CONFIG'][table].append(record)

        # Update the configuration
        return self.update_config_data(config_data)

    def update_record(self, table: str, field: str, value: Union[str, int], updated_record: Dict[str, Any]) -> bool:
        """Update an existing record in the configuration.

        Args:
            table: Configuration table name
            field: Field name to identify the record
            value: Value to identify the record
            updated_record: Updated record dictionary

        Returns:
            True if successful, False otherwise
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return False

        table_data = config_data['G2_CONFIG'].get(table, [])
        if not table_data:
            return False

        # Find and update the record
        for i, record in enumerate(table_data):
            if str(record.get(field, "")) == str(value):
                config_data['G2_CONFIG'][table][i] = updated_record
                return self.update_config_data(config_data)

        return False

    def delete_record(self, table: str, field: str, value: Union[str, int]) -> bool:
        """Delete a record from the configuration.

        Args:
            table: Configuration table name
            field: Field name to identify the record
            value: Value to identify the record

        Returns:
            True if successful, False otherwise
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return False

        table_data = config_data['G2_CONFIG'].get(table, [])
        if not table_data:
            return False

        # Find and delete the record
        for i, record in enumerate(table_data):
            if str(record.get(field, "")) == str(value):
                del config_data['G2_CONFIG'][table][i]
                return self.update_config_data(config_data)

        return False

    def get_next_id(self, table: str, id_field: str, seed_order: int = 1000) -> int:
        """Get the next available ID for a table.

        Args:
            table: Configuration table name
            id_field: ID field name
            seed_order: Starting seed value for new IDs

        Returns:
            Next available ID
        """
        records = self.get_record_list(table)
        if not records:
            return seed_order

        max_id = max(int(record.get(id_field, 0)) for record in records)
        return max(max_id + 1, seed_order)

    def close(self) -> None:
        """Close the configuration manager and cleanup resources."""
        try:
            if self._sz_config:
                self._sz_config.close()
            if self._sz_config_mgr:
                self._sz_config_mgr.close()
            if self._sz_factory:
                self._sz_factory.close()
        except Exception:
            pass  # Ignore cleanup errors

        # Reset all instance variables
        self._sz_factory = None
        self._sz_config_mgr = None
        self._sz_config = None
        self._current_config_id = None
        self.config_data = None
        self.config_updated = False
        self._cached_config_data = None
        self._cached_config_json = None

    def is_initialized(self) -> bool:
        """Check if the manager is properly initialized.

        Returns:
            True if initialized, False otherwise
        """
        return (self._sz_factory is not None and
                self._sz_config_mgr is not None and
                self._sz_config is not None)