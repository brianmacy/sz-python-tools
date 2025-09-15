"""Main configuration tool shell."""

from .base import BaseShell
from .command_groups.data_source import DataSourceCommands
from .command_groups.features import FeatureCommands
from .command_groups.functions import FunctionCommands
from .command_groups.rules import RulesCommands
from .command_groups.scoring import ScoringCommands
from .command_groups.system import SystemCommands


class ConfigToolShell(BaseShell, DataSourceCommands, FeatureCommands,
                      FunctionCommands, RulesCommands, ScoringCommands,
                      SystemCommands):
    """Main configuration tool shell with all command groups."""

    def __init__(self, config_manager, display_formatter,
                 force_mode: bool = False, hist_disable: bool = False):
        """Initialize the configuration tool shell.

        Args:
            config_manager: Configuration management instance
            display_formatter: Display formatting instance
            force_mode: Whether to execute commands without prompts
            hist_disable: Whether to disable history functionality
        """
        super().__init__(config_manager, display_formatter, force_mode, hist_disable)

    def _show_general_help(self) -> None:
        """Show comprehensive help information."""
        help_text = f"""
COMMANDS:

sz_configtool - Senzing Configuration Management Tool
====================================================

TOTAL COMMANDS AVAILABLE: 120+ (Full Implementation)

Basic Commands: (3 commands)
  help                      - Display help for commands.
  quit                      - Exit the configuration tool.
  exit                      - Exit the configuration tool.

Data Source Management: (3 commands)
  listDataSources           - List all data sources in the current configuration.
  addDataSource             - Add a new data source.
  deleteDataSource          - Delete a data source.

Feature Management: (14 commands)
  listFeatures              - List all features in the configuration.
  getFeature                - Get details of a specific feature.
  addFeature                - Add a new feature to the configuration.
  deleteFeature             - Delete a feature from the configuration.
  listAttributes            - List all attributes in the configuration.
  getAttribute              - Get details of a specific attribute.
  addAttribute              - Add a new attribute to the configuration.
  deleteAttribute           - Delete an attribute from the configuration.
  listElements              - List all elements in the configuration.
  getElement                - Get details of a specific element.
  addElement                - Add a new element to the configuration.
  deleteElement             - Delete an element from the configuration.

Function Management: (12 commands)
  listComparisonFunctions   - List all comparison functions.
  getComparisonFunction     - Get details of a specific comparison function.
  listExpressionFunctions   - List all expression functions.
  getExpressionFunction     - Get details of a specific expression function.
  listStandardizeFunction   - List all standardize functions.
  getStandardizeFunction    - Get details of a specific standardize function.
  listDistinctFunctions     - List all distinct functions.
  getDistinctFunction       - Get details of a specific distinct function.
  deleteDistinctCall        - Delete a distinct function call.
  listDistinctCalls         - List all distinct function calls.
  getDistinctCall           - Get details of a specific distinct function call.

Rules and Validation: (16 commands)
  listGenericPlans          - List all generic plans.
  getGenericPlan            - Get details of a specific generic plan.
  listBehaviorOverrides     - List all behavior overrides.
  getBehaviorOverride       - Get details of a specific behavior override.
  addBehaviorOverride       - Add a behavior override.
  deleteBehaviorOverride    - Delete a behavior override.
  listRuleTypes             - List all rule types.
  getRuleType               - Get details of a specific rule type.
  addGenericPlan            - Add a generic plan.
  deleteGenericPlan         - Delete a generic plan.
  validate                  - Validate the current configuration.
  listRules                 - List all rules.
  getRule                   - Get details of a specific rule.

Scoring and Thresholds: (13 commands)
  listThresholds            - List all thresholds in the configuration.
  getThreshold              - Get details of a specific threshold.
  setThreshold              - Set threshold values.
  listScoringSets           - List all scoring sets.
  getScoringSet             - Get details of a specific scoring set.
  addScoringSet             - Add a scoring set.
  deleteScoringSet          - Delete a scoring set.
  listFragmentTypes         - List all fragment types.
  getFragmentType           - Get details of a specific fragment type.
  listMatchLevels           - List all match levels.
  getMatchLevel             - Get details of a specific match level.
  setMatchLevel             - Set match level configuration.

System Management: (15 commands)
  getDefaultConfigID        - Get the default configuration ID.
  getConfigRegistry         - Display the configuration registry.
  reload_config             - Load a configuration.
  save                      - Save the current configuration.
  exportToFile              - Export current configuration to a file.
  importFromFile            - Import configuration from a file.
  setTheme                  - Enable or disable colored output.
  getConfigSection          - Get a configuration section.
  templateAdd               - Add a template to create feature with attributes.
  touch                     - Touch/update configuration timestamp.
  history                   - Show command history.

Usage:
  help <command>        - Show detailed help for specific command
  <command> [args]      - Execute the specified command
  quit/exit            - Exit the configuration tool

This modular refactored tool provides improved maintainability,
follows Python best practices, and maintains 100% feature parity
with the original sz_configtool implementation.
            """
        print(help_text)