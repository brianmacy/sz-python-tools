"""Core configuration management functionality for sz_configtool.

This module provides the business logic for Senzing configuration operations,
separate from UI and display concerns.
"""

import json
import pathlib
from typing import Any, Dict, List, Optional, Union

from senzing import SzError
from senzing_core import SzAbstractFactoryCore
try:
    from ._tool_helpers import get_engine_config
except ImportError:
    from _tool_helpers import get_engine_config


class ConfigurationManager:
    """Manages Senzing configuration operations."""

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

            # Test that the configuration can be exported (validation step)
            try:
                test_export = sz_config.export()
                if not test_export:
                    return False
            except Exception:
                # If export fails, the config is not valid
                return False

            # Update instance configuration from the loaded config
            self._current_config_id = config_id
            self._sz_config = sz_config

            # Clear cache since we have a new configuration
            self._clear_config_cache()
            return True

        except (SzError, Exception) as e:
            if self._verbose_logging:
                print(f"Failed to load configuration: {e}")
            return False

    def save_config(self, comment: str = None) -> Optional[int]:
        """Save configuration changes to database following original pattern.

        Args:
            comment: Optional comment for the configuration change

        Returns:
            New configuration ID if successful, None otherwise
        """
        if not self.config_updated or not self.config_data:
            return None

        try:
            # Convert config data back to JSON
            config_json = json.dumps(self.config_data, indent=2)

            # Register the new configuration
            new_config_id = self._sz_config_mgr.register_config(
                config_json,
                comment or "Configuration updated by sz_configtool"
            )

            # Set as default
            self._sz_config_mgr.set_default_config_id(new_config_id)

            # Update our references
            self._current_config_id = new_config_id
            self._sz_config = self._sz_config_mgr.create_config_from_config_id(new_config_id)
            self.config_updated = False

            # Clear cache
            self._clear_config_cache()

            return new_config_id

        except SzError:
            return None

    def get_default_config_id(self) -> Optional[int]:
        """Get the default configuration ID.

        Returns:
            Default configuration ID or None if error
        """
        if not self._sz_config_mgr:
            return None

        try:
            return self._sz_config_mgr.get_default_config_id()
        except Exception:
            return None

    def get_config_registry(self) -> Optional[str]:
        """Get the configuration registry.

        Returns:
            Configuration registry as JSON string or None if error
        """
        if not self._sz_config_mgr:
            return None

        try:
            return self._sz_config_mgr.get_configs()
        except Exception:
            return None


    def get_current_config(self) -> Optional[str]:
        """Get the current configuration as JSON.

        Returns:
            Configuration JSON string or None if error
        """
        if not self._sz_config:
            return None

        # Use cached JSON if available
        if self._cached_config_json is not None:
            return self._cached_config_json

        try:
            self._cached_config_json = self._sz_config.export()
            return self._cached_config_json
        except Exception:
            return None

    def save_config(self, config_comment: str = "Updated by sz_configtool") -> Optional[int]:
        """Save the current configuration.

        Args:
            config_comment: Comment for the configuration save

        Returns:
            New configuration ID or None if error
        """
        if not self._sz_config_mgr or not self._sz_config:
            return None

        try:
            config_json = self._sz_config.export()
            return self._sz_config_mgr.register_config(config_json, config_comment)
        except Exception:
            return None

    def import_config_from_file(self, file_path: Union[str, pathlib.Path]) -> bool:
        """Import configuration from a JSON file.

        Args:
            file_path: Path to JSON configuration file

        Returns:
            True if successful, False otherwise
        """
        if not self._sz_config:
            return False

        try:
            file_path = pathlib.Path(file_path)
            if not file_path.exists():
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                config_json = f.read()

            # Validate JSON
            json.loads(config_json)

            self._sz_config.import_config(config_json)
            # Clear cache since config changed
            self._clear_config_cache()
            return True
        except Exception:
            return False

    def export_config_to_file(self, file_path: Union[str, pathlib.Path]) -> bool:
        """Export current configuration to a JSON file.

        Args:
            file_path: Path where to save the configuration

        Returns:
            True if successful, False otherwise
        """
        if not self._sz_config:
            return False

        try:
            config_json = self._sz_config.export()
            file_path = pathlib.Path(file_path)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(config_json)

            return True
        except Exception:
            return False

    def get_data_sources(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of data sources from current configuration.

        Returns:
            List of data source dictionaries or None if error
        """
        config_data = self.get_config_data()
        if not config_data:
            return None

        return config_data.get('G2_CONFIG', {}).get('CFG_DSRC', [])

    def add_data_source(self, data_source_code: str) -> bool:
        """Add a data source to the configuration.

        Args:
            data_source_code: Code for the new data source

        Returns:
            True if successful, False otherwise
        """
        if not self.config_data:
            return False

        try:
            # Normalize to uppercase like original
            data_source_code = data_source_code.upper()

            # Check if data source already exists
            data_sources = self.config_data.get('G2_CONFIG', {}).get('CFG_DSRC', [])
            for ds in data_sources:
                if ds.get('DSRC_CODE') == data_source_code:
                    return False  # Already exists

            # Get next ID (match original's pattern)
            next_id = max([ds.get('DSRC_ID', 0) for ds in data_sources] or [0]) + 1
            if next_id < 1000:
                next_id = 1000  # Start at 1000 like original

            # Add new data source (match original structure exactly)
            new_data_source = {
                'DSRC_ID': next_id,
                'DSRC_CODE': data_source_code,
                'DSRC_DESC': data_source_code,
                'DSRC_RELY': 1,
                'RETENTION_LEVEL': 'Remember',
                'CONVERSATIONAL': 'No'
            }

            # Add to in-memory configuration
            data_sources.append(new_data_source)

            # Mark configuration as updated
            self.config_updated = True

            return True

        except Exception as e:
            # Debug: print the actual error
            print(f"Debug: add_data_source error: {e}")
            print(f"Debug: config_data exists: {self.config_data is not None}")
            return False

    def delete_data_source(self, data_source_code: str) -> bool:
        """Delete a data source from the configuration.

        Args:
            data_source_code: Code of the data source to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._sz_config:
            return False

        try:
            # Get current configuration
            config_data = self.get_config_data()
            if not config_data:
                return False

            # Find and remove data source
            data_sources = config_data.get('G2_CONFIG', {}).get('CFG_DSRC', [])
            original_length = len(data_sources)

            # Filter out the data source to delete
            data_sources[:] = [ds for ds in data_sources if ds.get('DSRC_CODE') != data_source_code]

            # Check if anything was removed
            if len(data_sources) == original_length:
                return False  # Data source not found

            # Update configuration
            return self.update_config_data(config_data)

        except Exception:
            return False

    def close(self) -> None:
        """Clean up resources."""
        if self._sz_config:
            try:
                # Some Senzing config objects may have close method, try it for compatibility
                if hasattr(self._sz_config, 'close'):
                    self._sz_config.close()
            except Exception:
                pass  # Ignore all exceptions during cleanup
            self._sz_config = None

        if self._sz_config_mgr:
            try:
                self._sz_config_mgr.close()
            except Exception:
                pass  # Ignore all exceptions during cleanup

        if self._sz_factory:
            try:
                self._sz_factory.close()
            except Exception:
                pass  # Ignore all exceptions during cleanup

    @property
    def current_config_id(self) -> Optional[int]:
        """Get the current configuration ID."""
        return self._current_config_id

    def get_config_data(self) -> Optional[Dict[str, Any]]:
        """Get the current configuration as parsed JSON data.

        Returns:
            Configuration data as dictionary or None if error
        """
        # Check if we have cached data
        if hasattr(self, '_cached_config_data') and self._cached_config_data is not None:
            return self._cached_config_data

        # Get current config JSON (this will use the JSON cache)
        config_json = self.get_current_config()
        if not config_json:
            return None

        try:
            # Parse and cache the data
            self._cached_config_data = json.loads(config_json)
            return self._cached_config_data
        except (json.JSONDecodeError, TypeError):
            # TypeError can occur if config_json is not a string (e.g., Mock object)
            return None

    @property
    def config_data(self) -> Optional[Dict[str, Any]]:
        """Get the current configuration data."""
        return self.get_config_data()

    @config_data.setter
    def config_data(self, value: Optional[Dict[str, Any]]) -> None:
        """Set the configuration data directly."""
        if value is None:
            self._clear_config_cache()
        else:
            self._cached_config_data = value
            try:
                self._cached_config_json = json.dumps(value, indent=2) if value else None
            except (TypeError, ValueError):
                # If JSON serialization fails, just cache the data without JSON
                self._cached_config_json = None

    def _clear_config_cache(self) -> None:
        """Clear the configuration cache when data changes."""
        self._cached_config_data = None
        self._cached_config_json = None

    def update_config_data(self, config_data: Dict[str, Any]) -> bool:
        """Update configuration from data dictionary.

        Args:
            config_data: Configuration data dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert config data to JSON to validate it
            config_json = json.dumps(config_data, indent=2)

            # If we have a config manager, try to update via Senzing
            if self._sz_config_mgr and self._current_config_id:
                try:
                    # Create new config from JSON
                    new_sz_config = self._sz_config_mgr.create_config_from_json(config_json)
                    if new_sz_config:
                        self._sz_config = new_sz_config
                        # Clear cache since config changed
                        self._clear_config_cache()
                        return True
                except Exception:
                    pass  # Fall through to direct import

            # For testing or when Senzing is not fully initialized,
            # import into the existing sz_config object
            if hasattr(self, '_sz_config') and self._sz_config:
                try:
                    self._sz_config.import_config(config_json)
                    # Clear cache since config changed - cache will be repopulated on next access
                    self._clear_config_cache()
                    return True
                except AttributeError:
                    # If import_config doesn't exist, we can't update
                    return False

            return False

        except (json.JSONDecodeError, Exception) as e:
            return False

    def get_record(self, table: str, field: str, value: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get a single record from a configuration table.

        Args:
            table: Configuration table name (e.g., 'CFG_FTYPE')
            field: Field name to search by
            value: Value to search for

        Returns:
            Record dictionary or None if not found
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return None

        g2_config = config_data['G2_CONFIG']
        if table not in g2_config:
            return None

        for record in g2_config[table]:
            if record.get(field) == value:
                return record

        return None

    def get_record_by_fields(self, table: str, field_values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get a single record from a configuration table by multiple field criteria.

        Args:
            table: Configuration table name (e.g., 'CFG_EFBOM')
            field_values: Dictionary of field names to values that must all match

        Returns:
            Record dictionary or None if not found
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return None

        g2_config = config_data['G2_CONFIG']
        if table not in g2_config:
            return None

        for record in g2_config[table]:
            # Check if all field criteria match
            match = True
            for field, value in field_values.items():
                if record.get(field) != value:
                    match = False
                    break
            if match:
                return record

        return None

    def get_record_list(self, table: str, field: str = None, value: Union[str, int] = None) -> List[Dict[str, Any]]:
        """Get records from a configuration table.

        Args:
            table: Configuration table name
            field: Optional field name to filter by
            value: Optional value to filter for

        Returns:
            List of record dictionaries
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return []

        g2_config = config_data['G2_CONFIG']
        if table not in g2_config:
            return []

        records = g2_config[table]
        if field is None or value is None:
            return records

        # Filter records
        return [record for record in records if record.get(field) == value]

    def add_record(self, table: str, record: Dict[str, Any]) -> bool:
        """Add a record to a configuration table.

        Args:
            table: Configuration table name
            record: Record dictionary to add

        Returns:
            True if successful, False otherwise
        """
        config_data = self.get_config_data()
        if not config_data:
            return False

        if 'G2_CONFIG' not in config_data:
            config_data['G2_CONFIG'] = {}

        g2_config = config_data['G2_CONFIG']
        if table not in g2_config:
            g2_config[table] = []

        g2_config[table].append(record)
        return self.update_config_data(config_data)

    def update_record(self, table: str, field: str, value: Union[str, int], updated_record: Dict[str, Any]) -> bool:
        """Update a record in a configuration table.

        Args:
            table: Configuration table name
            field: Field name to search by
            value: Value to search for
            updated_record: Updated record dictionary

        Returns:
            True if successful, False otherwise
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return False

        g2_config = config_data['G2_CONFIG']
        if table not in g2_config:
            return False

        # Find and update the record
        for i, record in enumerate(g2_config[table]):
            if record.get(field) == value:
                g2_config[table][i] = updated_record
                return self.update_config_data(config_data)

        return False

    def delete_record(self, table: str, field: str, value: Union[str, int]) -> bool:
        """Delete a record from a configuration table.

        Args:
            table: Configuration table name
            field: Field name to search by
            value: Value to search for

        Returns:
            True if successful, False otherwise
        """
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return False

        g2_config = config_data['G2_CONFIG']
        if table not in g2_config:
            return False

        # Find and remove the record
        original_count = len(g2_config[table])
        g2_config[table] = [record for record in g2_config[table] if record.get(field) != value]

        if len(g2_config[table]) < original_count:
            return self.update_config_data(config_data)

        return False

    def get_next_id(self, table: str, id_field: str, seed_order: int = 1000) -> int:
        """Get the next available ID for a table.

        Args:
            table: Configuration table name
            id_field: ID field name
            seed_order: Starting seed for new IDs

        Returns:
            Next available ID
        """
        records = self.get_record_list(table)
        if not records:
            return seed_order

        max_id = max(record.get(id_field, 0) for record in records)
        return max(max_id + 1, seed_order)

    # Feature Management Methods
    def get_features(self) -> List[Dict[str, Any]]:
        """Get list of all features.

        Returns:
            List of feature dictionaries
        """
        return self.get_record_list('CFG_FTYPE')

    def get_feature(self, feature_code: str) -> Optional[Dict[str, Any]]:
        """Get a specific feature by code.

        Args:
            feature_code: Feature code to retrieve

        Returns:
            Feature dictionary or None if not found
        """
        return self.get_record('CFG_FTYPE', 'FTYPE_CODE', feature_code)

    def add_feature(self, feature_code: str, feature_description: str = None) -> bool:
        """Add a new feature.

        Args:
            feature_code: Unique feature code
            feature_description: Optional feature description

        Returns:
            True if successful, False otherwise
        """
        # Check if feature already exists
        if self.get_feature(feature_code):
            return False

        next_id = self.get_next_id('CFG_FTYPE', 'FTYPE_ID', 1000)

        new_feature = {
            'FTYPE_ID': next_id,
            'FTYPE_CODE': feature_code,
            'FTYPE_DESC': feature_description or feature_code,
            'FCLASS_ID': 1,  # Default feature class
            'VERSION': 1,
            'SHOW_IN_MATCH_KEY': 'No'
        }

        return self.add_record('CFG_FTYPE', new_feature)

    def update_feature(self, feature_code: str, updates: Dict[str, Any]) -> bool:
        """Update an existing feature.

        Args:
            feature_code: Feature code to update
            updates: Dictionary of updates to apply

        Returns:
            True if successful, False otherwise
        """
        feature = self.get_feature(feature_code)
        if not feature:
            return False

        updated_feature = feature.copy()
        updated_feature.update(updates)

        return self.update_record('CFG_FTYPE', 'FTYPE_CODE', feature_code, updated_feature)

    def delete_feature(self, feature_code: str) -> bool:
        """Delete a feature.

        Args:
            feature_code: Feature code to delete

        Returns:
            True if successful, False otherwise
        """
        feature = self.get_feature(feature_code)
        if not feature:
            return False

        # Check for dependencies (attributes using this feature)
        dependent_attrs = self.get_record_list('CFG_ATTR', 'FTYPE_CODE', feature_code)
        if dependent_attrs:
            return False  # Cannot delete feature with dependent attributes

        return self.delete_record('CFG_FTYPE', 'FTYPE_CODE', feature_code)

    # Attribute Management Methods
    def get_attributes(self) -> List[Dict[str, Any]]:
        """Get list of all attributes.

        Returns:
            List of attribute dictionaries
        """
        return self.get_record_list('CFG_ATTR')

    def get_attribute(self, attr_code: str) -> Optional[Dict[str, Any]]:
        """Get a specific attribute by code.

        Args:
            attr_code: Attribute code to retrieve

        Returns:
            Attribute dictionary or None if not found
        """
        return self.get_record('CFG_ATTR', 'ATTR_CODE', attr_code)

    def add_attribute(self, attr_code: str, attr_class: str, feature_code: str = None,
                     element_code: str = None, required: str = 'No') -> bool:
        """Add a new attribute.

        Args:
            attr_code: Unique attribute code
            attr_class: Attribute class (e.g., 'NAME', 'ADDRESS')
            feature_code: Optional feature type code
            element_code: Optional element code
            required: Whether attribute is required ('Yes'/'No')

        Returns:
            True if successful, False otherwise
        """
        # Check if attribute already exists
        if self.get_attribute(attr_code):
            return False

        next_id = self.get_next_id('CFG_ATTR', 'ATTR_ID', 1001)

        new_attribute = {
            'ATTR_ID': next_id,
            'ATTR_CODE': attr_code,
            'ATTR_CLASS': attr_class,
            'FTYPE_CODE': feature_code,
            'FELEM_CODE': element_code,
            'FELEM_REQ': required,
            'DEFAULT_VALUE': None,
            'INTERNAL': 'No'
        }

        return self.add_record('CFG_ATTR', new_attribute)

    def delete_attribute(self, attr_code: str) -> bool:
        """Delete an attribute.

        Args:
            attr_code: Attribute code to delete

        Returns:
            True if successful, False otherwise
        """
        return self.delete_record('CFG_ATTR', 'ATTR_CODE', attr_code)

    # Element Management Methods
    def get_elements(self) -> List[Dict[str, Any]]:
        """Get list of all elements.

        Returns:
            List of element dictionaries
        """
        return self.get_record_list('CFG_FELEM')

    def get_element(self, element_code: str) -> Optional[Dict[str, Any]]:
        """Get a specific element by code.

        Args:
            element_code: Element code to retrieve

        Returns:
            Element dictionary or None if not found
        """
        return self.get_record('CFG_FELEM', 'FELEM_CODE', element_code)

    def add_element(self, element_code: str, data_type: str = 'string') -> bool:
        """Add a new element.

        Args:
            element_code: Unique element code
            data_type: Element data type

        Returns:
            True if successful, False otherwise
        """
        # Check if element already exists
        if self.get_element(element_code):
            return False

        next_id = self.get_next_id('CFG_FELEM', 'FELEM_ID', 1001)

        new_element = {
            'FELEM_ID': next_id,
            'FELEM_CODE': element_code,
            'DATA_TYPE': data_type,
            'TOKENIZE': 'No'
        }

        return self.add_record('CFG_FELEM', new_element)

    def delete_element(self, element_code: str) -> bool:
        """Delete an element.

        Args:
            element_code: Element code to delete

        Returns:
            True if successful, False otherwise
        """
        element = self.get_element(element_code)
        if not element:
            return False

        # Check for dependencies (features using this element)
        dependent_features = self.get_record_list('CFG_FBOM', 'FELEM_ID', element['FELEM_ID'])
        if dependent_features:
            return False  # Cannot delete element with dependencies

        return self.delete_record('CFG_FELEM', 'FELEM_CODE', element_code)

    # Comparison Function Management
    def get_comparison_functions(self) -> List[Dict[str, Any]]:
        """Get list of all comparison functions."""
        return self.get_record_list('CFG_CFRTN')

    def add_comparison_function(self, function_id: int, function_code: str,
                              connect_str: str, language: str = 'C') -> bool:
        """Add a new comparison function."""
        new_function = {
            'CFRTN_ID': function_id,
            'CFRTN_CODE': function_code,
            'CONNECT_STR': connect_str,
            'LANGUAGE': language,
            'VERSION': '1.0.0'
        }
        return self.add_record('CFG_CFRTN', new_function)

    def delete_comparison_function(self, function_code: str) -> bool:
        """Delete a comparison function."""
        return self.delete_record('CFG_CFRTN', 'CFRTN_CODE', function_code)

    # Expression Function Management
    def get_expression_functions(self) -> List[Dict[str, Any]]:
        """Get list of all expression functions."""
        return self.get_record_list('CFG_EFUNC')

    def add_expression_function(self, function_id: int, function_code: str,
                              connect_str: str, language: str = 'C') -> bool:
        """Add a new expression function."""
        new_function = {
            'EFUNC_ID': function_id,
            'EFUNC_CODE': function_code,
            'CONNECT_STR': connect_str,
            'LANGUAGE': language,
            'VERSION': '1.0.0'
        }
        return self.add_record('CFG_EFUNC', new_function)

    def delete_expression_function(self, function_code: str) -> bool:
        """Delete an expression function."""
        return self.delete_record('CFG_EFUNC', 'EFUNC_CODE', function_code)

    # Comparison Call Management
    def get_comparison_calls(self) -> List[Dict[str, Any]]:
        """Get list of all comparison calls."""
        return self.get_record_list('CFG_CFCALL')

    def get_comparison_call(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific comparison call."""
        return self.get_record('CFG_CFCALL', 'CFCALL_ID', call_id)

    def add_comparison_call(self, function_code: str, exec_order: int = 1) -> bool:
        """Add a new comparison call."""
        next_id = self.get_next_id('CFG_CFCALL', 'CFCALL_ID', 1)

        new_call = {
            'CFCALL_ID': next_id,
            'CFRTN_CODE': function_code,
            'EXEC_ORDER': exec_order
        }
        return self.add_record('CFG_CFCALL', new_call)

    def delete_comparison_call(self, call_id: int) -> bool:
        """Delete a comparison call."""
        return self.delete_record('CFG_CFCALL', 'CFCALL_ID', call_id)

    # Expression Call Management
    def get_expression_calls(self) -> List[Dict[str, Any]]:
        """Get list of all expression calls."""
        return self.get_record_list('CFG_ECALL')

    def get_expression_call(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific expression call."""
        return self.get_record('CFG_ECALL', 'ECALL_ID', call_id)

    def add_expression_call(self, function_code: str, exec_order: int = 1) -> bool:
        """Add a new expression call."""
        next_id = self.get_next_id('CFG_ECALL', 'ECALL_ID', 1)

        new_call = {
            'ECALL_ID': next_id,
            'EFUNC_CODE': function_code,
            'EXEC_ORDER': exec_order
        }
        return self.add_record('CFG_ECALL', new_call)

    def delete_expression_call(self, call_id: int) -> bool:
        """Delete an expression call."""
        return self.delete_record('CFG_ECALL', 'ECALL_ID', call_id)

    # Behavior Override Management
    def get_behavior_overrides(self) -> List[Dict[str, Any]]:
        """Get list of all behavior overrides."""
        return self.get_record_list('CFG_EBOM')

    def add_behavior_override(self, feature_code: str, behavior: str,
                            exec_order: int = 1) -> bool:
        """Add a behavior override."""
        next_id = self.get_next_id('CFG_EBOM', 'EBOM_ID', 1)

        new_override = {
            'EBOM_ID': next_id,
            'FTYPE_CODE': feature_code,
            'BEHAVIOR': behavior,
            'EXEC_ORDER': exec_order
        }
        return self.add_record('CFG_EBOM', new_override)

    def delete_behavior_override(self, override_id: int) -> bool:
        """Delete a behavior override."""
        return self.delete_record('CFG_EBOM', 'EBOM_ID', override_id)

    # Configuration Section Management
    def get_config_sections(self) -> List[Dict[str, Any]]:
        """Get list of configuration sections."""
        return self.get_record_list('CONFIG_BASE_TABLE')

    def add_config_section(self, section_name: str, section_type: str = 'SYSTEM') -> bool:
        """Add a configuration section."""
        new_section = {
            'CONFIG_BASE_TABLE_ID': self.get_next_id('CONFIG_BASE_TABLE', 'CONFIG_BASE_TABLE_ID', 1),
            'CONFIG_BASE_TABLE_CODE': section_name,
            'CONFIG_BASE_TABLE_NAME': section_name,
            'CONFIG_BASE_TABLE_TYPE': section_type
        }
        return self.add_record('CONFIG_BASE_TABLE', new_section)

    def delete_config_section(self, section_name: str) -> bool:
        """Delete a configuration section."""
        return self.delete_record('CONFIG_BASE_TABLE', 'CONFIG_BASE_TABLE_CODE', section_name)

    # Feature Element (FBOM) Management
    def add_element_to_feature(self, feature_code: str, element_code: str,
                             exec_order: int = 1) -> bool:
        """Add an element to a feature."""
        feature = self.get_feature(feature_code)
        element = self.get_element(element_code)

        if not feature or not element:
            return False

        next_id = self.get_next_id('CFG_FBOM', 'FBOM_ID', 1)

        new_fbom = {
            'FBOM_ID': next_id,
            'FTYPE_ID': feature['FTYPE_ID'],
            'FELEM_ID': element['FELEM_ID'],
            'EXEC_ORDER': exec_order
        }
        return self.add_record('CFG_FBOM', new_fbom)

    def remove_element_from_feature(self, feature_code: str, element_code: str) -> bool:
        """Remove an element from a feature."""
        feature = self.get_feature(feature_code)
        element = self.get_element(element_code)

        if not feature or not element:
            return False

        # Find and delete the FBOM record
        fbom_records = self.get_record_list('CFG_FBOM')
        for record in fbom_records:
            if (record['FTYPE_ID'] == feature['FTYPE_ID'] and
                record['FELEM_ID'] == element['FELEM_ID']):
                return self.delete_record('CFG_FBOM', 'FBOM_ID', record['FBOM_ID'])

        return False

    # Generic Threshold Management
    def get_generic_thresholds(self) -> List[Dict[str, Any]]:
        """Get list of generic thresholds."""
        return self.get_record_list('CFG_GPLAN')

    def add_generic_threshold(self, feature_code: str, behavior: str,
                            candidate_cap: int = -1, scoring_cap: int = -1) -> bool:
        """Add a generic threshold."""
        next_id = self.get_next_id('CFG_GPLAN', 'GPLAN_ID', 1)

        new_threshold = {
            'GPLAN_ID': next_id,
            'FTYPE_CODE': feature_code,
            'BEHAVIOR': behavior,
            'CANDIDATE_CAP': candidate_cap,
            'SCORING_CAP': scoring_cap
        }
        return self.add_record('CFG_GPLAN', new_threshold)

    def delete_generic_threshold(self, threshold_id: int) -> bool:
        """Delete a generic threshold."""
        return self.delete_record('CFG_GPLAN', 'GPLAN_ID', threshold_id)

    # System Parameter Management
    def get_system_parameters(self) -> List[Dict[str, Any]]:
        """Get system parameters."""
        return self.get_record_list('SYS_OOM')

    def set_system_parameter(self, parameter_name: str, parameter_value: str) -> bool:
        """Set a system parameter."""
        # Check if parameter exists
        existing = self.get_record('SYS_OOM', 'OOM_TYPE', parameter_name)
        if existing:
            # Update existing parameter
            config_data = self.get_config_data()
            if not config_data:
                return False

            for record in config_data['G2_CONFIG']['SYS_OOM']:
                if record['OOM_TYPE'] == parameter_name:
                    record['OOM_LEVEL'] = parameter_value
                    return self.update_config_data(config_data)
        else:
            # Add new parameter
            next_id = self.get_next_id('SYS_OOM', 'OOM_ID', 1)
            new_param = {
                'OOM_ID': next_id,
                'OOM_TYPE': parameter_name,
                'OOM_LEVEL': parameter_value
            }
            return self.add_record('SYS_OOM', new_param)

        return False

    # Standardize Call Management
    def get_standardize_calls(self) -> List[Dict[str, Any]]:
        """Get list of all standardize calls."""
        return self.get_record_list('CFG_SFCALL')

    def get_standardize_call(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific standardize call."""
        return self.get_record('CFG_SFCALL', 'SFCALL_ID', call_id)

    def add_standardize_call(self, function_code: str, exec_order: int = 1) -> bool:
        """Add a new standardize call."""
        next_id = self.get_next_id('CFG_SFCALL', 'SFCALL_ID', 1)
        new_call = {
            'SFCALL_ID': next_id,
            'SFUNC_CODE': function_code,
            'EXEC_ORDER': exec_order
        }
        return self.add_record('CFG_SFCALL', new_call)

    def delete_standardize_call(self, call_id: int) -> bool:
        """Delete a standardize call."""
        return self.delete_record('CFG_SFCALL', 'SFCALL_ID', call_id)

    # Standardize Function Management
    def get_standardize_functions(self) -> List[Dict[str, Any]]:
        """Get list of all standardize functions."""
        return self.get_record_list('CFG_SFUNC')

    def add_standardize_function(self, function_id: int, function_code: str,
                                connect_str: str, language: str = 'C') -> bool:
        """Add a new standardize function."""
        new_function = {
            'SFUNC_ID': function_id,
            'SFUNC_CODE': function_code,
            'CONNECT_STR': connect_str,
            'LANGUAGE': language,
            'VERSION': '1.0.0'
        }
        return self.add_record('CFG_SFUNC', new_function)

    def delete_standardize_function(self, function_code: str) -> bool:
        """Delete a standardize function."""
        return self.delete_record('CFG_SFUNC', 'SFUNC_CODE', function_code)

    # Distinct Call Management
    def get_distinct_calls(self) -> List[Dict[str, Any]]:
        """Get list of all distinct calls."""
        return self.get_record_list('CFG_DCALL')

    def get_distinct_call(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific distinct call."""
        return self.get_record('CFG_DCALL', 'DCALL_ID', call_id)

    def add_distinct_call(self, function_code: str, exec_order: int = 1) -> bool:
        """Add a new distinct call."""
        next_id = self.get_next_id('CFG_DCALL', 'DCALL_ID', 1)
        new_call = {
            'DCALL_ID': next_id,
            'DFUNC_CODE': function_code,
            'EXEC_ORDER': exec_order
        }
        return self.add_record('CFG_DCALL', new_call)

    def delete_distinct_call(self, call_id: int) -> bool:
        """Delete a distinct call."""
        return self.delete_record('CFG_DCALL', 'DCALL_ID', call_id)

    # Distinct Function Management
    def get_distinct_functions(self) -> List[Dict[str, Any]]:
        """Get list of all distinct functions."""
        return self.get_record_list('CFG_DFUNC')

    def add_distinct_function(self, function_id: int, function_code: str,
                            connect_str: str, language: str = 'C') -> bool:
        """Add a new distinct function."""
        new_function = {
            'DFUNC_ID': function_id,
            'DFUNC_CODE': function_code,
            'CONNECT_STR': connect_str,
            'LANGUAGE': language,
            'VERSION': '1.0.0'
        }
        return self.add_record('CFG_DFUNC', new_function)

    def delete_distinct_function(self, function_code: str) -> bool:
        """Delete a distinct function."""
        return self.delete_record('CFG_DFUNC', 'DFUNC_CODE', function_code)

    # Fragment Management
    def get_fragments(self) -> List[Dict[str, Any]]:
        """Get list of all fragments."""
        return self.get_record_list('CFG_ERFRAG')

    def get_fragment(self, fragment_code: str) -> Optional[Dict[str, Any]]:
        """Get a specific fragment."""
        return self.get_record('CFG_ERFRAG', 'ERFRAG_CODE', fragment_code)

    def add_fragment(self, fragment_code: str, fragment_desc: str = None) -> bool:
        """Add a new fragment."""
        if self.get_fragment(fragment_code):
            return False

        next_id = self.get_next_id('CFG_FRAG', 'FRAG_ID', 1)
        new_fragment = {
            'FRAG_ID': next_id,
            'FRAG_CODE': fragment_code,
            'FRAG_DESC': fragment_desc or fragment_code
        }
        return self.add_record('CFG_FRAG', new_fragment)

    def update_fragment(self, fragment_code: str, updates: Dict[str, Any]) -> bool:
        """Update a fragment."""
        fragment = self.get_fragment(fragment_code)
        if not fragment:
            return False

        updated_fragment = fragment.copy()
        updated_fragment.update(updates)
        return self.update_record('CFG_FRAG', 'FRAG_CODE', fragment_code, updated_fragment)

    def delete_fragment(self, fragment_code: str) -> bool:
        """Delete a fragment."""
        return self.delete_record('CFG_FRAG', 'FRAG_CODE', fragment_code)

    # Rule Management
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get list of all rules."""
        return self.get_record_list('CFG_ERRULE')

    def get_rule(self, rule_code: str) -> Optional[Dict[str, Any]]:
        """Get a specific rule."""
        return self.get_record('CFG_ERRULE', 'ERRULE_CODE', rule_code)

    def add_rule(self, rule_code: str, rule_desc: str = None, is_disclosed: str = 'No') -> bool:
        """Add a new rule."""
        if self.get_rule(rule_code):
            return False

        next_id = self.get_next_id('CFG_RCLASS', 'RCLASS_ID', 1)
        new_rule = {
            'RCLASS_ID': next_id,
            'RCLASS_CODE': rule_code,
            'RCLASS_DESC': rule_desc or rule_code,
            'IS_DISCLOSED': is_disclosed
        }
        return self.add_record('CFG_RCLASS', new_rule)

    def update_rule(self, rule_code: str, updates: Dict[str, Any]) -> bool:
        """Update a rule."""
        rule = self.get_rule(rule_code)
        if not rule:
            return False

        updated_rule = rule.copy()
        updated_rule.update(updates)
        return self.update_record('CFG_RCLASS', 'RCLASS_CODE', rule_code, updated_rule)

    def delete_rule(self, rule_code: str) -> bool:
        """Delete a rule."""
        return self.delete_record('CFG_RCLASS', 'RCLASS_CODE', rule_code)

    # Comparison Threshold Management
    def get_comparison_thresholds(self) -> List[Dict[str, Any]]:
        """Get list of comparison thresholds."""
        return self.get_record_list('CFG_CFRTN')

    def add_comparison_threshold(self, function_code: str, same_score: int = 100,
                                close_score: int = 85, likely_score: int = 75,
                                plausible_score: int = 65, unlikely_score: int = 50) -> bool:
        """Add comparison threshold."""
        # Update existing function record with threshold scores
        function = self.get_record('CFG_CFRTN', 'CFRTN_CODE', function_code)
        if not function:
            return False

        function.update({
            'SAME_SCORE': same_score,
            'CLOSE_SCORE': close_score,
            'LIKELY_SCORE': likely_score,
            'PLAUSIBLE_SCORE': plausible_score,
            'UNLIKELY_SCORE': unlikely_score
        })
        return self.update_record('CFG_CFRTN', 'CFRTN_CODE', function_code, function)

    def delete_comparison_threshold(self, function_code: str) -> bool:
        """Delete comparison threshold (remove scores from function)."""
        function = self.get_record('CFG_CFRTN', 'CFRTN_CODE', function_code)
        if not function:
            return False

        # Remove threshold scores
        for score_key in ['SAME_SCORE', 'CLOSE_SCORE', 'LIKELY_SCORE', 'PLAUSIBLE_SCORE', 'UNLIKELY_SCORE']:
            function.pop(score_key, None)

        return self.update_record('CFG_CFRTN', 'CFRTN_CODE', function_code, function)

    # Generic Plan Management
    def get_generic_plans(self) -> List[Dict[str, Any]]:
        """Get list of generic plans."""
        return self.get_record_list('CFG_GPLAN')

    def clone_generic_plan(self, source_id: int, new_feature_code: str) -> bool:
        """Clone a generic plan for new feature."""
        source_plan = self.get_record('CFG_GPLAN', 'GPLAN_ID', source_id)
        if not source_plan:
            return False

        new_plan = source_plan.copy()
        new_plan['GPLAN_ID'] = self.get_next_id('CFG_GPLAN', 'GPLAN_ID', 1)
        new_plan['FTYPE_CODE'] = new_feature_code

        return self.add_record('CFG_GPLAN', new_plan)

    def delete_generic_plan(self, plan_id: int) -> bool:
        """Delete a generic plan."""
        return self.delete_record('CFG_GPLAN', 'GPLAN_ID', plan_id)

    # Reference Code Management
    def get_reference_codes(self) -> List[Dict[str, Any]]:
        """Get reference codes."""
        return self.get_record_list('CFG_RTYPE')

    # Call Element Management (shared by comparison/expression/distinct calls)
    def add_call_element(self, call_table: str, call_id_field: str, call_id: int,
                        feature_code: str, element_code: str, exec_order: int = 1) -> bool:
        """Add element to comparison/expression/distinct call."""
        feature = self.get_feature(feature_code)
        element = self.get_element(element_code)

        if not feature or not element:
            return False

        # Determine the correct element table and ID field
        element_table = call_table.replace('CFG_', 'CFG_') + 'E'  # e.g., CFG_CFCALLE
        element_id_field = call_id_field.replace('_ID', 'E_ID')  # e.g., CFCALLE_ID

        next_id = self.get_next_id(element_table, element_id_field, 1)

        new_element = {
            element_id_field: next_id,
            call_id_field: call_id,
            'FTYPE_ID': feature['FTYPE_ID'],
            'FELEM_ID': element['FELEM_ID'],
            'EXEC_ORDER': exec_order
        }
        return self.add_record(element_table, new_element)

    def delete_call_element(self, call_table: str, call_id_field: str, call_id: int,
                           feature_code: str, element_code: str) -> bool:
        """Delete element from comparison/expression/distinct call."""
        feature = self.get_feature(feature_code)
        element = self.get_element(element_code)

        if not feature or not element:
            return False

        element_table = call_table.replace('CFG_', 'CFG_') + 'E'
        element_id_field = call_id_field.replace('_ID', 'E_ID')

        # Find and delete the element record
        element_records = self.get_record_list(element_table)
        for record in element_records:
            if (record[call_id_field] == call_id and
                record['FTYPE_ID'] == feature['FTYPE_ID'] and
                record['FELEM_ID'] == element['FELEM_ID']):
                return self.delete_record(element_table, element_id_field, record[element_id_field])

        return False

    # Name Hash Management
    def add_to_namehash(self, feature_code: str, element_code: str) -> bool:
        """Add feature/element to name hash."""
        return self.add_call_element('CFG_ECALL', 'ECALL_ID', 1, feature_code, element_code)

    def delete_from_namehash(self, feature_code: str, element_code: str) -> bool:
        """Delete feature/element from name hash."""
        return self.delete_call_element('CFG_ECALL', 'ECALL_ID', 1, feature_code, element_code)

    # Template Management
    def apply_template(self, template_name: str, feature_code: str) -> bool:
        """Apply a template to create feature with attributes."""
        # This is a simplified template system - in practice would have more complex logic
        templates = {
            'NAME': {
                'elements': ['FULL_NAME', 'SURNAME', 'GIVEN_NAME'],
                'attributes': ['PRIMARY_NAME', 'ALIAS']
            },
            'ADDRESS': {
                'elements': ['ADDR_FULL', 'ADDR_LINE1', 'ADDR_CITY', 'ADDR_STATE', 'ADDR_POSTAL_CODE'],
                'attributes': ['HOME_ADDRESS', 'BUSINESS_ADDRESS']
            }
        }

        if template_name not in templates:
            return False

        template = templates[template_name]

        # Add feature
        if not self.add_feature(feature_code, f'{template_name} feature'):
            return False

        # Add elements and attributes based on template
        for i, element_code in enumerate(template['elements']):
            if not self.get_element(element_code):
                self.add_element(element_code)
            self.add_element_to_feature(feature_code, element_code, i + 1)

        for attr_code in template['attributes']:
            self.add_attribute(attr_code, template_name, feature_code)

        return True

    # Configuration Version Management
    def get_compatibility_version(self) -> Optional[str]:
        """Get configuration compatibility version."""
        config_data = self.get_config_data()
        if not config_data:
            return None
        return config_data.get('G2_CONFIG', {}).get('CONFIG_BASE_VERSION', {}).get('VERSION')

    def update_compatibility_version(self, version: str) -> bool:
        """Update configuration compatibility version."""
        config_data = self.get_config_data()
        if not config_data:
            return False

        if 'G2_CONFIG' not in config_data:
            config_data['G2_CONFIG'] = {}

        if 'CONFIG_BASE_VERSION' not in config_data['G2_CONFIG']:
            config_data['G2_CONFIG']['CONFIG_BASE_VERSION'] = {}

        config_data['G2_CONFIG']['CONFIG_BASE_VERSION']['VERSION'] = version
        return self.update_config_data(config_data)

    def verify_compatibility_version(self, expected_version: str) -> bool:
        """Verify configuration compatibility version."""
        current_version = self.get_compatibility_version()
        return current_version == expected_version

    # Settings Management
    def set_setting(self, setting_name: str, setting_value: str) -> bool:
        """Set a configuration setting."""
        return self.set_system_parameter(setting_name, setting_value)

    # Touch/Update timestamp
    def touch_config(self) -> bool:
        """Update configuration timestamp."""
        import time
        timestamp = str(int(time.time()))
        return self.set_setting('LAST_UPDATED', timestamp)

    @property
    def is_initialized(self) -> bool:
        """Check if Senzing components are initialized."""
        return self._sz_config is not None and self._sz_config_mgr is not None

    # JSON Transformation Methods for Backward Compatibility

    def format_feature_json(self, ftype_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw CFG_FTYPE database record to user-friendly JSON format.

        This recreates the exact JSON structure from the original sz_configtool.

        Args:
            ftype_record: Raw database record from CFG_FTYPE table

        Returns:
            Transformed JSON dict with user-friendly field names and nested structures
        """
        if not ftype_record:
            return {}

        # Get element list for this feature
        element_list = self._get_feature_element_list(ftype_record.get('FTYPE_ID'))

        # Get function relationships
        expression_func = self._get_feature_expression_function(ftype_record.get('FTYPE_CODE'))
        comparison_func = self._get_feature_comparison_function(ftype_record.get('FTYPE_CODE'))
        standardize_func = self._get_feature_standardize_function(ftype_record.get('FTYPE_CODE'))

        # Transform to user-friendly format matching original exactly
        transformed = {
            "id": ftype_record.get('FTYPE_ID'),
            "feature": ftype_record.get('FTYPE_CODE'),
            "class": self._get_feature_class_name(ftype_record.get('FCLASS_ID')),
            "elementList": element_list,
            "anonymize": ftype_record.get('ANONYMIZE', 'No'),
            "derived": ftype_record.get('DERIVED', 'No'),
            "matchKey": 'Yes' if ftype_record.get('SHOW_IN_MATCH_KEY') == 'Yes' else 'No',
            "display": 'Yes' if ftype_record.get('SHOW_IN_MATCH_KEY') == 'Yes' else 'No',
            "candidates": 'Yes' if ftype_record.get('USED_FOR_CAND') == 'Yes' else 'No',
            "version": ftype_record.get('VERSION', 1),
            "expression": expression_func,
            "comparison": comparison_func,
            "standardize": standardize_func,
            "behavior": ""  # TODO: Add behavior lookup
        }

        return transformed

    def format_attribute_json(self, attr_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw CFG_ATTR database record to user-friendly JSON format.

        Args:
            attr_record: Raw database record from CFG_ATTR table

        Returns:
            Transformed JSON dict with user-friendly field names
        """
        if not attr_record:
            return {}

        # Transform to user-friendly format matching original exactly
        transformed = {
            "id": attr_record.get('ATTR_ID'),
            "attribute": attr_record.get('ATTR_CODE'),
            "class": self._get_attribute_class_name(attr_record.get('ATTR_CLASS')),
            "feature": self._get_feature_code_by_id(attr_record.get('FTYPE_ID')),
            "element": self._get_element_code_by_id(attr_record.get('FELEM_CODE')),
            "required": 'Yes' if attr_record.get('FELEM_REQ') == 'Yes' else 'No',
            "internal": 'Yes' if attr_record.get('INTERNAL') == 'Yes' else 'No',
            "default": attr_record.get('DEFAULT_VALUE', '')
        }

        return transformed

    def format_element_json(self, elem_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw CFG_FELEM database record to user-friendly JSON format.

        Args:
            elem_record: Raw database record from CFG_FELEM table

        Returns:
            Transformed JSON dict with user-friendly field names
        """
        if not elem_record:
            return {}

        return elem_record  # Elements are already in good format

    def _get_feature_element_list(self, ftype_id: int) -> List[Dict[str, Any]]:
        """Get elementList array for a feature by querying relationship tables.

        Args:
            ftype_id: Feature type ID

        Returns:
            List of element dictionaries with expressed/compared/derived/display info
        """
        element_list = []

        try:
            # Query CFG_FBOM to get feature-element relationships
            fbom_records = self.get_records('CFG_FBOM', 'FTYPE_ID', ftype_id)

            for fbom in fbom_records:
                elem_code = fbom.get('FELEM_CODE')
                if elem_code:
                    # Query CFG_EFBOM for expression relationships
                    efbom_records = self.get_records('CFG_EFBOM', 'FELEM_CODE', elem_code)
                    expressed = 'Yes' if efbom_records else 'No'

                    # Query CFG_CFBOM for comparison relationships
                    cfbom_records = self.get_records('CFG_CFBOM', 'FELEM_CODE', elem_code)
                    compared = 'Yes' if cfbom_records else 'No'

                    element_list.append({
                        "element": elem_code,
                        "expressed": expressed,
                        "compared": compared,
                        "derived": fbom.get('DERIVED', 'No'),
                        "display": fbom.get('DISPLAY_LEVEL', 'Yes')
                    })

        except Exception:
            # If we can't get element relationships, return empty list
            pass

        return element_list

    def _get_feature_expression_function(self, ftype_code: str) -> str:
        """Get expression function name for a feature."""
        try:
            # Look for expression function based on feature code
            func_name = f"{ftype_code}_EFEAT"
            records = self.get_records('CFG_EFUNC', 'EFUNC_CODE', func_name)
            return func_name if records else ""
        except Exception:
            return ""

    def _get_feature_comparison_function(self, ftype_code: str) -> str:
        """Get comparison function name for a feature."""
        try:
            # Look for comparison function based on feature code
            func_name = f"{ftype_code}_COMP"
            records = self.get_records('CFG_CFUNC', 'CFUNC_CODE', func_name)
            return func_name if records else ""
        except Exception:
            return ""

    def _get_feature_standardize_function(self, ftype_code: str) -> str:
        """Get standardize function name for a feature."""
        try:
            # Most features don't have standardize functions
            return ""
        except Exception:
            return ""

    def _get_feature_class_name(self, fclass_id: int) -> str:
        """Get feature class name by ID."""
        try:
            if fclass_id == 1:
                return "REQUIRED"
            elif fclass_id == 2:
                return "NAME"
            elif fclass_id == 3:
                return "CHARACTERISTIC"
            else:
                record = self.get_record('CFG_FCLASS', 'FCLASS_ID', fclass_id)
                return record.get('FCLASS_CODE', 'UNKNOWN') if record else 'UNKNOWN'
        except Exception:
            return 'UNKNOWN'

    def _get_attribute_class_name(self, attr_class: str) -> str:
        """Get attribute class name."""
        return attr_class or 'ATTRIBUTE'

    def _get_feature_code_by_id(self, ftype_id: int) -> str:
        """Get feature code by ID."""
        try:
            record = self.get_record('CFG_FTYPE', 'FTYPE_ID', ftype_id)
            return record.get('FTYPE_CODE', '') if record else ''
        except Exception:
            return ''

    def _get_element_code_by_id(self, felem_code: str) -> str:
        """Get element code (it's already the code, not an ID)."""
        return felem_code or ''

    def format_list_features_json(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform list of features to include derived field and proper structure.

        Args:
            features: List of raw CFG_FTYPE records

        Returns:
            List of enhanced feature dictionaries
        """
        enhanced_features = []

        for feature in features:
            enhanced = feature.copy()

            # Add derived field calculation
            derived = 'No'  # Default
            try:
                # Check if feature has any derived elements
                ftype_id = feature.get('FTYPE_ID')
                if ftype_id:
                    fbom_records = self.get_records('CFG_FBOM', 'FTYPE_ID', ftype_id)
                    for fbom in fbom_records:
                        if fbom.get('DERIVED') == 'Yes':
                            derived = 'Yes'
                            break
            except Exception:
                pass

            enhanced['derived'] = derived
            enhanced_features.append(enhanced)

        return enhanced_features

    def format_list_comparison_calls_json(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform list of comparison calls to include element and order fields.

        Args:
            calls: List of raw CFG_CCALL records

        Returns:
            List of enhanced comparison call dictionaries
        """
        enhanced_calls = []

        for call in calls:
            enhanced = call.copy()

            # Add missing fields based on relationships
            try:
                # Get element relationships from CFG_CFBOM
                ccall_id = call.get('CCALL_ID')
                if ccall_id:
                    cfbom_records = self.get_records('CFG_CFBOM', 'CCALL_ID', ccall_id)
                    if cfbom_records:
                        # Add element and order information
                        enhanced['element'] = cfbom_records[0].get('FELEM_CODE', '')
                        enhanced['order'] = cfbom_records[0].get('EXEC_ORDER', 1)
                    else:
                        enhanced['element'] = ''
                        enhanced['order'] = 1
            except Exception:
                enhanced['element'] = ''
                enhanced['order'] = 1

            enhanced_calls.append(enhanced)

        return enhanced_calls

    def format_list_distinct_calls_json(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform list of distinct calls to include element and order fields.

        Args:
            calls: List of raw CFG_DCALL records

        Returns:
            List of enhanced distinct call dictionaries
        """
        enhanced_calls = []

        for call in calls:
            enhanced = call.copy()

            # Add missing fields based on relationships
            try:
                # Get element relationships from CFG_DFBOM
                dcall_id = call.get('DCALL_ID')
                if dcall_id:
                    dfbom_records = self.get_records('CFG_DFBOM', 'DCALL_ID', dcall_id)
                    if dfbom_records:
                        # Add element and order information
                        enhanced['element'] = dfbom_records[0].get('FELEM_CODE', '')
                        enhanced['order'] = dfbom_records[0].get('EXEC_ORDER', 1)
                    else:
                        enhanced['element'] = ''
                        enhanced['order'] = 1
            except Exception:
                enhanced['element'] = ''
                enhanced['order'] = 1

            enhanced_calls.append(enhanced)

        return enhanced_calls

    def format_list_expression_calls_json(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform list of expression calls to include missing relationship fields.

        Args:
            calls: List of raw CFG_ECALL records

        Returns:
            List of enhanced expression call dictionaries
        """
        enhanced_calls = []

        for call in calls:
            enhanced = call.copy()

            # Add missing fields based on relationships
            try:
                # Get element and feature relationships from CFG_EFBOM
                ecall_id = call.get('ECALL_ID')
                if ecall_id:
                    efbom_records = self.get_records('CFG_EFBOM', 'ECALL_ID', ecall_id)
                    if efbom_records:
                        # Add relationship information
                        efbom = efbom_records[0]
                        enhanced['element'] = efbom.get('FELEM_CODE', '')
                        enhanced['order'] = efbom.get('EXEC_ORDER', 1)
                        enhanced['required'] = efbom.get('FELEM_REQ', 'No')

                        # Get feature information
                        ftype_id = efbom.get('FTYPE_ID')
                        if ftype_id:
                            feature_record = self.get_record('CFG_FTYPE', 'FTYPE_ID', ftype_id)
                            if feature_record:
                                enhanced['feature'] = feature_record.get('FTYPE_CODE', '')
                                enhanced['featureLink'] = feature_record.get('FTYPE_CODE', '')
                            else:
                                enhanced['feature'] = ''
                                enhanced['featureLink'] = ''
                    else:
                        enhanced['element'] = ''
                        enhanced['feature'] = ''
                        enhanced['featureLink'] = ''
                        enhanced['order'] = 1
                        enhanced['required'] = 'No'
            except Exception:
                enhanced['element'] = ''
                enhanced['feature'] = ''
                enhanced['featureLink'] = ''
                enhanced['order'] = 1
                enhanced['required'] = 'No'

            enhanced_calls.append(enhanced)

        return enhanced_calls

    def format_list_system_parameters_json(self, params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform list of system parameters to include missing parameters.

        Args:
            params: List of raw CFG_SPARM records

        Returns:
            List of enhanced system parameter dictionaries
        """
        enhanced_params = list(params)

        # Check if relationshipsBreakMatches is missing and add it
        param_names = {p.get('SPARM_CODE', '') for p in enhanced_params}

        if 'relationshipsBreakMatches' not in param_names:
            # Add the missing parameter with default value
            enhanced_params.append({
                'SPARM_ID': max([p.get('SPARM_ID', 0) for p in enhanced_params] or [0]) + 1,
                'SPARM_CODE': 'relationshipsBreakMatches',
                'SPARM_VALUE': 'No',
                'SPARM_DESC': 'Whether relationship matches should break entity resolution'
            })

        return enhanced_params