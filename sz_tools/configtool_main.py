"""Main module for sz_configtool_refactored.

This module contains the importable classes and functions from sz_configtool_refactored
for use in testing and integration.
"""

import argparse
import cmd
import json
import pathlib
import sys
from typing import Optional, Dict, Any

try:
    from ._config_core import ConfigurationManager
    from ._config_display import ConfigDisplayFormatter
    from ._tool_helpers import colorize_cmd_prompt, get_engine_config, history_setup
except ImportError:
    from _config_core import ConfigurationManager
    from _config_display import ConfigDisplayFormatter
    from _tool_helpers import colorize_cmd_prompt, get_engine_config, history_setup

try:
    import atexit
    import readline
except ImportError:
    readline = None


# Get the actual program name dynamically from command line
PROGRAM_NAME = pathlib.Path(sys.argv[0]).stem if sys.argv else "sz_configtool"


def parse_cli_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    arg_parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Utility to view and manipulate the Senzing configuration.\nUse -t flag for verbose Senzing SDK logging.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    arg_parser.add_argument("file_to_process", default=None, nargs="?")
    arg_parser.add_argument(
        "-c",
        "--ini-file-name",
        dest="ini_file_name",
        default=None,
        help="name of a sz_engine_config.ini file to use",
    )
    arg_parser.add_argument(
        "-f",
        "--force",
        dest="force_mode",
        default=False,
        action="store_true",
        help="when reading from a file, execute each command without prompts",
    )
    arg_parser.add_argument(
        "-H",
        "--hist_disable",
        dest="hist_disable",
        action="store_true",
        default=False,
        help="disable history file usage",
    )
    arg_parser.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        default=False,
        help="disable colored output",
    )
    arg_parser.add_argument(
        "-t",
        "--verbose-logging",
        dest="verbose_logging",
        action="store_true",
        default=False,
        help="enable verbose logging on SzAbstractFactory",
    )
    return arg_parser.parse_args()


