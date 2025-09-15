"""Comprehensive tests for all 20 LIST commands per CLAUDE.md requirements.

This test suite implements all 5 CLAUDE.md requirements for every list command:
1. Help functionality
2. Functionality (command execution)
3. Parameters (argument parsing)
4. Data retrieval (correct tables)
5. Display (formatting and output)
"""

import pytest
import sys
import os
from typing import List, Dict, Any, Optional

# Add the sz_tools directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sz_tools'))

from tests.test_framework_comprehensive import ListCommandTestBase
from _config_display import ConfigDisplayFormatter
from configtool_main import ConfigToolShell


# =========================================================================
# LIST COMMANDS COMPREHENSIVE TESTS
# =========================================================================

class TestListAttributes(ListCommandTestBase):
    """Comprehensive tests for listAttributes command."""

    def get_command_name(self) -> str:
        return "listAttributes"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_ATTR"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'ATTR_ID': 1, 'ATTR_CODE': 'PERSON_NAME', 'ATTR_CLASS': 'NAME', 'FTYPE_CODE': 'NAME'},
            {'ATTR_ID': 2, 'ATTR_CODE': 'DATE_OF_BIRTH', 'ATTR_CLASS': 'DOB', 'FTYPE_CODE': 'DOB'},
            {'ATTR_ID': 3, 'ATTR_CODE': 'ADDR_FULL', 'ATTR_CLASS': 'ADDRESS', 'FTYPE_CODE': 'ADDRESS'}
        ]


class TestListBehaviorOverrides(ListCommandTestBase):
    """Comprehensive tests for listBehaviorOverrides command."""

    def get_command_name(self) -> str:
        return "listBehaviorOverrides"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_BFRULE"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'BFRULE_ID': 1, 'FTYPE_CODE': 'NAME', 'BEHAVIOR': 'FM', 'EXEC_ORDER': 1},
            {'BFRULE_ID': 2, 'FTYPE_CODE': 'DOB', 'BEHAVIOR': 'NONE', 'EXEC_ORDER': 2},
            {'BFRULE_ID': 3, 'FTYPE_CODE': 'ADDRESS', 'BEHAVIOR': 'F1', 'EXEC_ORDER': 3}
        ]


class TestListComparisonCalls(ListCommandTestBase):
    """Comprehensive tests for listComparisonCalls command."""

    def get_command_name(self) -> str:
        return "listComparisonCalls"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_CFCALL"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'CFCALL_ID': 1, 'FTYPE_CODE': 'NAME', 'CFUNC_CODE': 'NAME_COMP', 'EXEC_ORDER': 1},
            {'CFCALL_ID': 2, 'FTYPE_CODE': 'DOB', 'CFUNC_CODE': 'DOB_COMP', 'EXEC_ORDER': 2},
            {'CFCALL_ID': 3, 'FTYPE_CODE': 'ADDRESS', 'CFUNC_CODE': 'ADDR_COMP', 'EXEC_ORDER': 3}
        ]


class TestListComparisonFunctions(ListCommandTestBase):
    """Comprehensive tests for listComparisonFunctions command."""

    def get_command_name(self) -> str:
        return "listComparisonFunctions"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_CFUNC"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'CFUNC_ID': 1, 'CFUNC_CODE': 'NAME_COMP', 'CFUNC_DESC': 'Name comparison'},
            {'CFUNC_ID': 2, 'CFUNC_CODE': 'DOB_COMP', 'CFUNC_DESC': 'Date of birth comparison'},
            {'CFUNC_ID': 3, 'CFUNC_CODE': 'ADDR_COMP', 'CFUNC_DESC': 'Address comparison'}
        ]


class TestListComparisonThresholds(ListCommandTestBase):
    """Comprehensive tests for listComparisonThresholds command."""

    def get_command_name(self) -> str:
        return "listComparisonThresholds"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_CFRTN"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'CFRTN_ID': 1, 'CFUNC_CODE': 'NAME_COMP', 'FTYPE_CODE': 'NAME', 'CFUNC_RTNVAL': 'SAME'},
            {'CFRTN_ID': 2, 'CFUNC_CODE': 'DOB_COMP', 'FTYPE_CODE': 'DOB', 'CFUNC_RTNVAL': 'CLOSE'},
            {'CFRTN_ID': 3, 'CFUNC_CODE': 'ADDR_COMP', 'FTYPE_CODE': 'ADDRESS', 'CFUNC_RTNVAL': 'CLOSE'}
        ]


