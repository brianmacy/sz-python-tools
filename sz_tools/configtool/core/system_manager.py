"""System and configuration management operations."""

from typing import Any, Dict, List, Optional
from .base_manager import BaseConfigurationManager


class SystemManager(BaseConfigurationManager):
    """Manager for system configuration operations."""

    def get_thresholds(self) -> List[Dict[str, Any]]:
        """Get all thresholds."""
        return self.get_record_list('CFG_THRESH')

    def get_threshold(self, threshold_id: int) -> Optional[Dict[str, Any]]:
        """Get a threshold by ID."""
        return self.get_record('CFG_THRESH', 'THRESH_ID', threshold_id)

    def set_threshold(self, threshold_type: str, value: float) -> bool:
        """Set a threshold value."""
        # Implementation would update the specific threshold
        # For now, return True as placeholder
        self.config_updated = True
        return True

    def get_scoring_sets(self) -> List[Dict[str, Any]]:
        """Get all scoring sets."""
        return self.get_record_list('CFG_SSET')

    def get_scoring_set(self, scoring_set_id: int) -> Optional[Dict[str, Any]]:
        """Get a scoring set by ID."""
        return self.get_record('CFG_SSET', 'SSET_ID', scoring_set_id)

    def add_scoring_set(self, scoring_set_config: Dict[str, Any]) -> bool:
        """Add a scoring set."""
        next_id = self.get_next_id('CFG_SSET', 'SSET_ID')
        scoring_set_config['SSET_ID'] = next_id
        success = self.add_record('CFG_SSET', scoring_set_config)
        if success:
            self.config_updated = True
        return success

    def delete_scoring_set(self, scoring_set_id: int) -> bool:
        """Delete a scoring set."""
        success = self.delete_record('CFG_SSET', 'SSET_ID', scoring_set_id)
        if success:
            self.config_updated = True
        return success

    def get_fragment_types(self) -> List[Dict[str, Any]]:
        """Get all fragment types."""
        return self.get_record_list('CFG_FRAGTYPE')

    def get_fragment_type(self, fragment_type_id: int) -> Optional[Dict[str, Any]]:
        """Get a fragment type by ID."""
        return self.get_record('CFG_FRAGTYPE', 'FRAGTYPE_ID', fragment_type_id)

    def get_match_levels(self) -> List[Dict[str, Any]]:
        """Get all match levels."""
        return self.get_record_list('CFG_MLEVEL')

    def get_match_level(self, match_level_id: int) -> Optional[Dict[str, Any]]:
        """Get a match level by ID."""
        return self.get_record('CFG_MLEVEL', 'MLEVEL_ID', match_level_id)

    def set_match_level(self, level_config: Dict[str, Any]) -> bool:
        """Set match level configuration."""
        # Implementation would update the specific match level
        # For now, return True as placeholder
        self.config_updated = True
        return True

    def get_compatibility_version(self) -> Optional[str]:
        """Get compatibility version."""
        config_data = self.get_config_data()
        if config_data and 'G2_CONFIG' in config_data:
            version_info = config_data['G2_CONFIG'].get('CFG_VERSION', [])
            if version_info and isinstance(version_info, list) and len(version_info) > 0:
                return version_info[0].get('VERSION', None)
        return None

    def update_compatibility_version(self, version: str) -> bool:
        """Update compatibility version."""
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return False

        # Update or create version record
        if 'CFG_VERSION' not in config_data['G2_CONFIG']:
            config_data['G2_CONFIG']['CFG_VERSION'] = []

        version_records = config_data['G2_CONFIG']['CFG_VERSION']
        if version_records:
            version_records[0]['VERSION'] = version
        else:
            version_records.append({
                'VERSION_ID': 1,
                'VERSION': version,
                'BUILD_DATE': '',
                'BUILD_NUMBER': '1'
            })

        success = self.update_config_data(config_data)
        if success:
            self.config_updated = True
        return success

    def verify_compatibility_version(self, expected_version: str) -> bool:
        """Verify compatibility version."""
        current_version = self.get_compatibility_version()
        return current_version == expected_version

    def touch_config(self) -> bool:
        """Touch/update configuration timestamp."""
        # Mark configuration as updated
        self.config_updated = True
        return True

    def format_threshold_json(self, threshold_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format threshold record to JSON."""
        if not threshold_record:
            return {}

        return {
            'id': threshold_record.get('THRESH_ID'),
            'threshold': threshold_record.get('THRESH_CODE', ''),
            'value': threshold_record.get('THRESH_VALUE', 0)
        }

    def format_scoring_set_json(self, scoring_set_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format scoring set record to JSON."""
        if not scoring_set_record:
            return {}

        return {
            'id': scoring_set_record.get('SSET_ID'),
            'scoringSet': scoring_set_record.get('SSET_CODE', ''),
            'description': scoring_set_record.get('SSET_DESC', '')
        }

    def format_fragment_type_json(self, fragment_type_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format fragment type record to JSON."""
        if not fragment_type_record:
            return {}

        return {
            'id': fragment_type_record.get('FRAGTYPE_ID'),
            'fragmentType': fragment_type_record.get('FRAGTYPE_CODE', ''),
            'description': fragment_type_record.get('FRAGTYPE_DESC', '')
        }

    def format_match_level_json(self, match_level_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format match level record to JSON."""
        if not match_level_record:
            return {}

        return {
            'id': match_level_record.get('MLEVEL_ID'),
            'matchLevel': match_level_record.get('MLEVEL_CODE', ''),
            'description': match_level_record.get('MLEVEL_DESC', '')
        }