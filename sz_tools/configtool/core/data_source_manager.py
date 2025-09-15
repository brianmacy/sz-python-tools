"""Data source management operations."""

from typing import Any, Dict, List, Optional
from .base_manager import BaseConfigurationManager


class DataSourceManager(BaseConfigurationManager):
    """Manager for data source configuration operations."""

    def get_data_sources(self) -> Optional[List[Dict[str, Any]]]:
        """Get all data sources from the current configuration.

        Returns:
            List of data source dictionaries if successful, None if configuration unavailable
        """
        if not self.get_config_data():
            return None
        return self.get_record_list('CFG_DSRC')

    def add_data_source(self, data_source_code: str) -> bool:
        """Add a new data source to the configuration.

        Args:
            data_source_code: Code for the new data source

        Returns:
            True if successful, False otherwise
        """
        # Check if data source already exists
        existing = self.get_record('CFG_DSRC', 'DSRC_CODE', data_source_code)
        if existing:
            return False  # Already exists

        # Get next available ID
        next_id = self.get_next_id('CFG_DSRC', 'DSRC_ID')

        # Create new data source record
        new_record = {
            'DSRC_ID': next_id,
            'DSRC_CODE': data_source_code,
            'DSRC_DESC': f'Data source {data_source_code}'
        }

        # Add the record
        success = self.add_record('CFG_DSRC', new_record)

        if success:
            self.config_updated = True

        return success

    def delete_data_source(self, data_source_code: str) -> bool:
        """Delete a data source from the configuration.

        Args:
            data_source_code: Code of the data source to delete

        Returns:
            True if successful, False otherwise
        """
        # Check if data source exists
        existing = self.get_record('CFG_DSRC', 'DSRC_CODE', data_source_code)
        if not existing:
            return False  # Doesn't exist

        # Delete the record
        success = self.delete_record('CFG_DSRC', 'DSRC_CODE', data_source_code)

        if success:
            self.config_updated = True

        return success

    def get_data_source_by_code(self, data_source_code: str) -> Optional[Dict[str, Any]]:
        """Get a data source by its code.

        Args:
            data_source_code: Data source code to search for

        Returns:
            Data source dictionary if found, None otherwise
        """
        return self.get_record('CFG_DSRC', 'DSRC_CODE', data_source_code)

    def get_data_source_by_id(self, data_source_id: int) -> Optional[Dict[str, Any]]:
        """Get a data source by its ID.

        Args:
            data_source_id: Data source ID to search for

        Returns:
            Data source dictionary if found, None otherwise
        """
        return self.get_record('CFG_DSRC', 'DSRC_ID', data_source_id)

    def update_data_source(self, data_source_code: str, updates: Dict[str, Any]) -> bool:
        """Update a data source's properties.

        Args:
            data_source_code: Data source code to update
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        # Get existing record
        existing = self.get_record('CFG_DSRC', 'DSRC_CODE', data_source_code)
        if not existing:
            return False

        # Update the record
        updated_record = existing.copy()
        updated_record.update(updates)

        # Update in configuration
        success = self.update_record('CFG_DSRC', 'DSRC_CODE', data_source_code, updated_record)

        if success:
            self.config_updated = True

        return success