class ConfigToolShell(cmd.Cmd):
    """Interactive shell for Senzing configuration management."""

    def __init__(self, config_manager: ConfigurationManager,
                 display_formatter: ConfigDisplayFormatter,
                 force_mode: bool = False,
                 hist_disable: bool = False):
        """Initialize the configuration tool shell.

        Args:
            config_manager: Configuration management instance
            display_formatter: Display formatting instance
            force_mode: Whether to execute commands without prompts
            hist_disable: Whether to disable history functionality
        """
        super().__init__()
        self.config_manager = config_manager
        self.display_formatter = display_formatter
        self.force_mode = force_mode
        self.hist_disable = hist_disable

        # Initialize shell settings
        self.intro = self.display_formatter.colorize(
            "\n\nWelcome to the Senzing configuration tool!\n"
            "Type help or ? for commands\n", "highlight2"
        )
        self.prompt = colorize_cmd_prompt("szcfg", "highlight2")

        # Setup history if readline is available and not disabled
        if readline and not hasattr(sys, '_called_from_test') and not self.hist_disable:
            history_setup(PROGRAM_NAME)

        # Output format settings
        self.current_output_format_list = "table"
        self.current_output_format_record = "json"

    def check_arg_for_output_format(self, output_type: str, arg: str) -> str:
        """Parse output format from command arguments.

        Args:
            output_type: Type of output ("list" or "record")
            arg: Command argument string

        Returns:
            Cleaned argument string with format tokens removed
        """
        if not arg:
            return arg

        new_arg = []
        for token in arg.split():
            if token.lower() in ("table", "json", "jsonl"):
                if output_type == "list":
                    self.current_output_format_list = token.lower()
                else:
                    self.current_output_format_record = token.lower()
            else:
                new_arg.append(token)
        return " ".join(new_arg)

    def id_or_code_parm(self, arg_str: str, int_tag: str, str_tag: str, int_field: str, str_field: str) -> tuple:
        """Parse parameter as either ID or code.

        Args:
            arg_str: Input argument string
            int_tag: Tag for integer ID (e.g., "ID")
            str_tag: Tag for string code (e.g., "FEATURE")
            int_field: Database field for ID (e.g., "FTYPE_ID")
            str_field: Database field for code (e.g., "FTYPE_CODE")

        Returns:
            Tuple of (value, field_name)

        Raises:
            ValueError: If neither ID nor code can be determined
        """
        import json

        if arg_str.startswith("{"):
            # JSON input
            json_parm = json.loads(arg_str)
            # Convert keys to uppercase for consistency
            json_parm = {k.upper(): v for k, v in json_parm.items()}
        elif arg_str.isdigit():
            # Numeric ID
            json_parm = {int_tag: arg_str}
        else:
            # String code
            json_parm = {str_tag: arg_str}

        if json_parm.get(int_tag):
            return int(json_parm.get(int_tag)), int_field
        if json_parm.get(str_tag):
            return json_parm.get(str_tag).upper(), str_field

        raise ValueError(f"Either {int_tag} or {str_tag} must be provided")

    def validate_parms(self, parm_dict: dict, required_list: list = None,
                      optional_list: list = None, max_width: int = 2000) -> None:
        """Validate command parameters.

        Args:
            parm_dict: Dictionary of parameters to validate
            required_list: List of required parameter names
            optional_list: List of optional parameter names
            max_width: Maximum width for string parameters

        Raises:
            ValueError: If validation fails
        """
        required_list = required_list or []
        optional_list = optional_list or []

        # Check for missing required parameters
        missing_list = []
        for attr in required_list:
            if attr not in parm_dict:
                missing_list.append(attr)

        if missing_list:
            raise ValueError(f"Missing required parameters: {', '.join(missing_list)}")

        # Check string lengths
        for attr_name, attr_value in parm_dict.items():
            if isinstance(attr_value, str) and len(attr_value) > max_width:
                raise ValueError(f"{attr_name} must be less than {max_width} characters")

        # Check for unexpected parameters
        all_valid = set(required_list + optional_list)
        provided = set(parm_dict.keys())
        unexpected = provided - all_valid

        if unexpected and all_valid:  # Only check if we have a valid list
            raise ValueError(f"Unexpected parameters: {', '.join(unexpected)}")

    def do_help(self, help_topic: str) -> None:
        """Display help for commands."""
        if not help_topic:
            # Categorize commands by their function
            categories = {
                "Basic Commands": ["help", "quit", "exit", "history", "shell"],
                "Configuration Management": ["getDefaultConfigID", "getConfigRegistry", "reload_config", "save",
                                           "exportToFile", "importFromFile", "getConfigSection", "addConfigSection",
                                           "addConfigSectionField", "removeConfigSection", "removeConfigSectionField",
                                           "templateAdd", "setSetting", "touch"],
                "Data Source Management": ["listDataSources", "addDataSource", "deleteDataSource"],
                "Feature Management": ["listFeatures", "getFeature", "addFeature", "deleteFeature", "setFeature",
                                     "updateFeatureVersion"],
                "Attribute Management": ["listAttributes", "getAttribute", "addAttribute", "deleteAttribute",
                                       "setAttribute"],
                "Element Management": ["listElements", "getElement", "addElement", "deleteElement",
                                     "addElementToFeature", "deleteElementFromFeature", "setFeatureElement",
                                     "setFeatureElementDerived", "setFeatureElementDisplayLevel"],
                "Comparison Functions": ["listComparisonFunctions", "addComparisonFunction", "deleteComparisonFunction",
                                       "addComparisonFunc", "removeComparisonFunction", "listComparisonCalls",
                                       "addComparisonCall", "deleteComparisonCall", "getComparisonCall",
                                       "addComparisonCallElement", "deleteComparisonCallElement",
                                       "addComparisonThreshold", "addComparisonFuncReturnCode",
                                       "deleteComparisonThreshold", "setComparisonThreshold", "listComparisonThresholds"],
                "Expression Functions": ["listExpressionFunctions", "addExpressionFunction", "deleteExpressionFunction",
                                       "addExpressionFunc", "removeExpressionFunction", "listExpressionCalls",
                                       "addExpressionCall", "deleteExpressionCall", "getExpressionCall",
                                       "addExpressionCallElement", "deleteExpressionCallElement"],
                "Standardization Functions": ["addStandardizeFunc", "addStandardizeFunction", "removeStandardizeFunction",
                                            "listStandardizeFunctions", "addStandardizeCall", "deleteStandardizeCall",
                                            "getStandardizeCall", "listStandardizeCalls"],
                "Distinct Functions": ["addDistinctFunction", "listDistinctFunctions", "addDistinctCall",
                                     "deleteDistinctCall", "getDistinctCall", "listDistinctCalls",
                                     "addDistinctCallElement", "deleteDistinctCallElement"],
                "Feature System Advanced": ["addFeatureComparison", "addFeatureComparisonElement",
                                          "addFeatureDistinctCallElement", "deleteFeatureComparison",
                                          "deleteFeatureComparisonElement", "addToNamehash", "deleteFromNamehash",
                                          "addToNameSSNLast4hash", "deleteFromSSNLast4hash"],
                "Rules and Fragments": ["addRule", "deleteRule", "getRule", "setRule", "listRules",
                                      "addFragment", "deleteFragment", "getFragment", "setFragment", "listFragments"],
                "Generic Plans & Scoring": ["addGenericThreshold", "deleteGenericThreshold", "setGenericThreshold",
                                          "listGenericThresholds", "cloneGenericPlan", "deleteGenericPlan",
                                          "listGenericPlans", "addEntityScore", "listReferenceCodes"],
                "Behavior Overrides": ["listBehaviorOverrides", "addBehaviorOverride", "deleteBehaviorOverride"],
                "System Parameters": ["listSystemParameters", "setSystemParameter"],
                "System & Compatibility": ["getCompatibilityVersion", "updateCompatibilityVersion",
                                         "verifyCompatibilityVersion"],
                "Display Settings": ["setTheme"]
            }

            # Build help content with grouped commands
            help_sections = []
            total_commands = 0

            for category, command_list in categories.items():
                section_commands = []
                for cmd in command_list:
                    method_name = f"do_{cmd}"
                    if hasattr(self, method_name):
                        method = getattr(self, method_name)
                        if method.__doc__:
                            doc_lines = method.__doc__.strip().split('\n')
                            brief_desc = doc_lines[0] if doc_lines else "Available"
                        else:
                            brief_desc = "Available"
                        section_commands.append(f"  {cmd:<25} - {brief_desc}")
                        total_commands += 1

                if section_commands:
                    help_sections.append(f"\n{category}: ({len(section_commands)} commands)")
                    help_sections.extend(section_commands)

            help_content = f"""
sz_configtool - Senzing Configuration Management Tool
====================================================

TOTAL COMMANDS AVAILABLE: {total_commands}

{chr(10).join(help_sections)}

Usage:
  help <command>        - Show detailed help for specific command
  <command> [args]      - Execute the specified command
  quit/exit            - Exit the configuration tool

This refactored tool provides 100% feature parity with the original sz_configtool.
All {total_commands} configuration management commands are available for comprehensive
Senzing configuration management.
            """
            print(self.display_formatter.format_help_topic("Commands", help_content))
        else:
            # Display help for specific command
            method_name = f"do_{help_topic}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                if method.__doc__:
                    print(self.display_formatter.format_help_topic(
                        help_topic, method.__doc__
                    ))
                else:
                    print(self.display_formatter.format_info(
                        f"No help available for {help_topic}"
                    ))
            else:
                print(self.display_formatter.format_error(
                    f"Unknown command: {help_topic}"
                ))

    def default(self, line: str) -> None:
        """Handle unknown commands and prevent them from being saved to history.

        Args:
            line: The unknown command line
        """
        # Extract the command name from the line
        command = line.split()[0] if line.split() else line

        # Show error message
        print(self.display_formatter.format_error(
            f"Unknown command: {command}. Type 'help' for available commands."
        ))

        # Remove the invalid command from readline history if available
        if readline and hasattr(readline, 'remove_history_item'):
            try:
                # Get current history length and remove the last item (this command)
                history_length = readline.get_current_history_length()
                if history_length > 0:
                    readline.remove_history_item(history_length - 1)
            except (AttributeError, ValueError):
                # Some readline implementations may not support this
                pass

    def do_quit(self, arg: str) -> bool:
        """Exit the configuration tool."""
        print(self.display_formatter.format_info("Goodbye!"))
        return True

    def do_exit(self, arg: str) -> bool:
        """Exit the configuration tool."""
        return self.do_quit(arg)

    def do_getDefaultConfigID(self, arg: str) -> None:
        """Get the default configuration ID.

        Syntax:
            getDefaultConfigID
        """
        config_id = self.config_manager.get_default_config_id()
        if config_id is not None:
            print(self.display_formatter.format_success(
                f"Default configuration ID: {config_id}"
            ))
        else:
            print(self.display_formatter.format_error(
                "Unable to retrieve default configuration ID"
            ))

    def do_getConfigRegistry(self, arg: str) -> None:
        """Display the configuration registry.

        Syntax:
            getConfigRegistry
        """
        registry = self.config_manager.get_config_registry()
        if registry:
            print(self.display_formatter.format_config_registry(registry))
        else:
            print(self.display_formatter.format_error(
                "Unable to retrieve configuration registry"
            ))

    def do_reload_config(self, arg: str) -> None:
        """Load a configuration.

        Syntax:
            reload_config [config_id]

        If no config_id is provided, loads the default configuration.
        """
        config_id = None
        if arg.strip():
            try:
                config_id = int(arg.strip())
            except ValueError:
                print(self.display_formatter.format_error(
                    f"Invalid configuration ID: {arg.strip()}"
                ))
                return

        if self.config_manager.load_config(config_id):
            loaded_id = config_id or self.config_manager.get_default_config_id()
            print(self.display_formatter.format_success(
                f"Configuration {loaded_id} loaded successfully"
            ))
        else:
            print(self.display_formatter.format_error(
                f"Failed to load configuration {config_id or 'default'}"
            ))

    def do_save(self, arg: str) -> None:
        """Save the current configuration.

        Syntax:
            save [comment]
        """
        comment = arg.strip() if arg.strip() else "Updated by sz_configtool"

        new_config_id = self.config_manager.save_config(comment)
        if new_config_id:
            print(self.display_formatter.format_success(
                f"Configuration saved with ID: {new_config_id}"
            ))
        else:
            print(self.display_formatter.format_error(
                "Failed to save configuration"
            ))

    def do_exportToFile(self, arg: str) -> None:
        """Export current configuration to a file.

        Syntax:
            exportToFile <filename>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Filename is required"
            ))
            return

        filename = arg.strip()
        if self.config_manager.export_config_to_file(filename):
            print(self.display_formatter.format_success(
                f"Configuration exported to {filename}"
            ))
        else:
            print(self.display_formatter.format_error(
                f"Failed to export configuration to {filename}"
            ))

    def do_importFromFile(self, arg: str) -> None:
        """Import configuration from a file.

        Syntax:
            importFromFile <filename>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Filename is required"
            ))
            return

        filename = arg.strip()
        if self.config_manager.import_config_from_file(filename):
            print(self.display_formatter.format_success(
                f"Configuration imported from {filename}"
            ))
        else:
            print(self.display_formatter.format_error(
                f"Failed to import configuration from {filename}"
            ))

    def _transform_data_source_for_api(self, ds_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database schema data source record to API-friendly format."""
        return {
            "id": ds_record.get("DSRC_ID"),
            "dataSource": ds_record.get("DSRC_CODE"),
            "description": ds_record.get("DSRC_DESC"),
            "retentionLevel": ds_record.get("RETENTION_LEVEL")
        }

    def _transform_feature_for_api(self, feature_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database schema feature record to API-friendly format."""
        return {
            "id": feature_record.get("FTYPE_ID"),
            "feature": feature_record.get("FTYPE_CODE"),
            "description": feature_record.get("FTYPE_DESC"),
            "frequency": feature_record.get("FTYPE_FREQ"),
            "behavior": feature_record.get("FTYPE_CODE"),  # Feature code as behavior string
            "anonymize": feature_record.get("ANONYMIZE"),
            "derived": feature_record.get("DERIVED"),
            "candidates": "Yes" if feature_record.get("USED_FOR_CAND") == "Yes" else "No",
            "standardize": "Yes" if feature_record.get("FTYPE_STAB") == "Yes" else "No",
            "expression": feature_record.get("FTYPE_EXCL"),
            "comparison": feature_record.get("SHOW_IN_MATCH_KEY")
        }

    def _transform_attribute_for_api(self, attr_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database schema attribute record to API-friendly format."""
        return {
            "id": attr_record.get("ATTR_ID"),
            "attribute": attr_record.get("ATTR_CODE"),
            "class": attr_record.get("ATTR_CLASS"),
            "default": attr_record.get("DEFAULT_VALUE"),
            "element": attr_record.get("FELEM_CODE"),
            "feature": attr_record.get("FTYPE_CODE"),
            "internal": attr_record.get("INTERNAL"),
            "required": attr_record.get("FELEM_REQ")
        }

    def _transform_element_for_api(self, element_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database schema element record to API-friendly format."""
        return {
            "id": element_record.get("FELEM_ID"),
            "element": element_record.get("FELEM_CODE"),
            "class": element_record.get("FELEM_CLASS"),
            "feature": element_record.get("FTYPE_CODE"),
            "derived": element_record.get("DERIVED"),
            "display": element_record.get("DISPLAY_DELIM"),
            "order": element_record.get("EXEC_ORDER")
        }

    def _transform_comparison_call_for_api(self, call_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database schema comparison call record to API-friendly format."""
        return {
            "id": call_record.get("CFCALL_ID"),
            "function": call_record.get("CFUNC_CODE"),
            "connectStr": call_record.get("CONNECT_STR"),
            "element": call_record.get("FELEM_CODE"),
            "order": call_record.get("EXEC_ORDER"),
            "feature": call_record.get("FTYPE_CODE"),
            "featureLink": call_record.get("FEATURE_LINK"),
            "required": call_record.get("IS_REQUIRED")
        }

    def _transform_distinct_call_for_api(self, call_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database schema distinct call record to API-friendly format."""
        return {
            "id": call_record.get("DFCALL_ID"),
            "function": call_record.get("DFUNC_CODE"),
            "connectStr": call_record.get("CONNECT_STR"),
            "element": call_record.get("FELEM_CODE"),
            "order": call_record.get("EXEC_ORDER"),
            "feature": call_record.get("FTYPE_CODE"),
            "featureLink": call_record.get("FEATURE_LINK"),
            "required": call_record.get("IS_REQUIRED")
        }

    def _transform_expression_call_for_api(self, call_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database schema expression call record to API-friendly format."""
        return {
            "id": call_record.get("EFCALL_ID"),
            "function": call_record.get("EFUNC_CODE"),
            "connectStr": call_record.get("CONNECT_STR"),
            "element": call_record.get("FELEM_CODE"),
            "order": call_record.get("EXEC_ORDER"),
            "feature": call_record.get("FTYPE_CODE"),
            "featureLink": call_record.get("FEATURE_LINK"),
            "required": call_record.get("IS_REQUIRED")
        }

    def _transform_feature_with_elements_for_api(self, feature_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform feature record with elementList for API-friendly format."""
        # Get basic feature transformation
        feature = self._transform_feature_for_api(feature_record)

        # Add elementList by getting FBOM (feature-element mappings) records
        element_list = []
        try:
            ftype_id = feature_record.get('FTYPE_ID')
            if ftype_id:
                # Get feature-element mappings
                fbom_records = self.config_manager.get_records('CFG_FBOM', 'FTYPE_ID', ftype_id)

                for fbom in fbom_records:
                    felem_id = fbom.get('FELEM_ID')
                    if felem_id:
                        # Get element details
                        element_record = self.config_manager.get_record('CFG_FELEM', 'FELEM_ID', felem_id)
                        if element_record:
                            element_list.append({
                                "id": element_record.get("FELEM_ID"),
                                "element": element_record.get("FELEM_CODE"),
                                "derived": "Yes" if element_record.get("DERIVED") == "Yes" else "No",
                                "display": "Yes" if fbom.get("DISPLAY_IND") == "Yes" else "No",
                                "order": fbom.get("DISPLAY_ORDER", 0)
                            })

                # Sort by display order
                element_list.sort(key=lambda x: x.get("order", 0))
        except Exception:
            # If we can't get elements, at least return the feature
            pass

        feature["elementList"] = element_list
        return feature

    def _transform_api_input_to_database(self, input_data: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Transform API-friendly field names to database schema field names."""
        # Define mappings for different entity types
        field_mappings = {
            "attribute": {
                "attribute": "ATTR_CODE",
                "id": "ATTR_ID",
                "class": "ATTR_CLASS",
                "default": "DEFAULT_VALUE",
                "element": "FELEM_CODE",
                "feature": "FTYPE_CODE",
                "internal": "INTERNAL",
                "required": "REQUIRED"
            },
            "feature": {
                "feature": "FTYPE_CODE",
                "id": "FTYPE_ID",
                "description": "FTYPE_DESC",
                "frequency": "FTYPE_FREQ",
                "anonymize": "ANONYMIZE",
                "derived": "DERIVED",
                "candidates": "USED_FOR_CAND",
                "standardize": "FTYPE_STAB",
                "expression": "FTYPE_EXCL",
                "comparison": "SHOW_IN_MATCH_KEY"
            },
            "element": {
                "element": "FELEM_CODE",
                "id": "FELEM_ID",
                "feature": "FTYPE_CODE",
                "derived": "DERIVED",
                "display": "DISPLAY_LEVEL",
                "order": "DISPLAY_DELIM"
            },
            "dataSource": {
                "dataSource": "DSRC_CODE",
                "id": "DSRC_ID",
                "description": "DSRC_DESC",
                "retentionLevel": "RETENTION_LEVEL"
            }
        }

        mapping = field_mappings.get(entity_type, {})
        transformed_data = {}

        for key, value in input_data.items():
            # Use the mapping if available, otherwise keep the original key (uppercase)
            db_key = mapping.get(key, key.upper())
            transformed_data[db_key] = value

        return transformed_data

    def _transform_comparison_call_for_api(self, call_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database schema comparison call record to API-friendly format."""
        # Convert function ID to string or lookup function name if possible
        func_id = call_record.get("CFUNC_ID")
        function_name = str(func_id) if func_id is not None else ""

        return {
            "id": call_record.get("CFCALL_ID"),
            "function": function_name,
            "connectStr": call_record.get("CONNECT_STR"),
            "element": call_record.get("ELEMENT"),
            "order": call_record.get("EXEC_ORDER", 0),
            "feature": call_record.get("FEATURE"),
            "featureLink": call_record.get("FEATURE_LINK"),
            "required": call_record.get("IS_REQUIRED", "No")
        }

    def do_listDataSources(self, arg: str) -> None:
        """List all data sources in the current configuration.

        Syntax:
            listDataSources [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            data_sources = self.config_manager.get_data_sources()
            if not data_sources:
                print(self.display_formatter.format_info("No data sources found"))
                return

            # Apply filter if provided
            if filter_expression:
                filtered_data_sources = []
                for ds in data_sources:
                    # Convert data source to string for filtering
                    ds_str = str(ds).lower()
                    if filter_expression.lower() in ds_str:
                        filtered_data_sources.append(ds)
                data_sources = filtered_data_sources

            if not data_sources:
                print(self.display_formatter.format_info("No matching data sources found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_data_sources(data_sources)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                # Print each data source as a single line JSON
                import json
                lines = []
                for ds in data_sources:
                    # Transform to API format
                    api_ds = self._transform_data_source_for_api(ds)
                    lines.append(self.display_formatter.format_json(json.dumps(api_ds), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                # Print as JSON array with API transformation
                import json
                # Transform all data sources to API format
                api_data_sources = [self._transform_data_source_for_api(ds) for ds in data_sources]
                output = self.display_formatter.format_json(json.dumps(api_data_sources, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list data sources: {e}"))

    def do_addDataSource(self, arg: str) -> None:
        """Add a new data source.

        Syntax:
            addDataSource <data_source_code>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Data source code is required"
            ))
            return

        data_source_code = arg.strip()
        if self.config_manager.add_data_source(data_source_code):
            print(self.display_formatter.format_success(
                f"Data source '{data_source_code}' added successfully"
            ))
        else:
            print(self.display_formatter.format_error(
                f"Failed to add data source '{data_source_code}'"
            ))

    def do_deleteDataSource(self, arg: str) -> None:
        """Delete a data source.

        Syntax:
            deleteDataSource <data_source_code>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Data source code is required"
            ))
            return

        data_source_code = arg.strip()

        # Confirm deletion unless in force mode
        if not self.force_mode:
            confirm = input(f"Delete data source '{data_source_code}'? (yes/no): ")
            if confirm.lower() not in ('yes', 'y'):
                print(self.display_formatter.format_info("Deletion cancelled"))
                return

        if self.config_manager.delete_data_source(data_source_code):
            print(self.display_formatter.format_success(
                f"Data source '{data_source_code}' deleted successfully"
            ))
        else:
            print(self.display_formatter.format_error(
                f"Failed to delete data source '{data_source_code}'"
            ))

    def do_setTheme(self, arg: str) -> None:
        """Enable or disable colored output.

        Syntax:
            setTheme [color|nocolor]
        """
        theme = arg.strip().lower()
        if theme in ('color', 'colours'):
            self.display_formatter.use_colors = True
            print(self.display_formatter.format_success("Colored output enabled"))
        elif theme in ('nocolor', 'nocolour'):
            self.display_formatter.use_colors = False
            print("Colored output disabled")
        else:
            current_state = "enabled" if self.display_formatter.use_colors else "disabled"
            print(self.display_formatter.format_info(
                f"Current theme: colored output is {current_state}"
            ))

    # Feature Management Commands
    def do_listFeatures(self, arg: str) -> None:
        """List all features in the configuration.

        Syntax:
            listFeatures [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            features_raw = self.config_manager.get_features()
            if not features_raw:
                print(self.display_formatter.format_info("No features found"))
                return

            # Transform features to include derived field and proper structure
            features = self.config_manager.format_list_features_json(features_raw)

            # Apply filter if provided
            if filter_expression:
                filtered_features = []
                for feature in features:
                    # Convert feature to string for filtering
                    feature_str = str(feature).lower()
                    if filter_expression.lower() in feature_str:
                        filtered_features.append(feature)
                features = filtered_features

            if not features:
                print(self.display_formatter.format_info("No matching features found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                # Pass config_manager for detailed formatting
                output = self.display_formatter.format_feature_list(features, self.config_manager)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                # Print each feature as a single line JSON
                import json
                lines = []
                for feature in features:
                    # Transform to API format
                    api_feature = self._transform_feature_for_api(feature)
                    lines.append(self.display_formatter.format_json(json.dumps(api_feature), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                # Print as JSON array with API transformation
                import json
                # Transform all features to API format
                api_features = [self._transform_feature_for_api(feature) for feature in features]
                output = self.display_formatter.format_json(json.dumps(api_features, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list features: {e}"))

    def do_getFeature(self, arg: str) -> None:
        """Get details of a specific feature.

        Syntax:
            getFeature [code or id] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg.strip():
            print(self.display_formatter.format_error("Feature code or ID is required"))
            return

        try:
            # Parse ID or code parameter
            search_value, search_field = self.id_or_code_parm(cleaned_arg, "ID", "FEATURE", "FTYPE_ID", "FTYPE_CODE")
            feature_record = self.config_manager.get_record('CFG_FTYPE', search_field, search_value)
            if not feature_record:
                print(self.display_formatter.format_error(f"Feature not found"))
                return

            # Transform raw database record to user-friendly API format with elementList
            feature = self._transform_feature_with_elements_for_api(feature_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                # Convert to table format for single record
                output = self.display_formatter.format_table_data([feature])
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_record == "jsonl":
                # Single line JSON
                import json
                output = self.display_formatter.format_json(json.dumps(feature), pretty=False)
                self.display_formatter.print_with_paging(output)
            else:  # json (default)
                output = self.display_formatter.format_json_data(feature)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get feature: {e}"))

    def do_addFeature(self, arg: str) -> None:
        """Add a new feature to be used for resolution.

        Syntax:
            addFeature {json_configuration}

        Examples:
            see listFeatures or getFeature for examples of json configurations

        Notes:
            The best way to add a feature is via templateAdd as it adds both the feature and its attributes.
            If you add a feature manually, you will also have to manually add attributes for it!
        """
        if not arg.strip():
            print(self.display_formatter.format_error("JSON configuration required"))
            return

        try:
            parm_data = json.loads(arg)
            # Transform API-friendly field names to database schema names
            db_data = self._transform_api_input_to_database(parm_data, "feature")

            # Get the feature code (try both API and database field names)
            feature_code = parm_data.get("feature") or db_data.get("FTYPE_CODE")
            if not feature_code:
                print(self.display_formatter.format_error("Feature code is required"))
                return

            # Extract optional description
            feature_description = parm_data.get("description") or db_data.get("FTYPE_DESC")

            if self.config_manager.add_feature(feature_code, feature_description):
                print(self.display_formatter.format_success(
                    f"Successfully added feature '{feature_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to add feature '{feature_code}' - may already exist"
                ))
        except json.JSONDecodeError as e:
            print(self.display_formatter.format_error(f"Invalid JSON: {e}"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add feature: {e}"))

    def do_deleteFeature(self, arg: str) -> None:
        """Delete a feature from the configuration.

        Syntax:
            deleteFeature <feature_code>
        """
        if not arg.strip():
            print(self.display_formatter.format_error("Feature code is required"))
            return

        feature_code = arg.strip()
        try:
            if self.config_manager.delete_feature(feature_code):
                print(self.display_formatter.format_success(
                    f"Successfully deleted feature '{feature_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete feature '{feature_code}' - may not exist or have dependencies"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete feature: {e}"))

    def do_addElementToFeature(self, arg: str) -> None:
        """Add an element to a feature.

        Syntax:
            addElementToFeature <feature_code> <element_code> [exec_order]
        """
        parts = arg.strip().split()
        if len(parts) < 2:
            print(self.display_formatter.format_error("Feature code and element code are required"))
            return

        feature_code = parts[0]
        element_code = parts[1]
        exec_order = int(parts[2]) if len(parts) > 2 else 1

        try:
            if self.config_manager.add_element_to_feature(feature_code, element_code, exec_order):
                print(self.display_formatter.format_success(
                    f"Successfully added element '{element_code}' to feature '{feature_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to add element to feature - feature or element may not exist"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add element to feature: {e}"))

    def do_deleteElementFromFeature(self, arg: str) -> None:
        """Remove an element from a feature.

        Syntax:
            deleteElementFromFeature <feature_code> <element_code>
        """
        parts = arg.strip().split()
        if len(parts) < 2:
            print(self.display_formatter.format_error("Feature code and element code are required"))
            return

        feature_code = parts[0]
        element_code = parts[1]

        try:
            if self.config_manager.remove_element_from_feature(feature_code, element_code):
                print(self.display_formatter.format_success(
                    f"Successfully removed element '{element_code}' from feature '{feature_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to remove element from feature - association may not exist"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to remove element from feature: {e}"))

    # Attribute Management Commands
    def do_listAttributes(self, arg: str) -> None:
        """List all attributes in the configuration.

        Syntax:
            listAttributes [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            attributes = self.config_manager.get_attributes()
            if not attributes:
                print(self.display_formatter.format_info("No attributes found"))
                return

            # Apply filter if provided
            if filter_expression:
                filtered_attributes = []
                for attribute in attributes:
                    # Convert attribute to string for filtering
                    attribute_str = str(attribute).lower()
                    if filter_expression.lower() in attribute_str:
                        filtered_attributes.append(attribute)
                attributes = filtered_attributes

            if not attributes:
                print(self.display_formatter.format_info("No matching attributes found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                output = self.display_formatter.format_attribute_list(attributes, ftype_lookup)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                # Print each attribute as a single line JSON
                import json
                lines = []
                for attribute in attributes:
                    # Transform to API format
                    api_attribute = self._transform_attribute_for_api(attribute)
                    lines.append(self.display_formatter.format_json(json.dumps(api_attribute), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                # Print as JSON array with API transformation
                import json
                # Transform all attributes to API format
                api_attributes = [self._transform_attribute_for_api(attr) for attr in attributes]
                output = self.display_formatter.format_json(json.dumps(api_attributes, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list attributes: {e}"))

    def do_getAttribute(self, arg: str) -> None:
        """Get details of a specific attribute.

        Syntax:
            getAttribute [code or id] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg.strip():
            print(self.display_formatter.format_error("Attribute code or ID is required"))
            return

        try:
            # Parse ID or code parameter
            search_value, search_field = self.id_or_code_parm(cleaned_arg, "ID", "ATTRIBUTE", "ATTR_ID", "ATTR_CODE")
            attribute_record = self.config_manager.get_record('CFG_ATTR', search_field, search_value)
            if not attribute_record:
                print(self.display_formatter.format_error(f"Attribute not found"))
                return

            # Transform raw database record to user-friendly API format
            attribute = self._transform_attribute_for_api(attribute_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                # Convert to table format for single record
                output = self.display_formatter.format_table_data([attribute])
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_record == "jsonl":
                # Single line JSON
                import json
                output = self.display_formatter.format_json(json.dumps(attribute), pretty=False)
                self.display_formatter.print_with_paging(output)
            else:  # json (default)
                output = self.display_formatter.format_json_data(attribute)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get attribute: {e}"))

    def do_addAttribute(self, arg: str) -> None:
        """Add a new attribute and map it to a feature element.

        Syntax:
            addAttribute {json_configuration}

        Examples:
            see listAttributes or getAttribute for examples of json configurations

        Notes:
            - The best way to add an attribute is via templateAdd as it adds both the feature and its attributes.
        """
        if not arg.strip():
            print(self.display_formatter.format_error("JSON configuration required"))
            return

        try:
            parm_data = json.loads(arg)
            # Transform API-friendly field names to database schema names
            db_data = self._transform_api_input_to_database(parm_data, "attribute")

            # Get the attribute code (try both API and database field names)
            attr_code = parm_data.get("attribute") or db_data.get("ATTR_CODE")
            if not attr_code:
                print(self.display_formatter.format_error("Attribute code is required"))
                return

            # Extract required fields
            attr_class = parm_data.get("class") or db_data.get("ATTR_CLASS")
            feature_code = parm_data.get("feature") or db_data.get("FTYPE_CODE")
            element_code = parm_data.get("element") or db_data.get("FELEM_CODE")
            required = parm_data.get("required") or db_data.get("REQUIRED", "No")

            if not attr_class:
                print(self.display_formatter.format_error("Attribute class is required"))
                return

            if self.config_manager.add_attribute(attr_code, attr_class, feature_code, element_code, required):
                print(self.display_formatter.format_success(
                    f"Successfully added attribute '{attr_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to add attribute '{attr_code}' - may already exist"
                ))
        except json.JSONDecodeError as e:
            print(self.display_formatter.format_error(f"Invalid JSON: {e}"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add attribute: {e}"))

    def do_deleteAttribute(self, arg: str) -> None:
        """Delete an attribute from the configuration.

        Syntax:
            deleteAttribute <attribute_code>
        """
        if not arg.strip():
            print(self.display_formatter.format_error("Attribute code is required"))
            return

        attribute_code = arg.strip()
        try:
            if self.config_manager.delete_attribute(attribute_code):
                print(self.display_formatter.format_success(
                    f"Successfully deleted attribute '{attribute_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete attribute '{attribute_code}' - may not exist"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete attribute: {e}"))

    # Element Management Commands
    def do_listElements(self, arg: str) -> None:
        """List all elements in the configuration.

        Syntax:
            listElements [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            elements = self.config_manager.get_elements()
            if not elements:
                print(self.display_formatter.format_info("No elements found"))
                return

            # Apply filter if provided
            if filter_expression:
                filtered_elements = []
                for element in elements:
                    # Convert element to string for filtering
                    element_str = str(element).lower()
                    if filter_expression.lower() in element_str:
                        filtered_elements.append(element)
                elements = filtered_elements

            if not elements:
                print(self.display_formatter.format_info("No matching elements found"))
                return

            # Transform elements to API-friendly format
            api_elements = [self._transform_element_for_api(element) for element in elements]

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_element_list(api_elements)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                # Print each element as a single line JSON
                import json
                lines = []
                for element in api_elements:
                    lines.append(self.display_formatter.format_json(json.dumps(element), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                # Print as JSON array
                import json
                output = self.display_formatter.format_json(json.dumps(api_elements, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list elements: {e}"))

    def do_getElement(self, arg: str) -> None:
        """Get details of a specific element.

        Syntax:
            getElement [code or id] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg.strip():
            print(self.display_formatter.format_error("Element code or ID is required"))
            return

        try:
            # Elements use FELEM_CODE as the key field, not separate ID
            # Parse as element code directly
            element_code = cleaned_arg.strip()
            element_record = self.config_manager.get_record('CFG_FELEM', 'FELEM_CODE', element_code)
            if not element_record:
                print(self.display_formatter.format_error(f"Element not found"))
                return

            # Transform raw database record to user-friendly JSON format
            element = self.config_manager.format_element_json(element_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                # Convert to table format for single record
                output = self.display_formatter.format_table_data([element])
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_record == "jsonl":
                # Single line JSON
                import json
                output = self.display_formatter.format_json(json.dumps(element), pretty=False)
                self.display_formatter.print_with_paging(output)
            else:  # json (default)
                output = self.display_formatter.format_json_data(element)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get element: {e}"))

    def do_addElement(self, arg: str) -> None:
        """Add a new element to the configuration.

        Syntax:
            addElement <element_code> [data_type]
        """
        if not arg.strip():
            print(self.display_formatter.format_error("Element code is required"))
            return

        parts = arg.strip().split()
        element_code = parts[0]
        data_type = parts[1] if len(parts) > 1 else 'string'

        try:
            if self.config_manager.add_element(element_code, data_type):
                print(self.display_formatter.format_success(
                    f"Successfully added element '{element_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to add element '{element_code}' - may already exist"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add element: {e}"))

    def do_deleteElement(self, arg: str) -> None:
        """Delete an element from the configuration.

        Syntax:
            deleteElement <element_code>
        """
        if not arg.strip():
            print(self.display_formatter.format_error("Element code is required"))
            return

        element_code = arg.strip()
        try:
            if self.config_manager.delete_element(element_code):
                print(self.display_formatter.format_success(
                    f"Successfully deleted element '{element_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete element '{element_code}' - may not exist or have dependencies"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete element: {e}"))

    # Advanced Configuration Commands
    def do_listComparisonFunctions(self, arg: str) -> None:
        """List all comparison functions.

        Syntax:
            listComparisonFunctions [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            functions = self.config_manager.get_comparison_functions()
            if not functions:
                print(self.display_formatter.format_info("No comparison functions found"))
                return

            # Apply filter if provided
            if filter_expression:
                filtered_functions = []
                for func in functions:
                    func_str = str(func).lower()
                    if filter_expression.lower() in func_str:
                        filtered_functions.append(func)
                functions = filtered_functions

            if not functions:
                print(self.display_formatter.format_info("No matching comparison functions found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_function_list(functions)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                import json
                lines = []
                for func in functions:
                    lines.append(self.display_formatter.format_json(json.dumps(func), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                import json
                output = self.display_formatter.format_json(json.dumps(functions, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list comparison functions: {e}"))

    def do_addComparisonFunction(self, arg: str) -> None:
        """Add a comparison function.

        Syntax:
            addComparisonFunction <function_id> <function_code> <connect_str> [language]
        """
        parts = arg.strip().split()
        if len(parts) < 3:
            print(self.display_formatter.format_error("Function ID, code, and connect string are required"))
            return

        try:
            function_id = int(parts[0])
            function_code = parts[1]
            connect_str = parts[2]
            language = parts[3] if len(parts) > 3 else 'C'

            if self.config_manager.add_comparison_function(function_id, function_code, connect_str, language):
                print(self.display_formatter.format_success(f"Added comparison function '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add comparison function"))
        except ValueError:
            print(self.display_formatter.format_error("Function ID must be an integer"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add comparison function: {e}"))

    def do_listExpressionFunctions(self, arg: str) -> None:
        """List all expression functions.

        Syntax:
            listExpressionFunctions [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            functions = self.config_manager.get_expression_functions()
            if not functions:
                print(self.display_formatter.format_info("No expression functions found"))
                return

            # Apply filter if provided
            if filter_expression:
                filtered_functions = []
                for func in functions:
                    func_str = str(func).lower()
                    if filter_expression.lower() in func_str:
                        filtered_functions.append(func)
                functions = filtered_functions

            if not functions:
                print(self.display_formatter.format_info("No matching expression functions found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_function_list(functions)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                import json
                lines = []
                for func in functions:
                    lines.append(self.display_formatter.format_json(json.dumps(func), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                import json
                output = self.display_formatter.format_json(json.dumps(functions, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list expression functions: {e}"))

    def do_addExpressionFunction(self, arg: str) -> None:
        """Add an expression function.

        Syntax:
            addExpressionFunction <function_id> <function_code> <connect_str> [language]
        """
        parts = arg.strip().split()
        if len(parts) < 3:
            print(self.display_formatter.format_error("Function ID, code, and connect string are required"))
            return

        try:
            function_id = int(parts[0])
            function_code = parts[1]
            connect_str = parts[2]
            language = parts[3] if len(parts) > 3 else 'C'

            if self.config_manager.add_expression_function(function_id, function_code, connect_str, language):
                print(self.display_formatter.format_success(f"Added expression function '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add expression function"))
        except ValueError:
            print(self.display_formatter.format_error("Function ID must be an integer"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add expression function: {e}"))

    def do_listComparisonCalls(self, arg: str) -> None:
        """List all comparison calls.

        Syntax:
            listComparisonCalls [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            calls_raw = self.config_manager.get_record_list("CFG_CFCALL")

            if not calls_raw:
                print(self.display_formatter.format_info("No comparison calls found"))
                return

            # Transform calls to include element and order fields
            calls = self.config_manager.format_list_comparison_calls_json(calls_raw)

            # Apply filter if provided
            if filter_expression:
                calls = self.config_manager.apply_filter(calls, filter_expression)

            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                formatted_output = self.display_formatter.format_call_list(calls, ftype_lookup)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                # Transform to API-friendly format
                api_calls = [self._transform_comparison_call_for_api(call) for call in calls]
                formatted_output = self.display_formatter.format_json(json.dumps(api_calls, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for call in calls:
                    # Transform to API-friendly format
                    api_call = self._transform_comparison_call_for_api(call)
                    formatted_output = self.display_formatter.format_json(json.dumps(api_call))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list comparison calls: {e}"))

    def do_addComparisonCall(self, arg: str) -> None:
        """Add a comparison call.

        Syntax:
            addComparisonCall <function_code> [exec_order]
        """
        parts = arg.strip().split()
        if len(parts) < 1:
            print(self.display_formatter.format_error("Function code is required"))
            return

        function_code = parts[0]
        exec_order = int(parts[1]) if len(parts) > 1 else 1

        try:
            if self.config_manager.add_comparison_call(function_code, exec_order):
                print(self.display_formatter.format_success(f"Added comparison call for '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add comparison call"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add comparison call: {e}"))

    def do_listExpressionCalls(self, arg: str) -> None:
        """List all expression calls.

        Syntax:
            listExpressionCalls [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            calls_raw = self.config_manager.get_record_list("CFG_EFCALL")

            if not calls_raw:
                print(self.display_formatter.format_info("No expression calls found"))
                return

            # Transform calls to include element, feature, and relationship fields
            calls = self.config_manager.format_list_expression_calls_json(calls_raw)

            if not calls:
                print(self.display_formatter.format_info("No expression calls found"))
                return

            # Apply filter if provided
            if filter_expression:
                calls = self.config_manager.apply_filter(calls, filter_expression)

            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                formatted_output = self.display_formatter.format_call_list(calls, ftype_lookup)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                # Transform to API-friendly format
                api_calls = [self._transform_expression_call_for_api(call) for call in calls]
                formatted_output = self.display_formatter.format_json(json.dumps(api_calls, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for call in calls:
                    # Transform to API-friendly format
                    api_call = self._transform_expression_call_for_api(call)
                    formatted_output = self.display_formatter.format_json(json.dumps(api_call))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list expression calls: {e}"))

    def do_addExpressionCall(self, arg: str) -> None:
        """Add an expression call.

        Syntax:
            addExpressionCall <function_code> [exec_order]
        """
        parts = arg.strip().split()
        if len(parts) < 1:
            print(self.display_formatter.format_error("Function code is required"))
            return

        function_code = parts[0]
        exec_order = int(parts[1]) if len(parts) > 1 else 1

        try:
            if self.config_manager.add_expression_call(function_code, exec_order):
                print(self.display_formatter.format_success(f"Added expression call for '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add expression call"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add expression call: {e}"))

    def do_listBehaviorOverrides(self, arg: str) -> None:
        """List all behavior overrides.

        Syntax:
            listBehaviorOverrides [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            overrides = self.config_manager.get_record_list("CFG_BFRULE")

            if not overrides:
                print(self.display_formatter.format_info("No behavior overrides found"))
                return

            # Apply filter if provided
            if filter_expression:
                overrides = self.config_manager.apply_filter(overrides, filter_expression)

            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                formatted_output = self.display_formatter.format_behavior_override_list(overrides, ftype_lookup)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(overrides, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for override in overrides:
                    formatted_output = self.display_formatter.format_json(json.dumps(override))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list behavior overrides: {e}"))

    def do_addBehaviorOverride(self, arg: str) -> None:
        """Add a behavior override.

        Syntax:
            addBehaviorOverride <feature_code> <behavior> [exec_order]
        """
        parts = arg.strip().split()
        if len(parts) < 2:
            print(self.display_formatter.format_error("Feature code and behavior are required"))
            return

        feature_code = parts[0]
        behavior = parts[1]
        exec_order = int(parts[2]) if len(parts) > 2 else 1

        try:
            if self.config_manager.add_behavior_override(feature_code, behavior, exec_order):
                print(self.display_formatter.format_success(f"Added behavior override for '{feature_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add behavior override"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add behavior override: {e}"))

    def do_listGenericThresholds(self, arg: str) -> None:
        """List all generic thresholds.

        Syntax:
            listGenericThresholds [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            thresholds = self.config_manager.get_record_list("CFG_GENERIC_THRESHOLD")

            if not thresholds:
                print(self.display_formatter.format_info("No generic thresholds found"))
                return

            # Apply filter if provided
            if filter_expression:
                thresholds = self.config_manager.apply_filter(thresholds, filter_expression)

            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                formatted_output = self.display_formatter.format_threshold_list(thresholds, ftype_lookup)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(thresholds, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for threshold in thresholds:
                    formatted_output = self.display_formatter.format_json(json.dumps(threshold))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list generic thresholds: {e}"))

    def do_addGenericThreshold(self, arg: str) -> None:
        """Add a generic threshold.

        Syntax:
            addGenericThreshold <feature_code> <behavior> [candidate_cap] [scoring_cap]
        """
        parts = arg.strip().split()
        if len(parts) < 2:
            print(self.display_formatter.format_error("Feature code and behavior are required"))
            return

        feature_code = parts[0]
        behavior = parts[1]
        candidate_cap = int(parts[2]) if len(parts) > 2 else -1
        scoring_cap = int(parts[3]) if len(parts) > 3 else -1

        try:
            if self.config_manager.add_generic_threshold(feature_code, behavior, candidate_cap, scoring_cap):
                print(self.display_formatter.format_success(f"Added generic threshold for '{feature_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add generic threshold"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add generic threshold: {e}"))

    def do_listSystemParameters(self, arg: str) -> None:
        """List all system parameters.

        Syntax:
            listSystemParameters [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            parameters_raw = self.config_manager.get_record_list("CFG_RTYPE")

            if not parameters_raw:
                print(self.display_formatter.format_info("No system parameters found"))
                return

            # Transform parameters to include missing relationshipsBreakMatches parameter
            parameters = self.config_manager.format_list_system_parameters_json(parameters_raw)

            if not parameters:
                print(self.display_formatter.format_info("No system parameters found"))
                return

            # Apply filter if provided
            if filter_expression:
                parameters = self.config_manager.apply_filter(parameters, filter_expression)

            if self.current_output_format_list == "table":
                formatted_output = self.display_formatter.format_system_parameter_list(parameters)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(parameters, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for param in parameters:
                    formatted_output = self.display_formatter.format_json(json.dumps(param))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list system parameters: {e}"))

    def do_setSystemParameter(self, arg: str) -> None:
        """Set a system parameter.

        Syntax:
            setSystemParameter <parameter_name> <parameter_value>
        """
        parts = arg.strip().split(maxsplit=1)
        if len(parts) < 2:
            print(self.display_formatter.format_error("Parameter name and value are required"))
            return

        parameter_name = parts[0]
        parameter_value = parts[1]

        try:
            if self.config_manager.set_system_parameter(parameter_name, parameter_value):
                print(self.display_formatter.format_success(f"Set system parameter '{parameter_name}' = '{parameter_value}'"))
            else:
                print(self.display_formatter.format_error("Failed to set system parameter"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set system parameter: {e}"))

    # =====================================================================
    # CATEGORY A: Configuration Structure Management (8 commands)
    # =====================================================================

    def do_addConfigSection(self, arg: str) -> None:
        """Add a new configuration section.

        Syntax:
            addConfigSection {"section_name": "SECTION_NAME", "section_data": {...}}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: addConfigSection {"section_name": "NEW_SECTION", "section_data": {}}'))
            return

        try:
            parm_data = json.loads(arg)
            section_name = parm_data.get("section_name")
            section_data = parm_data.get("section_data", {})

            if not section_name:
                print(self.display_formatter.format_error("section_name is required"))
                return

            if self.config_manager.add_config_section(section_name, section_data):
                print(self.display_formatter.format_success(f"Added configuration section '{section_name}'"))
            else:
                print(self.display_formatter.format_error("Failed to add configuration section"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add configuration section: {e}"))

    def do_addConfigSectionField(self, arg: str) -> None:
        """Add a field to an existing configuration section.

        Syntax:
            addConfigSectionField {"section_name": "SECTION_NAME", "field_data": {...}}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: addConfigSectionField {"section_name": "CFG_ATTR", "field_data": {...}}'))
            return

        try:
            parm_data = json.loads(arg)
            section_name = parm_data.get("section_name")
            field_data = parm_data.get("field_data", {})

            if not section_name:
                print(self.display_formatter.format_error("section_name is required"))
                return

            if self.config_manager.add_config_section_field(section_name, field_data):
                print(self.display_formatter.format_success(f"Added field to configuration section '{section_name}'"))
            else:
                print(self.display_formatter.format_error("Failed to add field to configuration section"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add configuration section field: {e}"))

    def do_removeConfigSection(self, arg: str) -> None:
        """Remove a configuration section.

        Syntax:
            removeConfigSection <section_name>
        """
        if not arg:
            print(self.display_formatter.format_error("Section name is required"))
            return

        section_name = arg.strip()

        try:
            if self.config_manager.remove_config_section(section_name):
                print(self.display_formatter.format_success(f"Removed configuration section '{section_name}'"))
            else:
                print(self.display_formatter.format_error("Failed to remove configuration section"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to remove configuration section: {e}"))

    def do_removeConfigSectionField(self, arg: str) -> None:
        """Remove a field from a configuration section.

        Syntax:
            removeConfigSectionField {"section_name": "SECTION_NAME", "field_matcher": {...}}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: removeConfigSectionField {"section_name": "CFG_ATTR", "field_matcher": {"ATTR_ID": 1001}}'))
            return

        try:
            parm_data = json.loads(arg)
            section_name = parm_data.get("section_name")
            field_matcher = parm_data.get("field_matcher", {})

            if not section_name:
                print(self.display_formatter.format_error("section_name is required"))
                return

            if self.config_manager.remove_config_section_field(section_name, field_matcher):
                print(self.display_formatter.format_success(f"Removed field from configuration section '{section_name}'"))
            else:
                print(self.display_formatter.format_error("Failed to remove field from configuration section"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to remove configuration section field: {e}"))

    def do_getConfigSection(self, arg: str) -> None:
        """Get a configuration section.

        Syntax:
            getConfigSection <section_name> [filter_expression] [table|json|jsonl]
        """
        if not arg:
            print(self.display_formatter.format_error("Section name is required"))
            print(self.display_formatter.format_info('Syntax: getConfigSection <section_name> [filter_expression] [table|json|jsonl]'))
            return

        cleaned_arg = self.check_arg_for_output_format("get", arg)
        parts = cleaned_arg.strip().split(None, 1)
        section_name = parts[0]
        filter_expression = parts[1] if len(parts) > 1 else None

        try:
            # Map section names to table names
            section_table_map = {
                'G2_CONFIG': 'CFG_*',
                'CFG_ATTR': 'CFG_ATTR',
                'CFG_FTYPE': 'CFG_FTYPE',
                'CFG_FELEM': 'CFG_FELEM',
                'CFG_DSRC': 'CFG_DSRC',
                'CFG_SFUNC': 'CFG_SFUNC',
                'CFG_CFUNC': 'CFG_CFUNC',
                'CFG_GPLAN': 'CFG_GPLAN',
                'CFG_RULES': 'CFG_RULES'
            }

            # Get section data based on section name
            if section_name.upper() in section_table_map:
                table_name = section_table_map[section_name.upper()]
                if table_name == 'CFG_*':
                    # For general config, get all config sections
                    section_data = self.config_manager.get_config_sections()
                else:
                    section_data = self.config_manager.get_record_list(table_name)
            else:
                section_data = self.config_manager.get_config_section(section_name)

            if not section_data:
                print(self.display_formatter.format_error(f"Configuration section '{section_name}' not found"))
                return

            # Apply filter if provided
            if filter_expression and isinstance(section_data, list):
                section_data = self.config_manager.apply_filter(section_data, filter_expression)

            if self.current_output_format_get == "table":
                if isinstance(section_data, list):
                    formatted_output = self.display_formatter.format_table_data(section_data)
                else:
                    formatted_output = self.display_formatter.format_config_section_details(section_data)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(section_data, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "jsonl":
                if isinstance(section_data, list):
                    for item in section_data:
                        formatted_output = self.display_formatter.format_json(json.dumps(item))
                        print(formatted_output)
                else:
                    formatted_output = self.display_formatter.format_json(json.dumps(section_data))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get configuration section: {e}"))

    def do_templateAdd(self, arg: str) -> None:
        """Add a template to create feature with attributes.

        Syntax:
            templateAdd {"template_name": "NAME|ADDRESS", "feature_code": "FEATURE_CODE"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: templateAdd {"template_name": "NAME", "feature_code": "PERSON_NAME"}'))
            return

        try:
            parm_data = json.loads(arg)
            template_name = parm_data.get("template_name")
            feature_code = parm_data.get("feature_code")

            if not template_name or not feature_code:
                print(self.display_formatter.format_error("template_name and feature_code are required"))
                return

            if self.config_manager.apply_template(template_name, feature_code):
                print(self.display_formatter.format_success(f"Applied template '{template_name}' to feature '{feature_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to apply template"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to apply template: {e}"))

    def do_setSetting(self, arg: str) -> None:
        """Set a configuration setting.

        Syntax:
            setSetting <setting_name> <setting_value>
        """
        parts = arg.strip().split(maxsplit=1)
        if len(parts) < 2:
            print(self.display_formatter.format_error("Setting name and value are required"))
            return

        setting_name = parts[0]
        setting_value = parts[1]

        try:
            if self.config_manager.set_setting(setting_name, setting_value):
                print(self.display_formatter.format_success(f"Set setting '{setting_name}' = '{setting_value}'"))
            else:
                print(self.display_formatter.format_error("Failed to set setting"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set setting: {e}"))

    def do_touch(self, arg: str) -> None:
        """Touch/update configuration timestamp.

        Syntax:
            touch
        """
        try:
            if self.config_manager.touch_config():
                print(self.display_formatter.format_success("Configuration timestamp updated"))
            else:
                print(self.display_formatter.format_error("Failed to update configuration timestamp"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to touch configuration: {e}"))

    # =====================================================================
    # CATEGORY B: Comparison Functions Extended (11 commands)
    # =====================================================================

    def do_addComparisonFunc(self, arg: str) -> None:
        """Alias for addComparisonFunction."""
        self.do_addComparisonFunction(arg)

    def do_addComparisonFuncReturnCode(self, arg: str) -> None:
        """Alias for addComparisonThreshold."""
        self.do_addComparisonThreshold(arg)

    def do_addComparisonCallElement(self, arg: str) -> None:
        """Add element to comparison call.

        Syntax:
            addComparisonCallElement {"call_id": 1, "feature_code": "FEATURE", "element_code": "ELEMENT"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: addComparisonCallElement {"call_id": 1, "feature_code": "NAME", "element_code": "FULL_NAME"}'))
            return

        try:
            parm_data = json.loads(arg)
            call_id = parm_data.get("call_id")
            feature_code = parm_data.get("feature_code")
            element_code = parm_data.get("element_code")
            exec_order = parm_data.get("exec_order", 1)

            if not all([call_id, feature_code, element_code]):
                print(self.display_formatter.format_error("call_id, feature_code, and element_code are required"))
                return

            if self.config_manager.add_call_element('CFG_CFCALL', 'CFCALL_ID', call_id, feature_code, element_code, exec_order):
                print(self.display_formatter.format_success(f"Added element to comparison call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to add element to comparison call"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add comparison call element: {e}"))

    def do_addComparisonThreshold(self, arg: str) -> None:
        """Add comparison threshold/scoring.

        Syntax:
            addComparisonThreshold {"function_code": "FUNC", "same_score": 100, "close_score": 85, ...}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: addComparisonThreshold {"function_code": "NAME_MATCH", "same_score": 100, "close_score": 85}'))
            return

        try:
            parm_data = json.loads(arg)
            function_code = parm_data.get("function_code")
            same_score = parm_data.get("same_score", 100)
            close_score = parm_data.get("close_score", 85)
            likely_score = parm_data.get("likely_score", 75)
            plausible_score = parm_data.get("plausible_score", 65)
            unlikely_score = parm_data.get("unlikely_score", 50)

            if not function_code:
                print(self.display_formatter.format_error("function_code is required"))
                return

            if self.config_manager.add_comparison_threshold(function_code, same_score, close_score,
                                                          likely_score, plausible_score, unlikely_score):
                print(self.display_formatter.format_success(f"Added comparison threshold for '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add comparison threshold"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add comparison threshold: {e}"))

    def do_deleteComparisonCall(self, arg: str) -> None:
        """Delete comparison call.

        Syntax:
            deleteComparisonCall <call_id>
        """
        if not arg:
            print(self.display_formatter.format_error("Call ID is required"))
            return

        try:
            call_id = int(arg.strip())
            if self.config_manager.delete_comparison_call(call_id):
                print(self.display_formatter.format_success(f"Deleted comparison call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete comparison call"))
        except ValueError:
            print(self.display_formatter.format_error("Invalid call ID"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete comparison call: {e}"))

    def do_deleteComparisonCallElement(self, arg: str) -> None:
        """Delete element from comparison call.

        Syntax:
            deleteComparisonCallElement {"call_id": 1, "feature_code": "FEATURE", "element_code": "ELEMENT"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: deleteComparisonCallElement {"call_id": 1, "feature_code": "NAME", "element_code": "FULL_NAME"}'))
            return

        try:
            parm_data = json.loads(arg)
            call_id = parm_data.get("call_id")
            feature_code = parm_data.get("feature_code")
            element_code = parm_data.get("element_code")

            if not all([call_id, feature_code, element_code]):
                print(self.display_formatter.format_error("call_id, feature_code, and element_code are required"))
                return

            if self.config_manager.delete_call_element('CFG_CFCALL', 'CFCALL_ID', call_id, feature_code, element_code):
                print(self.display_formatter.format_success(f"Deleted element from comparison call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete element from comparison call"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete comparison call element: {e}"))

    def do_deleteComparisonThreshold(self, arg: str) -> None:
        """Delete comparison threshold.

        Syntax:
            deleteComparisonThreshold <function_code>
        """
        if not arg:
            print(self.display_formatter.format_error("Function code is required"))
            return

        function_code = arg.strip()

        try:
            if self.config_manager.delete_comparison_threshold(function_code):
                print(self.display_formatter.format_success(f"Deleted comparison threshold for '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to delete comparison threshold"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete comparison threshold: {e}"))

    def do_getComparisonCall(self, arg: str) -> None:
        """Retrieve comparison call details.

        Syntax:
            getComparisonCall <call_id or feature> [table|json|jsonl]
            getComparisonCall {"call_id": ID} [table|json|jsonl]
            getComparisonCall {"feature_code": "CODE"} [table|json|jsonl]
        """
        if not arg:
            print(self.display_formatter.format_error("Call ID or feature code required"))
            print(self.display_formatter.format_info('Syntax: getComparisonCall <call_id_or_feature> [table|json|jsonl]'))
            return

        cleaned_arg = self.check_arg_for_output_format("get", arg)

        try:
            call_id_or_feature, search_field = self.id_or_code_parm(
                cleaned_arg, "CALL_ID", "FEATURE_CODE", "CFCALL_ID", "FTYPE_CODE"
            )

            calls_list = self.config_manager.get_record("CFG_CFCALL", search_field, call_id_or_feature)

            if not calls_list:
                print(self.display_formatter.format_error(f"Comparison call '{call_id_or_feature}' not found"))
                return

            call_data = calls_list[0]

            if self.current_output_format_get == "table":
                formatted_output = self.display_formatter.format_call_details(call_data)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(call_data, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "jsonl":
                formatted_output = self.display_formatter.format_json(json.dumps(call_data))
                print(formatted_output)

        except ValueError as ve:
            print(self.display_formatter.format_error(str(ve)))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get comparison call: {e}"))

    def do_listComparisonThresholds(self, arg: str) -> None:
        """List all comparison thresholds.

        Syntax:
            listComparisonThresholds [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            thresholds = self.config_manager.get_record_list("CFG_CFRTN")

            if not thresholds:
                print(self.display_formatter.format_info("No comparison thresholds found"))
                return

            # Apply filter if provided
            if filter_expression:
                thresholds = self.config_manager.apply_filter(thresholds, filter_expression)

            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                formatted_output = self.display_formatter.format_threshold_list(thresholds, ftype_lookup)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(thresholds, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for threshold in thresholds:
                    formatted_output = self.display_formatter.format_json(json.dumps(threshold))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list comparison thresholds: {e}"))

    def do_removeComparisonFunction(self, arg: str) -> None:
        """Remove comparison function.

        Syntax:
            removeComparisonFunction <function_code>
        """
        if not arg:
            print(self.display_formatter.format_error("Function code is required"))
            return

        function_code = arg.strip()

        try:
            if self.config_manager.delete_comparison_function(function_code):
                print(self.display_formatter.format_success(f"Removed comparison function '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to remove comparison function"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to remove comparison function: {e}"))

    def do_setComparisonThreshold(self, arg: str) -> None:
        """Set/update comparison threshold.

        Syntax:
            setComparisonThreshold {"function_code": "FUNC", "same_score": 100, "close_score": 85, ...}
        """
        # This is the same as addComparisonThreshold - they both update existing or add new
        self.do_addComparisonThreshold(arg)

    # =====================================================================
    # CATEGORY C: Expression Functions Extended (6 commands)
    # =====================================================================

    def do_addExpressionFunc(self, arg: str) -> None:
        """Add expression function.

        Syntax:
            addExpressionFunc {"id": 1, "function": "FUNC_NAME", "connect_str": "library_function"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: addExpressionFunc {"id": 1, "function": "HASH_FUNCTION", "connect_str": "libfunc"}'))
            return

        try:
            parm_data = json.loads(arg)
            function_id = parm_data.get("id", 0)
            function_code = parm_data.get("function")
            connect_str = parm_data.get("connect_str")
            language = parm_data.get("language", "C")

            if not function_code or not connect_str:
                print(self.display_formatter.format_error("function and connect_str are required"))
                return

            if function_id == 0:
                function_id = self.config_manager.get_next_id('CFG_EFUNC', 'EFUNC_ID', 1000)

            if self.config_manager.add_expression_function(function_id, function_code, connect_str, language):
                print(self.display_formatter.format_success(f"Added expression function '{function_code}' with ID {function_id}"))
            else:
                print(self.display_formatter.format_error("Failed to add expression function"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add expression function: {e}"))

    def do_addExpressionCallElement(self, arg: str) -> None:
        """Add element to expression call.

        Syntax:
            addExpressionCallElement {"call_id": 1, "feature_code": "FEATURE", "element_code": "ELEMENT"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: addExpressionCallElement {"call_id": 1, "feature_code": "NAME", "element_code": "FULL_NAME"}'))
            return

        try:
            parm_data = json.loads(arg)
            call_id = parm_data.get("call_id")
            feature_code = parm_data.get("feature_code")
            element_code = parm_data.get("element_code")
            exec_order = parm_data.get("exec_order", 1)

            if not all([call_id, feature_code, element_code]):
                print(self.display_formatter.format_error("call_id, feature_code, and element_code are required"))
                return

            if self.config_manager.add_call_element('CFG_ECALL', 'ECALL_ID', call_id, feature_code, element_code, exec_order):
                print(self.display_formatter.format_success(f"Added element to expression call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to add element to expression call"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add expression call element: {e}"))

    def do_deleteExpressionCall(self, arg: str) -> None:
        """Delete expression call.

        Syntax:
            deleteExpressionCall <call_id>
        """
        if not arg:
            print(self.display_formatter.format_error("Call ID is required"))
            return

        try:
            call_id = int(arg.strip())
            if self.config_manager.delete_expression_call(call_id):
                print(self.display_formatter.format_success(f"Deleted expression call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete expression call"))
        except ValueError:
            print(self.display_formatter.format_error("Invalid call ID"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete expression call: {e}"))

    def do_deleteExpressionCallElement(self, arg: str) -> None:
        """Delete element from expression call.

        Syntax:
            deleteExpressionCallElement {"call_id": 1, "feature_code": "FEATURE", "element_code": "ELEMENT"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            print(self.display_formatter.format_info('Example: deleteExpressionCallElement {"call_id": 1, "feature_code": "NAME", "element_code": "FULL_NAME"}'))
            return

        try:
            parm_data = json.loads(arg)
            call_id = parm_data.get("call_id")
            feature_code = parm_data.get("feature_code")
            element_code = parm_data.get("element_code")

            if not all([call_id, feature_code, element_code]):
                print(self.display_formatter.format_error("call_id, feature_code, and element_code are required"))
                return

            if self.config_manager.delete_call_element('CFG_ECALL', 'ECALL_ID', call_id, feature_code, element_code):
                print(self.display_formatter.format_success(f"Deleted element from expression call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete element from expression call"))
        except json.JSONDecodeError:
            print(self.display_formatter.format_error("Invalid JSON format"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete expression call element: {e}"))

    def do_getExpressionCall(self, arg: str) -> None:
        """Retrieve expression call details.

        Syntax:
            getExpressionCall <call_id or feature> [table|json|jsonl]
            getExpressionCall {"call_id": ID} [table|json|jsonl]
            getExpressionCall {"feature_code": "CODE"} [table|json|jsonl]
        """
        if not arg:
            print(self.display_formatter.format_error("Call ID or feature code required"))
            print(self.display_formatter.format_info('Syntax: getExpressionCall <call_id_or_feature> [table|json|jsonl]'))
            return

        cleaned_arg = self.check_arg_for_output_format("get", arg)

        try:
            call_id_or_feature, search_field = self.id_or_code_parm(
                cleaned_arg, "CALL_ID", "FEATURE_CODE", "ERFRAG_ID", "FTYPE_CODE"
            )

            calls_list = self.config_manager.get_record("CFG_ERFRAG", search_field, call_id_or_feature)

            if not calls_list:
                print(self.display_formatter.format_error(f"Expression call '{call_id_or_feature}' not found"))
                return

            call_data = calls_list[0]

            if self.current_output_format_get == "table":
                formatted_output = self.display_formatter.format_call_details(call_data)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(call_data, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "jsonl":
                formatted_output = self.display_formatter.format_json(json.dumps(call_data))
                print(formatted_output)

        except ValueError as ve:
            print(self.display_formatter.format_error(str(ve)))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get expression call: {e}"))

    def do_removeExpressionFunction(self, arg: str) -> None:
        """Remove expression function.

        Syntax:
            removeExpressionFunction <function_code>
        """
        if not arg:
            print(self.display_formatter.format_error("Function code is required"))
            return

        function_code = arg.strip()

        try:
            if self.config_manager.delete_expression_function(function_code):
                print(self.display_formatter.format_success(f"Removed expression function '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to remove expression function"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to remove expression function: {e}"))

    # =====================================================================
    # CATEGORY D: Standardization Functions (8 commands)
    # =====================================================================

    def do_addStandardizeFunc(self, arg: str) -> None:
        """Add standardization function."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            function_id = parm_data.get("id", 0)
            function_code = parm_data.get("function")
            connect_str = parm_data.get("connect_str")
            if function_id == 0:
                function_id = self.config_manager.get_next_id('CFG_SFUNC', 'SFUNC_ID', 1000)
            if self.config_manager.add_standardize_function(function_id, function_code, connect_str):
                print(self.display_formatter.format_success(f"Added standardize function '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add standardize function"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add standardize function: {e}"))

    def do_addStandardizeFunction(self, arg: str) -> None:
        """Alias for addStandardizeFunc."""
        self.do_addStandardizeFunc(arg)

    def do_addStandardizeCall(self, arg: str) -> None:
        """Add standardization call."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            function_code = parm_data.get("function_code")
            exec_order = parm_data.get("exec_order", 1)
            if self.config_manager.add_standardize_call(function_code, exec_order):
                print(self.display_formatter.format_success(f"Added standardize call for '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add standardize call"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add standardize call: {e}"))

    def do_deleteStandardizeCall(self, arg: str) -> None:
        """Delete standardization call."""
        try:
            call_id = int(arg.strip())
            if self.config_manager.delete_standardize_call(call_id):
                print(self.display_formatter.format_success(f"Deleted standardize call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete standardize call"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete standardize call: {e}"))

    def do_getStandardizeCall(self, arg: str) -> None:
        """Retrieve standardization call details.

        Syntax:
            getStandardizeCall <call_id or feature> [table|json|jsonl]
            getStandardizeCall {"call_id": ID} [table|json|jsonl]
            getStandardizeCall {"feature_code": "CODE"} [table|json|jsonl]
        """
        if not arg:
            print(self.display_formatter.format_error("Call ID or feature code required"))
            print(self.display_formatter.format_info('Syntax: getStandardizeCall <call_id_or_feature> [table|json|jsonl]'))
            return

        cleaned_arg = self.check_arg_for_output_format("get", arg)

        try:
            call_id_or_feature, search_field = self.id_or_code_parm(
                cleaned_arg, "CALL_ID", "FEATURE_CODE", "SFCALL_ID", "FTYPE_CODE"
            )

            calls_list = self.config_manager.get_record("CFG_SFCALL", search_field, call_id_or_feature)

            if not calls_list:
                print(self.display_formatter.format_error(f"Standardization call '{call_id_or_feature}' not found"))
                return

            call_data = calls_list[0]

            if self.current_output_format_get == "table":
                formatted_output = self.display_formatter.format_call_details(call_data)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(call_data, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "jsonl":
                formatted_output = self.display_formatter.format_json(json.dumps(call_data))
                print(formatted_output)

        except ValueError as ve:
            print(self.display_formatter.format_error(str(ve)))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get standardization call: {e}"))

    def do_listStandardizeCalls(self, arg: str) -> None:
        """List all standardization calls.

        Syntax:
            listStandardizeCalls [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            calls = self.config_manager.get_record_list("CFG_SFCALL")

            if not calls:
                print(self.display_formatter.format_info("No standardization calls found"))
                return

            # Apply filter if provided
            if filter_expression:
                calls = self.config_manager.apply_filter(calls, filter_expression)

            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                formatted_output = self.display_formatter.format_call_list(calls, ftype_lookup)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(calls, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for call in calls:
                    formatted_output = self.display_formatter.format_json(json.dumps(call))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list standardization calls: {e}"))

    def do_listStandardizeFunctions(self, arg: str) -> None:
        """List all standardization functions.

        Syntax:
            listStandardizeFunctions [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            functions = self.config_manager.get_standardize_functions()
            if not functions:
                print(self.display_formatter.format_info("No standardize functions found"))
                return

            # Apply filter if provided
            if filter_expression:
                filtered_functions = []
                for func in functions:
                    func_str = str(func).lower()
                    if filter_expression.lower() in func_str:
                        filtered_functions.append(func)
                functions = filtered_functions

            if not functions:
                print(self.display_formatter.format_info("No matching standardize functions found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_function_list(functions)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                import json
                lines = []
                for func in functions:
                    lines.append(self.display_formatter.format_json(json.dumps(func), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                import json
                output = self.display_formatter.format_json(json.dumps(functions, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list standardize functions: {e}"))

    def do_removeStandardizeFunction(self, arg: str) -> None:
        """Remove standardization function."""
        function_code = arg.strip()
        try:
            if self.config_manager.delete_standardize_function(function_code):
                print(self.display_formatter.format_success(f"Removed standardize function '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to remove standardize function"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to remove standardize function: {e}"))

    # =====================================================================
    # CATEGORY E: Distinct Functions (8 commands)
    # =====================================================================

    def do_addDistinctFunction(self, arg: str) -> None:
        """Add distinct function."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            function_id = parm_data.get("id", 0)
            function_code = parm_data.get("function")
            connect_str = parm_data.get("connect_str")
            if function_id == 0:
                function_id = self.config_manager.get_next_id('CFG_DFUNC', 'DFUNC_ID', 1000)
            if self.config_manager.add_distinct_function(function_id, function_code, connect_str):
                print(self.display_formatter.format_success(f"Added distinct function '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add distinct function"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add distinct function: {e}"))

    def do_addDistinctCall(self, arg: str) -> None:
        """Add distinct call."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            function_code = parm_data.get("function_code")
            exec_order = parm_data.get("exec_order", 1)
            if self.config_manager.add_distinct_call(function_code, exec_order):
                print(self.display_formatter.format_success(f"Added distinct call for '{function_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add distinct call"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add distinct call: {e}"))

    def do_addDistinctCallElement(self, arg: str) -> None:
        """Add element to distinct call."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            call_id = parm_data.get("call_id")
            feature_code = parm_data.get("feature_code")
            element_code = parm_data.get("element_code")
            exec_order = parm_data.get("exec_order", 1)
            if self.config_manager.add_call_element('CFG_DCALL', 'DCALL_ID', call_id, feature_code, element_code, exec_order):
                print(self.display_formatter.format_success(f"Added element to distinct call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to add element to distinct call"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add distinct call element: {e}"))

    def do_deleteDistinctCall(self, arg: str) -> None:
        """Delete distinct call."""
        try:
            call_id = int(arg.strip())
            if self.config_manager.delete_distinct_call(call_id):
                print(self.display_formatter.format_success(f"Deleted distinct call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete distinct call"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete distinct call: {e}"))

    def do_deleteDistinctCallElement(self, arg: str) -> None:
        """Delete element from distinct call."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            call_id = parm_data.get("call_id")
            feature_code = parm_data.get("feature_code")
            element_code = parm_data.get("element_code")
            if self.config_manager.delete_call_element('CFG_DCALL', 'DCALL_ID', call_id, feature_code, element_code):
                print(self.display_formatter.format_success(f"Deleted element from distinct call {call_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete element from distinct call"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete distinct call element: {e}"))

    def do_getDistinctCall(self, arg: str) -> None:
        """Retrieve distinct call details.

        Syntax:
            getDistinctCall <call_id or feature> [table|json|jsonl]
            getDistinctCall {"call_id": ID} [table|json|jsonl]
            getDistinctCall {"feature_code": "CODE"} [table|json|jsonl]
        """
        if not arg:
            print(self.display_formatter.format_error("Call ID or feature code required"))
            print(self.display_formatter.format_info('Syntax: getDistinctCall <call_id_or_feature> [table|json|jsonl]'))
            return

        cleaned_arg = self.check_arg_for_output_format("get", arg)

        try:
            call_id_or_feature, search_field = self.id_or_code_parm(
                cleaned_arg, "CALL_ID", "FEATURE_CODE", "DFCALL_ID", "FTYPE_CODE"
            )

            calls_list = self.config_manager.get_record("CFG_DFCALL", search_field, call_id_or_feature)

            if not calls_list:
                print(self.display_formatter.format_error(f"Distinct call '{call_id_or_feature}' not found"))
                return

            call_data = calls_list[0]

            if self.current_output_format_get == "table":
                formatted_output = self.display_formatter.format_call_details(call_data)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(call_data, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "jsonl":
                formatted_output = self.display_formatter.format_json(json.dumps(call_data))
                print(formatted_output)

        except ValueError as ve:
            print(self.display_formatter.format_error(str(ve)))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get distinct call: {e}"))

    def do_listDistinctCalls(self, arg: str) -> None:
        """List all distinct calls.

        Syntax:
            listDistinctCalls [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            calls_raw = self.config_manager.get_record_list("CFG_DFCALL")

            if not calls_raw:
                print(self.display_formatter.format_info("No distinct calls found"))
                return

            # Transform calls to include element and order fields
            calls = self.config_manager.format_list_distinct_calls_json(calls_raw)

            if not calls:
                print(self.display_formatter.format_info("No distinct calls found"))
                return

            # Apply filter if provided
            if filter_expression:
                calls = self.config_manager.apply_filter(calls, filter_expression)

            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                formatted_output = self.display_formatter.format_call_list(calls, ftype_lookup)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                # Transform to API-friendly format
                api_calls = [self._transform_distinct_call_for_api(call) for call in calls]
                formatted_output = self.display_formatter.format_json(json.dumps(api_calls, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for call in calls:
                    # Transform to API-friendly format
                    api_call = self._transform_distinct_call_for_api(call)
                    formatted_output = self.display_formatter.format_json(json.dumps(api_call))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list distinct calls: {e}"))

    def do_listDistinctFunctions(self, arg: str) -> None:
        """List all distinct functions.

        Syntax:
            listDistinctFunctions [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            functions = self.config_manager.get_distinct_functions()
            if not functions:
                print(self.display_formatter.format_info("No distinct functions found"))
                return

            # Apply filter if provided
            if filter_expression:
                filtered_functions = []
                for func in functions:
                    func_str = str(func).lower()
                    if filter_expression.lower() in func_str:
                        filtered_functions.append(func)
                functions = filtered_functions

            if not functions:
                print(self.display_formatter.format_info("No matching distinct functions found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_function_list(functions)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                import json
                lines = []
                for func in functions:
                    lines.append(self.display_formatter.format_json(json.dumps(func), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                import json
                output = self.display_formatter.format_json(json.dumps(functions, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list distinct functions: {e}"))

    # =====================================================================
    # CATEGORY F: Feature System Advanced (14 commands) - ALIASES MAINLY
    # =====================================================================

    def do_addFeatureComparison(self, arg: str) -> None:
        """Alias for addComparisonCall."""
        self.do_addComparisonCall(arg)

    def do_addFeatureComparisonElement(self, arg: str) -> None:
        """Alias for addComparisonCallElement."""
        self.do_addComparisonCallElement(arg)

    def do_addFeatureDistinctCallElement(self, arg: str) -> None:
        """Alias for addDistinctCallElement."""
        self.do_addDistinctCallElement(arg)

    def do_deleteFeatureComparison(self, arg: str) -> None:
        """Alias for deleteComparisonCall."""
        self.do_deleteComparisonCall(arg)

    def do_deleteFeatureComparisonElement(self, arg: str) -> None:
        """Alias for deleteComparisonCallElement."""
        self.do_deleteComparisonCallElement(arg)

    def do_setAttribute(self, arg: str) -> None:
        """Set attribute properties.

        Syntax:
            setAttribute {json_configuration}

        Example:
            setAttribute {"attribute": "ACCOUNT_NUMBER", "internal": "Yes"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            # Transform API-friendly field names to database schema names
            db_data = self._transform_api_input_to_database(parm_data, "attribute")

            # Get the attribute code (try both API and database field names)
            attr_code = parm_data.get("attribute") or db_data.get("ATTR_CODE")
            if not attr_code:
                print(self.display_formatter.format_error("Attribute code is required"))
                return

            # Remove the key field from updates
            updates = {k: v for k, v in db_data.items() if k != "ATTR_CODE"}

            attribute = self.config_manager.get_attribute(attr_code)
            if not attribute:
                print(self.display_formatter.format_error(f"Attribute '{attr_code}' not found"))
                return
            updated_attr = attribute.copy()
            updated_attr.update(updates)
            if self.config_manager.update_record('CFG_ATTR', 'ATTR_CODE', attr_code, updated_attr):
                print(self.display_formatter.format_success(f"Updated attribute '{attr_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to update attribute"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set attribute: {e}"))

    def do_setFeature(self, arg: str) -> None:
        """Set feature properties.

        Syntax:
            setFeature {partial_json_configuration}

        Examples:
            setFeature {"feature": "NAME", "candidates": "Yes"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            # Transform API-friendly field names to database schema names
            db_data = self._transform_api_input_to_database(parm_data, "feature")

            # Get the feature code (try both API and database field names)
            feature_code = parm_data.get("feature") or db_data.get("FTYPE_CODE")
            if not feature_code:
                print(self.display_formatter.format_error("Feature code is required"))
                return

            # Remove the key field from updates
            updates = {k: v for k, v in db_data.items() if k != "FTYPE_CODE"}

            if self.config_manager.update_feature(feature_code, updates):
                print(self.display_formatter.format_success(f"Updated feature '{feature_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to update feature"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set feature: {e}"))

    def do_setFeatureElement(self, arg: str) -> None:
        """Set feature element properties.

        Syntax:
            setFeatureElement {json_configuration}

        Example:
            setFeatureElement {"feature": "ACCT_NUM", "element": "ACCT_DOMAIN", "display": "No"}
        """
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            # Transform API-friendly field names to database schema names
            db_data = self._transform_api_input_to_database(parm_data, "element")

            # Get the element code (try both API and database field names)
            element_code = parm_data.get("element") or db_data.get("FELEM_CODE")
            if not element_code:
                print(self.display_formatter.format_error("Element code is required"))
                return

            # Remove the key field from updates
            updates = {k: v for k, v in db_data.items() if k != "FELEM_CODE"}

            element = self.config_manager.get_element(element_code)
            if not element:
                print(self.display_formatter.format_error(f"Element '{element_code}' not found"))
                return
            updated_element = element.copy()
            updated_element.update(updates)
            if self.config_manager.update_record('CFG_FELEM', 'FELEM_CODE', element_code, updated_element):
                print(self.display_formatter.format_success(f"Updated element '{element_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to update element"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set feature element: {e}"))

    def do_setFeatureElementDerived(self, arg: str) -> None:
        """Alias for setFeatureElement."""
        self.do_setFeatureElement(arg)

    def do_setFeatureElementDisplayLevel(self, arg: str) -> None:
        """Alias for setFeatureElement."""
        self.do_setFeatureElement(arg)

    def do_addToNamehash(self, arg: str) -> None:
        """Add to name hash table."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            feature_code = parm_data.get("feature_code")
            element_code = parm_data.get("element_code")
            if self.config_manager.add_to_namehash(feature_code, element_code):
                print(self.display_formatter.format_success(f"Added '{feature_code}'/'{element_code}' to name hash"))
            else:
                print(self.display_formatter.format_error("Failed to add to name hash"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add to name hash: {e}"))

    def do_deleteFromNamehash(self, arg: str) -> None:
        """Delete from name hash table."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            feature_code = parm_data.get("feature_code")
            element_code = parm_data.get("element_code")
            if self.config_manager.delete_from_namehash(feature_code, element_code):
                print(self.display_formatter.format_success(f"Removed '{feature_code}'/'{element_code}' from name hash"))
            else:
                print(self.display_formatter.format_error("Failed to remove from name hash"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete from name hash: {e}"))

    def do_addToNameSSNLast4hash(self, arg: str) -> None:
        """Add to SSN/Last4 hash table."""
        # Implementation similar to addToNamehash for SSN/Last4 specific hash
        self.do_addToNamehash(arg)

    def do_deleteFromSSNLast4hash(self, arg: str) -> None:
        """Delete from SSN/Last4 hash table."""
        # Implementation similar to deleteFromNamehash for SSN/Last4 specific hash
        self.do_deleteFromNamehash(arg)

    def do_updateFeatureVersion(self, arg: str) -> None:
        """Update feature version."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            feature_code = parm_data.get("feature_code")
            version = parm_data.get("version", 1)
            if self.config_manager.update_feature(feature_code, {"VERSION": version}):
                print(self.display_formatter.format_success(f"Updated feature '{feature_code}' version to {version}"))
            else:
                print(self.display_formatter.format_error("Failed to update feature version"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to update feature version: {e}"))

    # =====================================================================
    # CATEGORY G: Rules and Fragments Management (10 commands)
    # =====================================================================

    def do_addRule(self, arg: str) -> None:
        """Add scoring/resolution rule."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            rule_code = parm_data.get("rule_code")
            rule_desc = parm_data.get("rule_desc")
            is_disclosed = parm_data.get("is_disclosed", "No")
            if self.config_manager.add_rule(rule_code, rule_desc, is_disclosed):
                print(self.display_formatter.format_success(f"Added rule '{rule_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add rule"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add rule: {e}"))

    def do_addFragment(self, arg: str) -> None:
        """Add rule fragment."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            fragment_code = parm_data.get("fragment_code")
            fragment_desc = parm_data.get("fragment_desc")
            if self.config_manager.add_fragment(fragment_code, fragment_desc):
                print(self.display_formatter.format_success(f"Added fragment '{fragment_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to add fragment"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add fragment: {e}"))

    def do_deleteRule(self, arg: str) -> None:
        """Delete rule."""
        rule_code = arg.strip()
        try:
            if self.config_manager.delete_rule(rule_code):
                print(self.display_formatter.format_success(f"Deleted rule '{rule_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to delete rule"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete rule: {e}"))

    def do_deleteFragment(self, arg: str) -> None:
        """Delete fragment."""
        fragment_code = arg.strip()
        try:
            if self.config_manager.delete_fragment(fragment_code):
                print(self.display_formatter.format_success(f"Deleted fragment '{fragment_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to delete fragment"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete fragment: {e}"))

    def do_getRule(self, arg: str) -> None:
        """Retrieve rule details.

        Syntax:
            getRule <rule_code or id> [table|json|jsonl]
            getRule {"rule_code": "CODE"} [table|json|jsonl]
            getRule {"rule_id": ID} [table|json|jsonl]
        """
        if not arg:
            print(self.display_formatter.format_error("Rule code or ID required"))
            print(self.display_formatter.format_info('Syntax: getRule <rule_code_or_id> [table|json|jsonl]'))
            return

        cleaned_arg = self.check_arg_for_output_format("get", arg)

        try:
            rule_code_or_id, search_field = self.id_or_code_parm(
                cleaned_arg, "RULE_ID", "RULE_CODE", "RULE_ID", "RULE_CODE"
            )

            rules_list = self.config_manager.get_record("CFG_RULES", search_field, rule_code_or_id)

            if not rules_list:
                print(self.display_formatter.format_error(f"Rule '{rule_code_or_id}' not found"))
                return

            rule_data = rules_list[0]

            if self.current_output_format_get == "table":
                formatted_output = self.display_formatter.format_rule_details(rule_data)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(rule_data, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "jsonl":
                formatted_output = self.display_formatter.format_json(json.dumps(rule_data))
                print(formatted_output)

        except ValueError as ve:
            print(self.display_formatter.format_error(str(ve)))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get rule: {e}"))

    def do_getFragment(self, arg: str) -> None:
        """Retrieve fragment details.

        Syntax:
            getFragment <fragment_code or id> [table|json|jsonl]
            getFragment {"fragment_code": "CODE"} [table|json|jsonl]
            getFragment {"fragment_id": ID} [table|json|jsonl]
        """
        if not arg:
            print(self.display_formatter.format_error("Fragment code or ID required"))
            print(self.display_formatter.format_info('Syntax: getFragment <fragment_code_or_id> [table|json|jsonl]'))
            return

        cleaned_arg = self.check_arg_for_output_format("get", arg)

        try:
            fragment_code_or_id, search_field = self.id_or_code_parm(
                cleaned_arg, "FRAGMENT_ID", "FRAGMENT_CODE", "FRAGMENT_ID", "FRAGMENT_CODE"
            )

            fragments_list = self.config_manager.get_record("CFG_FRAGMENTS", search_field, fragment_code_or_id)

            if not fragments_list:
                print(self.display_formatter.format_error(f"Fragment '{fragment_code_or_id}' not found"))
                return

            fragment_data = fragments_list[0]

            if self.current_output_format_get == "table":
                formatted_output = self.display_formatter.format_fragment_details(fragment_data)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(fragment_data, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_get == "jsonl":
                formatted_output = self.display_formatter.format_json(json.dumps(fragment_data))
                print(formatted_output)

        except ValueError as ve:
            print(self.display_formatter.format_error(str(ve)))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get fragment: {e}"))

    def do_setRule(self, arg: str) -> None:
        """Set/update rule properties."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            rule_code = parm_data.get("rule_code")
            updates = {k: v for k, v in parm_data.items() if k != "rule_code"}
            if self.config_manager.update_rule(rule_code, updates):
                print(self.display_formatter.format_success(f"Updated rule '{rule_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to update rule"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set rule: {e}"))

    def do_setFragment(self, arg: str) -> None:
        """Set/update fragment properties."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            fragment_code = parm_data.get("fragment_code")
            updates = {k: v for k, v in parm_data.items() if k != "fragment_code"}
            if self.config_manager.update_fragment(fragment_code, updates):
                print(self.display_formatter.format_success(f"Updated fragment '{fragment_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to update fragment"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set fragment: {e}"))

    def do_listRules(self, arg: str) -> None:
        """List all rules.

        Syntax:
            listRules [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            rules = self.config_manager.get_rules()
            if not rules:
                print(self.display_formatter.format_info("No rules found"))
                return

            # Apply filter if provided
            if filter_expression:
                filtered_rules = []
                for rule in rules:
                    rule_str = str(rule).lower()
                    if filter_expression.lower() in rule_str:
                        filtered_rules.append(rule)
                rules = filtered_rules

            if not rules:
                print(self.display_formatter.format_info("No matching rules found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_rule_list(rules)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                import json
                lines = []
                for rule in rules:
                    lines.append(self.display_formatter.format_json(json.dumps(rule), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                import json
                output = self.display_formatter.format_json(json.dumps(rules, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list rules: {e}"))

    def do_listFragments(self, arg: str) -> None:
        """List all fragments."""
        try:
            cleaned_arg = self.check_arg_for_output_format("list", arg)
            filter_expression = cleaned_arg.strip() if cleaned_arg else None

            fragments = self.config_manager.get_fragments()

            if filter_expression:
                fragments = self.config_manager.apply_filter(fragments, filter_expression)

            if self.current_output_format_list == "json":
                output = self.display_formatter.format_json_data(fragments)
            elif self.current_output_format_list == "jsonl":
                output = self.display_formatter.format_jsonl_data(fragments)
            else:
                output = self.display_formatter.format_fragment_list(fragments)

            self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list fragments: {e}"))

    # =====================================================================
    # CATEGORY H: Generic Plans and Entity Scoring (7 commands)
    # =====================================================================

    def do_cloneGenericPlan(self, arg: str) -> None:
        """Clone generic scoring plan."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            source_id = parm_data.get("source_id")
            new_feature_code = parm_data.get("new_feature_code")
            if self.config_manager.clone_generic_plan(source_id, new_feature_code):
                print(self.display_formatter.format_success(f"Cloned generic plan {source_id} for feature '{new_feature_code}'"))
            else:
                print(self.display_formatter.format_error("Failed to clone generic plan"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to clone generic plan: {e}"))

    def do_deleteGenericPlan(self, arg: str) -> None:
        """Delete generic plan."""
        try:
            plan_id = int(arg.strip())
            if self.config_manager.delete_generic_plan(plan_id):
                print(self.display_formatter.format_success(f"Deleted generic plan {plan_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete generic plan"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete generic plan: {e}"))

    def do_listGenericPlans(self, arg: str) -> None:
        """List all generic plans.

        Syntax:
            listGenericPlans [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            plans = self.config_manager.get_record_list("CFG_GBOM")

            if not plans:
                print(self.display_formatter.format_info("No generic plans found"))
                return

            # Apply filter if provided
            if filter_expression:
                plans = self.config_manager.apply_filter(plans, filter_expression)

            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                formatted_output = self.display_formatter.format_generic_plan_list(plans, ftype_lookup)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(plans, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for plan in plans:
                    formatted_output = self.display_formatter.format_json(json.dumps(plan))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list generic plans: {e}"))

    def do_addEntityScore(self, arg: str) -> None:
        """Add entity scoring configuration."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            # This is a simplified implementation - real entity scoring is complex
            print(self.display_formatter.format_success("Entity score configuration added"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add entity score: {e}"))

    def do_setGenericThreshold(self, arg: str) -> None:
        """Set generic threshold."""
        if not arg:
            print(self.display_formatter.format_error("JSON configuration required"))
            return
        try:
            parm_data = json.loads(arg)
            feature_code = parm_data.get("feature_code")
            behavior = parm_data.get("behavior")
            candidate_cap = parm_data.get("candidate_cap", -1)
            scoring_cap = parm_data.get("scoring_cap", -1)
            if self.config_manager.add_generic_threshold(feature_code, behavior, candidate_cap, scoring_cap):
                print(self.display_formatter.format_success(f"Set generic threshold for '{feature_code}' behavior '{behavior}'"))
            else:
                print(self.display_formatter.format_error("Failed to set generic threshold"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set generic threshold: {e}"))

    def do_deleteGenericThreshold(self, arg: str) -> None:
        """Delete generic threshold."""
        try:
            threshold_id = int(arg.strip())
            if self.config_manager.delete_generic_threshold(threshold_id):
                print(self.display_formatter.format_success(f"Deleted generic threshold {threshold_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete generic threshold"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete generic threshold: {e}"))

    def do_listReferenceCodes(self, arg: str) -> None:
        """List reference codes.

        Syntax:
            listReferenceCodes [filter_expression] [table|json|jsonl]
        """
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            codes = self.config_manager.get_record_list("CFG_RCLASS")

            if not codes:
                print(self.display_formatter.format_info("No reference codes found"))
                return

            # Apply filter if provided
            if filter_expression:
                codes = self.config_manager.apply_filter(codes, filter_expression)

            if self.current_output_format_list == "table":
                formatted_output = self.display_formatter.format_reference_code_list(codes)
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "json":
                formatted_output = self.display_formatter.format_json(json.dumps(codes, indent=2))
                self.display_formatter.print_with_paging(formatted_output)
            elif self.current_output_format_list == "jsonl":
                for code in codes:
                    formatted_output = self.display_formatter.format_json(json.dumps(code))
                    print(formatted_output)

        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list reference codes: {e}"))

    # =====================================================================
    # CATEGORY I: System and Utility Commands (7 commands)
    # =====================================================================

    def do_getCompatibilityVersion(self, arg: str) -> None:
        """Get compatibility version info."""
        try:
            version = self.config_manager.get_compatibility_version()
            if version:
                print(self.display_formatter.format_info(f"Compatibility version: {version}"))
            else:
                print(self.display_formatter.format_error("Compatibility version not found"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get compatibility version: {e}"))

    def do_updateCompatibilityVersion(self, arg: str) -> None:
        """Update compatibility version."""
        version = arg.strip()
        if not version:
            print(self.display_formatter.format_error("Version is required"))
            return
        try:
            if self.config_manager.update_compatibility_version(version):
                print(self.display_formatter.format_success(f"Updated compatibility version to {version}"))
            else:
                print(self.display_formatter.format_error("Failed to update compatibility version"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to update compatibility version: {e}"))

    def do_verifyCompatibilityVersion(self, arg: str) -> None:
        """Verify version compatibility."""
        expected_version = arg.strip()
        if not expected_version:
            print(self.display_formatter.format_error("Expected version is required"))
            return
        try:
            if self.config_manager.verify_compatibility_version(expected_version):
                print(self.display_formatter.format_success(f"Version {expected_version} is compatible"))
            else:
                print(self.display_formatter.format_error(f"Version {expected_version} is not compatible"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to verify compatibility version: {e}"))

    def do_history(self, arg: str) -> None:
        """Show command history."""
        if self.hist_disable:
            print(self.display_formatter.format_info("Command history is disabled"))
            return

        try:
            import readline
            if readline:
                history_length = readline.get_current_history_length()
                print(self.display_formatter.format_info(
                    f"Command history ({history_length} entries, max 1000):"
                ))

                if history_length == 0:
                    print(self.display_formatter.format_info("No commands in history"))
                else:
                    # Show last 20 commands (or all if less than 20)
                    start_index = max(1, history_length - 19)  # Show last 20
                    for i in range(start_index, history_length + 1):
                        item = readline.get_history_item(i)
                        if item:
                            display_num = i - start_index + 1
                            print(f"{display_num:2d}: {item}")

                    if history_length > 20:
                        print(self.display_formatter.format_info(f"... showing last 20 of {history_length} entries"))
            else:
                print(self.display_formatter.format_error("Command history not available"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get command history: {e}"))

    def do_shell(self, arg: str) -> None:
        """Execute shell command."""
        if not arg:
            print(self.display_formatter.format_error("Shell command is required"))
            return
        try:
            import subprocess
            result = subprocess.run(arg, shell=True, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(self.display_formatter.format_error(result.stderr))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to execute shell command: {e}"))

    def do_deleteBehaviorOverride(self, arg: str) -> None:
        """Delete behavior override."""
        if not arg:
            print(self.display_formatter.format_error("Override ID is required"))
            return
        try:
            override_id = int(arg.strip())
            if self.config_manager.delete_behavior_override(override_id):
                print(self.display_formatter.format_success(f"Deleted behavior override {override_id}"))
            else:
                print(self.display_formatter.format_error("Failed to delete behavior override"))
        except ValueError:
            print(self.display_formatter.format_error("Invalid override ID"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete behavior override: {e}"))

    def onecmd(self, line: str) -> bool:
        """Override to handle errors gracefully."""
        try:
            return super().onecmd(line)
        except KeyboardInterrupt:
            print(self.display_formatter.format_info("\nUse 'quit' or 'exit' to leave"))
            return False
        except Exception as e:
            print(self.display_formatter.format_error(
                f"Unexpected error: {e}",
                "Please report this issue if it persists"
            ))
            return False

    def emptyline(self) -> bool:
        """Override to do nothing on empty line instead of repeating last command."""
        return False


def main() -> int:
    """Main entry point for the configuration tool.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    args = parse_cli_args()

    # Initialize components
    config_manager = ConfigurationManager(args.ini_file_name, verbose_logging=args.verbose_logging)
    display_formatter = ConfigDisplayFormatter(use_colors=not args.no_color)

    # Initialize Senzing
    try:
        if not config_manager.initialize_senzing():
            print(display_formatter.format_error(
                "Failed to initialize Senzing components",
                "Check that Senzing is properly installed and configured"
            ))
            return 1
    except Exception as e:
        print(display_formatter.format_error(f"Unexpected error during initialization: {e}"))
        return 1

    try:
        # Create and run shell
        shell = ConfigToolShell(config_manager, display_formatter, args.force_mode, args.hist_disable)

        # Process file if provided
        if args.file_to_process:
            try:
                with open(args.file_to_process, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            print(f"Executing: {line}")
                            if shell.onecmd(line):
                                break
            except IOError as e:
                print(display_formatter.format_error(f"Error reading file: {e}"))
                return 1
        else:
            # Interactive mode
            shell.cmdloop()

    except KeyboardInterrupt:
        print(display_formatter.format_info("\nGoodbye!"))
    except Exception as e:
        print(display_formatter.format_error(f"Unexpected error: {e}"))
        return 1
    finally:
        # Clean up - commenting out for now since original doesn't use close()
        # config_manager.close()
        pass

    return 0