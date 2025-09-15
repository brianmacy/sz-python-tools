"""Rules and validation management operations."""

from typing import Any, Dict, List, Optional
from .base_manager import BaseConfigurationManager


class RulesManager(BaseConfigurationManager):
    """Manager for rules and validation configuration operations."""

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all rules."""
        return self.get_record_list('CFG_RULE')

    def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        """Get a rule by ID."""
        return self.get_record('CFG_RULE', 'RULE_ID', rule_id)

    def get_generic_plans(self) -> List[Dict[str, Any]]:
        """Get all generic plans."""
        return self.get_record_list('CFG_GPLAN')

    def get_generic_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get a generic plan by ID."""
        return self.get_record('CFG_GPLAN', 'GPLAN_ID', plan_id)

    def add_generic_plan(self, plan_config: Dict[str, Any]) -> bool:
        """Add a generic plan."""
        next_id = self.get_next_id('CFG_GPLAN', 'GPLAN_ID')
        plan_config['GPLAN_ID'] = next_id
        success = self.add_record('CFG_GPLAN', plan_config)
        if success:
            self.config_updated = True
        return success

    def delete_generic_plan(self, plan_id: int) -> bool:
        """Delete a generic plan."""
        success = self.delete_record('CFG_GPLAN', 'GPLAN_ID', plan_id)
        if success:
            self.config_updated = True
        return success

    def get_behavior_overrides(self) -> List[Dict[str, Any]]:
        """Get all behavior overrides."""
        return self.get_record_list('CFG_BOVER')

    def get_behavior_override(self, override_id: int) -> Optional[Dict[str, Any]]:
        """Get a behavior override by ID."""
        return self.get_record('CFG_BOVER', 'BOVER_ID', override_id)

    def add_behavior_override(self, override_config: Dict[str, Any]) -> bool:
        """Add a behavior override."""
        next_id = self.get_next_id('CFG_BOVER', 'BOVER_ID')
        override_config['BOVER_ID'] = next_id
        success = self.add_record('CFG_BOVER', override_config)
        if success:
            self.config_updated = True
        return success

    def delete_behavior_override(self, override_id: int) -> bool:
        """Delete a behavior override."""
        success = self.delete_record('CFG_BOVER', 'BOVER_ID', override_id)
        if success:
            self.config_updated = True
        return success

    def get_rule_types(self) -> List[Dict[str, Any]]:
        """Get all rule types."""
        return self.get_record_list('CFG_RTYPE')

    def get_rule_type(self, rule_type_id: int) -> Optional[Dict[str, Any]]:
        """Get a rule type by ID."""
        return self.get_record('CFG_RTYPE', 'RTYPE_ID', rule_type_id)

    def validate_configuration(self, validation_type: str = "full") -> Dict[str, Any]:
        """Validate the current configuration."""
        # Basic validation implementation
        errors = []
        warnings = []

        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            errors.append("No configuration data available")
            return {'valid': False, 'errors': errors, 'warnings': warnings}

        # Check for required data sources
        data_sources = self.get_record_list('CFG_DSRC')
        if not data_sources:
            warnings.append("No data sources configured")

        # Check for required features
        features = self.get_record_list('CFG_FTYPE')
        if not features:
            warnings.append("No features configured")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def format_rule_json(self, rule_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format rule record to JSON."""
        if not rule_record:
            return {}

        return {
            'id': rule_record.get('RULE_ID'),
            'rule': rule_record.get('RULE_CODE', ''),
            'description': rule_record.get('RULE_DESC', ''),
            'disclosed': rule_record.get('IS_DISCLOSED', 'No')
        }

    def format_generic_plan_json(self, plan_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format generic plan record to JSON."""
        if not plan_record:
            return {}

        return {
            'id': plan_record.get('GPLAN_ID'),
            'feature': plan_record.get('FTYPE_CODE', ''),
            'description': plan_record.get('GPLAN_DESC', '')
        }

    def format_behavior_override_json(self, override_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format behavior override record to JSON."""
        if not override_record:
            return {}

        return {
            'id': override_record.get('BOVER_ID'),
            'feature': override_record.get('FTYPE_CODE', ''),
            'behavior': override_record.get('BEHAVIOR', ''),
            'value': override_record.get('OVERRIDE_VALUE', '')
        }

    def format_rule_type_json(self, rule_type_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format rule type record to JSON."""
        if not rule_type_record:
            return {}

        return {
            'id': rule_type_record.get('RTYPE_ID'),
            'ruleType': rule_type_record.get('RTYPE_CODE', ''),
            'description': rule_type_record.get('RTYPE_DESC', '')
        }