class TestListDataSources(ListCommandTestBase):
    """Comprehensive tests for listDataSources command."""

    def get_command_name(self) -> str:
        return "listDataSources"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_DSRC"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'DSRC_ID': 1, 'DSRC_CODE': 'CUSTOMERS', 'DSRC_DESC': 'Customer data'},
            {'DSRC_ID': 2, 'DSRC_CODE': 'VENDORS', 'DSRC_DESC': 'Vendor data'},
            {'DSRC_ID': 3, 'DSRC_CODE': 'WATCHLIST', 'DSRC_DESC': 'Watchlist data'}
        ]


class TestListDistinctCalls(ListCommandTestBase):
    """Comprehensive tests for listDistinctCalls command."""

    def get_command_name(self) -> str:
        return "listDistinctCalls"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_DFCALL"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'DFCALL_ID': 1, 'FTYPE_CODE': 'NAME', 'DFUNC_CODE': 'NAME_DISTINCT', 'EXEC_ORDER': 1},
            {'DFCALL_ID': 2, 'FTYPE_CODE': 'DOB', 'DFUNC_CODE': 'DOB_DISTINCT', 'EXEC_ORDER': 2},
            {'DFCALL_ID': 3, 'FTYPE_CODE': 'ADDRESS', 'DFUNC_CODE': 'ADDR_DISTINCT', 'EXEC_ORDER': 3}
        ]


class TestListDistinctFunctions(ListCommandTestBase):
    """Comprehensive tests for listDistinctFunctions command."""

    def get_command_name(self) -> str:
        return "listDistinctFunctions"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_DFUNC"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'DFUNC_ID': 1, 'DFUNC_CODE': 'NAME_DISTINCT', 'DFUNC_DESC': 'Name distinct function'},
            {'DFUNC_ID': 2, 'DFUNC_CODE': 'DOB_DISTINCT', 'DFUNC_DESC': 'DOB distinct function'},
            {'DFUNC_ID': 3, 'DFUNC_CODE': 'ADDR_DISTINCT', 'DFUNC_DESC': 'Address distinct function'}
        ]


class TestListElements(ListCommandTestBase):
    """Comprehensive tests for listElements command."""

    def get_command_name(self) -> str:
        return "listElements"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_FELEM"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'FELEM_ID': 1, 'FELEM_CODE': 'NAME_HASH', 'FELEM_DESC': 'Name hash element'},
            {'FELEM_ID': 2, 'FELEM_CODE': 'DOB_HASH', 'FELEM_DESC': 'DOB hash element'},
            {'FELEM_ID': 3, 'FELEM_CODE': 'ADDR_HASH', 'FELEM_DESC': 'Address hash element'}
        ]


class TestListExpressionCalls(ListCommandTestBase):
    """Comprehensive tests for listExpressionCalls command."""

    def get_command_name(self) -> str:
        return "listExpressionCalls"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_EFCALL"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'EFCALL_ID': 1, 'FTYPE_CODE': 'NAME', 'EFUNC_CODE': 'NAME_EXPR', 'EXEC_ORDER': 1},
            {'EFCALL_ID': 2, 'FTYPE_CODE': 'DOB', 'EFUNC_CODE': 'DOB_EXPR', 'EXEC_ORDER': 2},
            {'EFCALL_ID': 3, 'FTYPE_CODE': 'ADDRESS', 'EFUNC_CODE': 'ADDR_EXPR', 'EXEC_ORDER': 3}
        ]


class TestListExpressionFunctions(ListCommandTestBase):
    """Comprehensive tests for listExpressionFunctions command."""

    def get_command_name(self) -> str:
        return "listExpressionFunctions"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_EFUNC"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'EFUNC_ID': 1, 'EFUNC_CODE': 'NAME_EXPR', 'EFUNC_DESC': 'Name expression function'},
            {'EFUNC_ID': 2, 'EFUNC_CODE': 'DOB_EXPR', 'EFUNC_DESC': 'DOB expression function'},
            {'EFUNC_ID': 3, 'EFUNC_CODE': 'ADDR_EXPR', 'EFUNC_DESC': 'Address expression function'}
        ]


