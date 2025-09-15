"""Function management operations (comparison, expression, standardize, distinct)."""

from typing import Any, Dict, List, Optional
from .base_manager import BaseConfigurationManager


class FunctionManager(BaseConfigurationManager):
    """Manager for function configuration operations."""

    def get_comparison_functions(self) -> List[Dict[str, Any]]:
        """Get all comparison functions."""
        return self.get_record_list('CFG_CFUNC')

    def get_expression_functions(self) -> List[Dict[str, Any]]:
        """Get all expression functions."""
        return self.get_record_list('CFG_EFUNC')

    def get_standardize_functions(self) -> List[Dict[str, Any]]:
        """Get all standardize functions."""
        return self.get_record_list('CFG_SFUNC')

    def get_distinct_functions(self) -> List[Dict[str, Any]]:
        """Get all distinct functions."""
        return self.get_record_list('CFG_DFUNC')

    def get_distinct_calls(self) -> List[Dict[str, Any]]:
        """Get all distinct function calls."""
        return self.get_record_list('CFG_DCALL')

    def get_distinct_call(self, call_id: int) -> Optional[Dict[str, Any]]:
        """Get a distinct function call by ID."""
        return self.get_record('CFG_DCALL', 'DCALL_ID', call_id)

    def delete_distinct_call(self, call_id: int) -> bool:
        """Delete a distinct function call."""
        success = self.delete_record('CFG_DCALL', 'DCALL_ID', call_id)
        if success:
            self.config_updated = True
        return success

    def format_comparison_function_json(self, func_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format comparison function record to JSON."""
        if not func_record:
            return {}

        return {
            'id': func_record.get('CFUNC_ID'),
            'function': func_record.get('CFUNC_CODE', ''),
            'description': func_record.get('CFUNC_DESC', ''),
            'version': func_record.get('VERSION', 1)
        }

    def format_expression_function_json(self, func_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format expression function record to JSON."""
        if not func_record:
            return {}

        return {
            'id': func_record.get('EFUNC_ID'),
            'function': func_record.get('EFUNC_CODE', ''),
            'description': func_record.get('EFUNC_DESC', ''),
            'version': func_record.get('VERSION', 1)
        }

    def format_standardize_function_json(self, func_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format standardize function record to JSON."""
        if not func_record:
            return {}

        return {
            'id': func_record.get('SFUNC_ID'),
            'function': func_record.get('SFUNC_CODE', ''),
            'description': func_record.get('SFUNC_DESC', ''),
            'version': func_record.get('VERSION', 1)
        }

    def format_distinct_function_json(self, func_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format distinct function record to JSON."""
        if not func_record:
            return {}

        return {
            'id': func_record.get('DFUNC_ID'),
            'function': func_record.get('DFUNC_CODE', ''),
            'description': func_record.get('DFUNC_DESC', ''),
            'version': func_record.get('VERSION', 1)
        }

    def format_distinct_call_json(self, call_record: Dict[str, Any]) -> Dict[str, Any]:
        """Format distinct call record to JSON."""
        if not call_record:
            return {}

        return {
            'id': call_record.get('DCALL_ID'),
            'function': call_record.get('DFUNC_CODE', ''),
            'execOrder': call_record.get('EXEC_ORDER', 1)
        }