class TestListFeatures(ListCommandTestBase):
    """Comprehensive tests for listFeatures command."""

    def get_command_name(self) -> str:
        return "listFeatures"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_FBOM"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'FTYPE_ID': 1, 'FTYPE_CODE': 'NAME', 'FTYPE_DESC': 'Name feature'},
            {'FTYPE_ID': 2, 'FTYPE_CODE': 'DOB', 'FTYPE_DESC': 'Date of birth feature'},
            {'FTYPE_ID': 3, 'FTYPE_CODE': 'ADDRESS', 'FTYPE_DESC': 'Address feature'}
        ]


class TestListFragments(ListCommandTestBase):
    """Comprehensive tests for listFragments command."""

    def get_command_name(self) -> str:
        return "listFragments"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_EFCALL"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'ERFRAG_ID': 1, 'ERFRAG_CODE': 'SAME_NAME', 'ERFRAG_DESC': 'Same name fragment'},
            {'ERFRAG_ID': 2, 'ERFRAG_CODE': 'CLOSE_DOB', 'ERFRAG_DESC': 'Close DOB fragment'},
            {'ERFRAG_ID': 3, 'ERFRAG_CODE': 'SAME_ADDR', 'ERFRAG_DESC': 'Same address fragment'}
        ]


class TestListGenericPlans(ListCommandTestBase):
    """Comprehensive tests for listGenericPlans command."""

    def get_command_name(self) -> str:
        return "listGenericPlans"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_GBOM"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'GBOM_ID': 1, 'FTYPE_CODE': 'NAME', 'BEHAVIOR': 'FM', 'FELEM_CODE': 'NAME_HASH'},
            {'GBOM_ID': 2, 'FTYPE_CODE': 'DOB', 'BEHAVIOR': 'FM', 'FELEM_CODE': 'DOB_HASH'},
            {'GBOM_ID': 3, 'FTYPE_CODE': 'ADDRESS', 'BEHAVIOR': 'A1', 'FELEM_CODE': 'ADDR_HASH'}
        ]


class TestListGenericThresholds(ListCommandTestBase):
    """Comprehensive tests for listGenericThresholds command."""

    def get_command_name(self) -> str:
        return "listGenericThresholds"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_GENERIC_THRESHOLD"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'GPLAN_ID': 1, 'BEHAVIOR': 'FM', 'FTYPE_ID': 1, 'CANDIDATE_CAP': 10, 'SCORING_CAP': 10},
            {'GPLAN_ID': 2, 'BEHAVIOR': 'F1', 'FTYPE_ID': 2, 'CANDIDATE_CAP': 5, 'SCORING_CAP': 5},
            {'GPLAN_ID': 3, 'BEHAVIOR': 'A1', 'FTYPE_ID': 3, 'CANDIDATE_CAP': 15, 'SCORING_CAP': 15}
        ]


class TestListReferenceCodes(ListCommandTestBase):
    """Comprehensive tests for listReferenceCodes command."""

    def get_command_name(self) -> str:
        return "listReferenceCodes"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_RCLASS"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'RCLASS_ID': 1, 'RCLASS_CODE': 'PERSON', 'RCLASS_DESC': 'Person reference class'},
            {'RCLASS_ID': 2, 'RCLASS_CODE': 'ORGANIZATION', 'RCLASS_DESC': 'Organization reference class'},
            {'RCLASS_ID': 3, 'RCLASS_CODE': 'VEHICLE', 'RCLASS_DESC': 'Vehicle reference class'}
        ]


class TestListRules(ListCommandTestBase):
    """Comprehensive tests for listRules command."""

    def get_command_name(self) -> str:
        return "listRules"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_ERRULE"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'ERRULE_ID': 100, 'ERRULE_CODE': 'SAME_A1', 'RESOLVE': 'Yes', 'RELATE': 'No'},
            {'ERRULE_ID': 108, 'ERRULE_CODE': 'SF1_SNAME_CFF_CSTAB', 'RESOLVE': 'Yes', 'RELATE': 'No'},
            {'ERRULE_ID': 115, 'ERRULE_CODE': 'SAME_A1E_EXACT', 'RESOLVE': 'Yes', 'RELATE': 'No'}
        ]


class TestListStandardizeCalls(ListCommandTestBase):
    """Comprehensive tests for listStandardizeCalls command."""

    def get_command_name(self) -> str:
        return "listStandardizeCalls"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_SFCALL"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'SFCALL_ID': 1, 'FTYPE_CODE': 'NAME', 'SFUNC_CODE': 'NAME_STD', 'EXEC_ORDER': 1},
            {'SFCALL_ID': 2, 'FTYPE_CODE': 'DOB', 'SFUNC_CODE': 'DOB_STD', 'EXEC_ORDER': 2},
            {'SFCALL_ID': 3, 'FTYPE_CODE': 'ADDRESS', 'SFUNC_CODE': 'ADDR_STD', 'EXEC_ORDER': 3}
        ]


class TestListStandardizeFunctions(ListCommandTestBase):
    """Comprehensive tests for listStandardizeFunctions command."""

    def get_command_name(self) -> str:
        return "listStandardizeFunctions"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_SFUNC"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'SFUNC_ID': 1, 'SFUNC_CODE': 'NAME_STD', 'SFUNC_DESC': 'Name standardization'},
            {'SFUNC_ID': 2, 'SFUNC_CODE': 'DOB_STD', 'SFUNC_DESC': 'DOB standardization'},
            {'SFUNC_ID': 3, 'SFUNC_CODE': 'ADDR_STD', 'SFUNC_DESC': 'Address standardization'}
        ]


class TestListSystemParameters(ListCommandTestBase):
    """Comprehensive tests for listSystemParameters command."""

    def get_command_name(self) -> str:
        return "listSystemParameters"

    def get_expected_table_name(self) -> Optional[str]:
        return "CFG_RTYPE"

    def get_sample_test_data(self) -> List[Dict[str, Any]]:
        return [
            {'VAR_ID': 1, 'VAR_CODE': 'CONFIG_VERSION', 'VAR_VALUE': '1.0'},
            {'VAR_ID': 2, 'VAR_CODE': 'MAX_THREADS', 'VAR_VALUE': '8'},
            {'VAR_ID': 3, 'VAR_CODE': 'DEBUG_LEVEL', 'VAR_VALUE': '0'}
        ]


# =========================================================================
# INTEGRATION TESTS FOR ALL LIST COMMANDS
# =========================================================================

class TestAllListCommandsIntegration:
    """Integration tests that verify all list commands work together."""

    def setup_method(self):
        """Set up test fixtures."""
        from unittest.mock import Mock

        self.mock_config_manager = Mock()
        self.mock_config_manager.initialize_senzing.return_value = True
        self.display_formatter = ConfigDisplayFormatter()
        self.shell = ConfigToolShell(
            self.mock_config_manager,
            self.display_formatter,
            hist_disable=True
        )

    def test_all_list_commands_exist(self):
        """Test that all 20 list commands exist."""
        expected_commands = [
            'listAttributes', 'listBehaviorOverrides', 'listComparisonCalls',
            'listComparisonFunctions', 'listComparisonThresholds', 'listDataSources',
            'listDistinctCalls', 'listDistinctFunctions', 'listElements',
            'listExpressionCalls', 'listExpressionFunctions', 'listFeatures',
            'listFragments', 'listGenericPlans', 'listGenericThresholds',
            'listReferenceCodes', 'listRules', 'listStandardizeCalls',
            'listStandardizeFunctions', 'listSystemParameters'
        ]

        for cmd in expected_commands:
            assert hasattr(self.shell, f'do_{cmd}'), f"Missing command: {cmd}"
            method = getattr(self.shell, f'do_{cmd}')
            assert callable(method), f"Command {cmd} is not callable"

    def test_all_list_commands_have_help(self):
        """Test that all list commands have help documentation."""
        list_commands = [method[3:] for method in dir(self.shell)
                        if method.startswith('do_list') and callable(getattr(self.shell, method))]

        for cmd in list_commands:
            method = getattr(self.shell, f'do_{cmd}')
            assert method.__doc__ is not None, f"Command {cmd} missing docstring"
            assert len(method.__doc__.strip()) > 0, f"Command {cmd} has empty docstring"


if __name__ == "__main__":
    # Run comprehensive tests for all list commands
    pytest.main([__file__, "-v", "--tb=short"])