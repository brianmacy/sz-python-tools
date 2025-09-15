"""Display formatting functionality for sz_configtool.

This module handles all display formatting and presentation logic,
separate from business logic and UI control.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

try:
    from ._tool_helpers import Colors
except ImportError:
    from _tool_helpers import Colors

try:
    import prettytable
except (ImportError, ModuleNotFoundError):
    prettytable = None

try:
    from pygments import formatters, highlight, lexers
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

import sys
import os
import shutil


class ConfigDisplayFormatter:
    """Formats configuration data for display."""

    def __init__(self, use_colors: bool = True):
        """Initialize the display formatter.

        Args:
            use_colors: Whether to use colored output
        """
        self._use_colors = use_colors
        self._prettytable_available = prettytable is not None
        self._enable_paging = True  # Enable automatic paging for long output

    @property
    def use_colors(self) -> bool:
        """Get the current color setting."""
        return self._use_colors

    @use_colors.setter
    def use_colors(self, value: bool) -> None:
        """Set the color setting."""
        self._use_colors = value

    def colorize(self, text: str, color_list: str = "None") -> str:
        """Apply colors to text if colors are enabled.

        Args:
            text: Text to colorize
            color_list: Color specification

        Returns:
            Colorized text or original text if colors disabled
        """
        if not self._use_colors:
            return text
        return Colors.apply(text, color_list)

    def format_message(self, message: str, message_type: str = "") -> str:
        """Format a message with appropriate colors.

        Args:
            message: Message text
            message_type: Type of message (ERROR, WARNING, INFO, SUCCESS)

        Returns:
            Formatted message
        """
        color_map = {
            "ERROR": "bad",
            "WARNING": "caution,italics",
            "INFO": "highlight2",
            "SUCCESS": "good"
        }

        color = color_map.get(message_type.upper(), message_type)
        return f"\n{self.colorize(message, color)}\n"

    def format_json(self, json_str: str, pretty: bool = True) -> str:
        """Format JSON with syntax highlighting.

        Args:
            json_str: JSON string to format
            pretty: Whether to pretty-print the JSON

        Returns:
            Formatted JSON string
        """
        if not json_str:
            return ""

        try:
            # Parse and optionally pretty-print JSON
            if pretty:
                json_data = json.loads(json_str)
                json_str = json.dumps(json_data, indent=2, sort_keys=True)

            # Apply syntax highlighting if available
            if PYGMENTS_AVAILABLE and self._use_colors:
                lexer = lexers.JsonLexer()
                formatter = formatters.TerminalFormatter()
                return highlight(json_str, lexer, formatter)

            # Fallback to simple colorization
            return self._colorize_json_simple(json_str)

        except json.JSONDecodeError:
            return json_str

    def _colorize_json_simple(self, json_str: str) -> str:
        """Simple JSON colorization without pygments.

        Args:
            json_str: JSON string to colorize

        Returns:
            Colorized JSON string
        """
        if not self._use_colors:
            return json_str

        # Simple approach: colorize keys first, then values
        try:
            # First colorize keys (strings followed by colons)
            key_pattern = r'"([^"\\]*(?:\\.[^"\\]*)*)":'
            def colorize_key(match):
                try:
                    return self.colorize(match.group(0), "attr_color")
                except Exception:
                    return match.group(0)
            json_str = re.sub(key_pattern, colorize_key, json_str)

            # Then colorize values (strings not followed by colons)
            value_pattern = r'"([^"\\]*(?:\\.[^"\\]*)*)"(?!\s*:)'
            def colorize_value(match):
                try:
                    # Skip if this text is already colorized (contains escape sequences)
                    text = match.group(0)
                    if '\x1b[' in text:
                        return text
                    return self.colorize(text, "value_color")
                except Exception:
                    return match.group(0)
            json_str = re.sub(value_pattern, colorize_value, json_str)

        except Exception:
            # If regex processing fails, return original string
            pass

        return json_str

    def format_config_registry(self, registry_json: str) -> str:
        """Format configuration registry for display.

        Args:
            registry_json: Configuration registry JSON

        Returns:
            Formatted registry display
        """
        try:
            registry_data = json.loads(registry_json)
            configs = registry_data.get('CONFIGS', [])

            if not prettytable:
                # Fallback to simple text format
                output = self.colorize("\nConfiguration Registry:\n", "highlight2")
                for config in configs:
                    config_id = config.get('CONFIG_ID', 'Unknown')
                    config_comment = config.get('CONFIG_COMMENT', 'No comment')
                    sys_create_dt = config.get('SYS_CREATE_DT', 'Unknown')
                    output += f"ID: {config_id}, Comment: {config_comment}, Created: {sys_create_dt}\n"
                return output

            # Use prettytable for better formatting
            try:
                table = prettytable.PrettyTable()
                table.field_names = ["Config ID", "Comment", "Created"]
                table.align = "l"

                for config in configs:
                    table.add_row([
                        config.get('CONFIG_ID', 'Unknown'),
                        config.get('CONFIG_COMMENT', 'No comment'),
                        config.get('SYS_CREATE_DT', 'Unknown')
                    ])

                header = self.colorize("\nConfiguration Registry:", "highlight2")
                return f"{header}\n{table}\n"
            except Exception:
                # Fallback to simple format if prettytable fails
                output = self.colorize("\nConfiguration Registry:\n", "highlight2")
                for config in configs:
                    config_id = config.get('CONFIG_ID', 'Unknown')
                    config_comment = config.get('CONFIG_COMMENT', 'No comment')
                    sys_create_dt = config.get('SYS_CREATE_DT', 'Unknown')
                    output += f"ID: {config_id}, Comment: {config_comment}, Created: {sys_create_dt}\n"
                return output

        except json.JSONDecodeError:
            return self.format_message("ERROR: Invalid JSON in configuration registry", "ERROR")

    def format_data_sources(self, data_sources: List[Dict[str, Any]]) -> str:
        """Format data sources list for display.

        Args:
            data_sources: List of data source dictionaries

        Returns:
            Formatted data sources display
        """
        if not data_sources:
            return self.colorize("No data sources found.", "caution")

        if not prettytable:
            # Fallback to simple text format
            # Sort data sources by DSRC_ID
            sorted_data_sources = sorted(data_sources, key=lambda x: x.get('DSRC_ID', 0))

            output = self.colorize("\nData Sources:\n", "highlight2")
            for ds in sorted_data_sources:
                dsrc_id = ds.get('DSRC_ID', 'Unknown')
                dsrc_code = ds.get('DSRC_CODE', 'Unknown')
                output += f"ID: {dsrc_id}, Code: {dsrc_code}\n"
            return output

        # Use prettytable for better formatting
        try:
            # Sort data sources by DSRC_ID
            sorted_data_sources = sorted(data_sources, key=lambda x: x.get('DSRC_ID', 0))

            table = prettytable.PrettyTable()
            table.field_names = ["ID", "Code"]
            table.align = "l"

            for ds in sorted_data_sources:
                table.add_row([
                    ds.get('DSRC_ID', 'Unknown'),
                    ds.get('DSRC_CODE', 'Unknown')
                ])

            header = self.colorize("\nData Sources:", "highlight2")
            return f"{header}\n{table}\n"
        except Exception:
            # Fallback to simple text format if prettytable fails
            # Sort data sources by DSRC_ID
            sorted_data_sources = sorted(data_sources, key=lambda x: x.get('DSRC_ID', 0))

            output = self.colorize("\nData Sources:\n", "highlight2")
            for ds in sorted_data_sources:
                dsrc_id = ds.get('DSRC_ID', 'Unknown')
                dsrc_code = ds.get('DSRC_CODE', 'Unknown')
                output += f"ID: {dsrc_id}, Code: {dsrc_code}\n"
            return output

    def format_help_topic(self, topic: str, content: str) -> str:
        """Format help content for a topic.

        Args:
            topic: Help topic name
            content: Help content text

        Returns:
            Formatted help display
        """
        header = self.colorize(f"\n{topic.upper()}:", "highlight2")
        return f"{header}\n{content}\n"

    def format_error(self, error_message: str, context: str = "") -> str:
        """Format error message for display.

        Args:
            error_message: Error message text
            context: Optional context information

        Returns:
            Formatted error message
        """
        formatted_error = self.format_message(f"Error: {error_message}", "ERROR")
        if context:
            formatted_error += self.colorize(f"Context: {context}\n", "caution")
        return formatted_error

    def format_success(self, message: str) -> str:
        """Format success message for display.

        Args:
            message: Success message text

        Returns:
            Formatted success message
        """
        return self.format_message(f"Success: {message}", "SUCCESS")

    def format_warning(self, message: str) -> str:
        """Format warning message for display.

        Args:
            message: Warning message text

        Returns:
            Formatted warning message
        """
        return self.format_message(f"Warning: {message}", "WARNING")

    def format_info(self, message: str) -> str:
        """Format info message for display.

        Args:
            message: Info message text

        Returns:
            Formatted info message
        """
        return self.format_message(f"Info: {message}", "INFO")

    def format_json_data(self, data: Dict[str, Any]) -> str:
        """Format JSON data for display."""
        try:
            import json
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            return self.format_json(json_str, pretty=True)
        except Exception:
            return str(data)

    def format_jsonl_data(self, data: List[Dict[str, Any]]) -> str:
        """Format data as JSON Lines (JSONL) for display."""
        if not data:
            return ""

        try:
            import json
            lines = []
            for item in data:
                lines.append(json.dumps(item, ensure_ascii=False, separators=(',', ':')))
            return '\n'.join(lines)
        except Exception:
            return str(data)

    def _convert_ftype_id_to_code(self, record: Dict[str, Any], ftype_lookup: Dict[int, str] = None) -> str:
        """Convert FTYPE_ID to FTYPE_CODE with 0 mapping to 'ALL'.

        Args:
            record: Record containing FTYPE_ID
            ftype_lookup: Optional lookup dictionary for FTYPE_ID -> FTYPE_CODE mapping

        Returns:
            FTYPE_CODE string or 'ALL' for FTYPE_ID 0
        """
        ftype_id = record.get('FTYPE_ID', 0)

        if ftype_id == 0:
            return 'ALL'

        # If we have FTYPE_CODE already in the record, use it
        if 'FTYPE_CODE' in record:
            return record['FTYPE_CODE']

        # If we have a lookup dictionary, use it
        if ftype_lookup and ftype_id in ftype_lookup:
            return ftype_lookup[ftype_id]

        # Fallback to showing the ID
        return str(ftype_id)

    def _build_ftype_lookup(self, config_manager) -> Dict[int, str]:
        """Build a lookup dictionary from FTYPE_ID to FTYPE_CODE.

        Args:
            config_manager: ConfigurationManager instance

        Returns:
            Dictionary mapping FTYPE_ID to FTYPE_CODE
        """
        try:
            features = config_manager.get_features()
            return {feature.get('FTYPE_ID', 0): feature.get('FTYPE_CODE', str(feature.get('FTYPE_ID', 0)))
                   for feature in features}
        except Exception:
            return {}

    def format_feature_list(self, features: List[Dict[str, Any]], config_manager=None) -> str:
        """Format a list of features for display with comprehensive details."""
        if not features:
            return "No features found"

        try:
            # Handle non-iterable objects (like Mock objects in tests)
            if not hasattr(features, '__iter__') or isinstance(features, str):
                return "No features found"

            # Sort features by FTYPE_ID
            sorted_features = sorted(features, key=lambda x: x.get('FTYPE_ID', 0))

            # If config_manager provided, get detailed formatting
            if config_manager:
                return self._format_features_detailed(sorted_features, config_manager)

            # Fallback to basic formatting
            return self._format_features_basic(sorted_features)
        except Exception as e:
            return f"Error formatting features: {e}"

    def _format_features_basic(self, features: List[Dict[str, Any]]) -> str:
        """Basic feature formatting (fallback)."""
        table_data = []
        for feature in features:
            table_data.append({
                "ID": str(feature.get('FTYPE_ID', '')),
                "Code": feature.get('FTYPE_CODE', ''),
                "Description": feature.get('FTYPE_DESC', '')
            })
        return self.format_table_data(table_data)

    def _format_features_detailed(self, features: List[Dict[str, Any]], config_manager) -> str:
        """Detailed feature formatting with lookups as table columns."""
        table_data = []

        for feature in features:
            # Build comprehensive feature info like the original
            feature_info = self._build_feature_info(feature, config_manager)

            # Create element list as JSON structure (non-derived elements only)
            element_summary = ""
            if feature_info['elementList']:
                element_list = []
                for element in feature_info['elementList']:
                    # Skip derived elements
                    if element.get('derived') == 'Yes':
                        continue

                    element_dict = {
                        "element": element.get('element', ''),
                        "expressed": element.get('expressed', ''),
                        "compared": element.get('compared', ''),
                        "display": element.get('display', '')
                    }
                    element_list.append(element_dict)

                if element_list:
                    import json
                    try:
                        element_summary = json.dumps(element_list)
                    except (TypeError, ValueError):
                        # Handle Mock objects and other non-serializable objects in tests
                        element_summary = str(element_list)

            # Build table row with all feature information
            feature_row = {
                "ID": str(feature_info['id']),
                "Feature": feature_info['feature'],
                "Class": feature_info['class'],
                "Behavior": feature_info['behavior'],
                "Anonymize": feature_info['anonymize'],
                "Candidates": feature_info['candidates'],
                "Scoring": feature.get('USED_FOR_SCORING', ''),
                "Match Key": feature_info['matchKey'],
                "Version": str(feature_info['version']),
                "Standardize": feature_info['standardize'],
                "Expression": feature_info['expression'],
                "Comparison": feature_info['comparison'],
                "Elements": element_summary
            }

            table_data.append(feature_row)

        return self.format_table_data(table_data)

    def _build_feature_info(self, feature: Dict[str, Any], config_manager) -> Dict[str, Any]:
        """Build comprehensive feature info with lookups - mimics original format_feature_json."""
        try:
            ftype_id = feature.get('FTYPE_ID')

            # Get feature class
            fclass_record = None
            if feature.get('FCLASS_ID'):
                fclass_record = config_manager.get_record('CFG_FCLASS', 'FCLASS_ID', feature['FCLASS_ID'])

            # Get function calls for this feature
            sfcall_records = config_manager.get_record_list('CFG_SFCALL', 'FTYPE_ID', ftype_id) or []
            efcall_records = config_manager.get_record_list('CFG_EFCALL', 'FTYPE_ID', ftype_id) or []
            cfcall_records = config_manager.get_record_list('CFG_CFCALL', 'FTYPE_ID', ftype_id) or []

            # Get first call of each type (sorted by exec order)
            sfcall_record = sorted(sfcall_records, key=lambda k: k.get("EXEC_ORDER", 0))[0] if sfcall_records else {}
            efcall_record = sorted(efcall_records, key=lambda k: k.get("EXEC_ORDER", 0))[0] if efcall_records else {}
            cfcall_record = sorted(cfcall_records, key=lambda k: k.get("CFCALL_ID", 0))[0] if cfcall_records else {}

            # Get function details
            sfunc_record = {}
            if sfcall_record and sfcall_record.get('SFUNC_ID'):
                sfunc_record = config_manager.get_record('CFG_SFUNC', 'SFUNC_ID', sfcall_record['SFUNC_ID']) or {}

            efunc_record = {}
            if efcall_record and efcall_record.get('EFUNC_ID'):
                efunc_record = config_manager.get_record('CFG_EFUNC', 'EFUNC_ID', efcall_record['EFUNC_ID']) or {}

            cfunc_record = {}
            if cfcall_record and cfcall_record.get('CFUNC_ID'):
                cfunc_record = config_manager.get_record('CFG_CFUNC', 'CFUNC_ID', cfcall_record['CFUNC_ID']) or {}

            # Build behavior string
            behavior = self._get_feature_behavior(feature)

            # Build basic feature info
            feature_info = {
                'id': feature.get('FTYPE_ID', ''),
                'feature': feature.get('FTYPE_CODE', ''),
                'class': fclass_record.get('FCLASS_CODE', 'OTHER') if fclass_record else 'OTHER',
                'behavior': behavior,
                'anonymize': feature.get('ANONYMIZE', ''),
                'candidates': feature.get('USED_FOR_CAND', ''),
                'standardize': sfunc_record.get('SFUNC_CODE', '') if sfunc_record else '',
                'expression': efunc_record.get('EFUNC_CODE', '') if efunc_record else '',
                'comparison': cfunc_record.get('CFUNC_CODE', '') if cfunc_record else '',
                'matchKey': feature.get('SHOW_IN_MATCH_KEY', ''),
                'version': feature.get('VERSION', ''),
                'elementList': []
            }

            # Get element list
            feature_info['elementList'] = self._get_feature_elements(feature, config_manager, efcall_record, cfcall_record)

            return feature_info

        except Exception as e:
            # Return basic info on error
            return {
                'id': feature.get('FTYPE_ID', ''),
                'feature': feature.get('FTYPE_CODE', ''),
                'class': 'ERROR',
                'behavior': str(e),
                'anonymize': feature.get('ANONYMIZE', ''),
                'candidates': feature.get('USED_FOR_CAND', ''),
                'standardize': '',
                'expression': '',
                'comparison': '',
                'matchKey': feature.get('SHOW_IN_MATCH_KEY', ''),
                'version': feature.get('VERSION', ''),
                'elementList': []
            }

    def _get_feature_behavior(self, feature: Dict[str, Any]) -> str:
        """Get feature behavior string - mimics original getFeatureBehavior."""
        behavior = feature.get('FTYPE_FREQ', '')
        if str(feature.get('FTYPE_EXCL', '')).upper() in ('1', 'Y', 'YES'):
            behavior += 'E'
        if str(feature.get('FTYPE_STAB', '')).upper() in ('1', 'Y', 'YES'):
            behavior += 'S'
        return behavior

    def _get_feature_elements(self, feature: Dict[str, Any], config_manager, efcall_record: Dict, cfcall_record: Dict) -> List[Dict[str, Any]]:
        """Get detailed element list for a feature."""
        try:
            element_list = []
            ftype_id = feature.get('FTYPE_ID')

            # Get feature elements (FBOM records)
            fbom_records = config_manager.get_record_list('CFG_FBOM', 'FTYPE_ID', ftype_id) or []

            for fbom_record in sorted(fbom_records, key=lambda k: k.get('EXEC_ORDER', 0)):
                # Get element details
                felem_record = config_manager.get_record('CFG_FELEM', 'FELEM_ID', fbom_record.get('FELEM_ID'))
                if not felem_record:
                    element_list.append({
                        'element': f"ERROR: FELEM_ID {fbom_record.get('FELEM_ID')}",
                        'expressed': 'No',
                        'compared': 'No',
                        'derived': 'No',
                        'display': 'No'
                    })
                    continue

                # Check if element is expressed (has EFBOM record)
                expressed = 'No'
                if efcall_record:
                    efbom_record = config_manager.get_record_by_fields('CFG_EFBOM', {
                        'EFCALL_ID': efcall_record.get('EFCALL_ID'),
                        'FTYPE_ID': fbom_record.get('FTYPE_ID'),
                        'FELEM_ID': fbom_record.get('FELEM_ID')
                    })
                    if efbom_record:
                        expressed = 'Yes'

                # Check if element is compared (has CFBOM record)
                compared = 'No'
                if cfcall_record:
                    cfbom_record = config_manager.get_record_by_fields('CFG_CFBOM', {
                        'CFCALL_ID': cfcall_record.get('CFCALL_ID'),
                        'FTYPE_ID': fbom_record.get('FTYPE_ID'),
                        'FELEM_ID': fbom_record.get('FELEM_ID')
                    })
                    if cfbom_record:
                        compared = 'Yes'

                element_list.append({
                    'element': felem_record.get('FELEM_CODE', ''),
                    'expressed': expressed,
                    'compared': compared,
                    'derived': fbom_record.get('DERIVED', 'No'),
                    'display': 'Yes' if fbom_record.get('DISPLAY_LEVEL', 0) != 0 else 'No'
                })

            return element_list
        except Exception:
            return []

    def format_attribute_list(self, attributes: List[Dict[str, Any]], ftype_lookup: Dict[int, str] = None) -> str:
        """Format a list of attributes for display."""
        if not attributes:
            return "No attributes found"

        try:
            # Sort attributes by ATTR_ID
            sorted_attributes = sorted(attributes, key=lambda x: x.get('ATTR_ID', 0))

            # Convert to simplified format for table display
            table_data = []
            for attr in sorted_attributes:
                table_data.append({
                    "ID": str(attr.get('ATTR_ID', '')),
                    "Attribute": attr.get('ATTR_CODE', ''),
                    "Class": attr.get('ATTR_CLASS', ''),
                    "Feature": self._convert_ftype_id_to_code(attr, ftype_lookup),
                    "Element": attr.get('FELEM_CODE', '') or "None",
                    "Required": attr.get('FELEM_REQ', ''),
                    "Default": attr.get('DEFAULT_VALUE', ''),
                    "Internal": attr.get('INTERNAL', '')
                })

            return self.format_table_data(table_data)
        except Exception:
            return self.format_table_data(attributes)

    def format_element_list(self, elements: List[Dict[str, Any]]) -> str:
        """Format a list of elements for display."""
        if not elements:
            return "No elements found"

        try:
            # Sort elements by FELEM_ID (to match original sorting by FELEM_CODE)
            sorted_elements = sorted(elements, key=lambda x: x.get('FELEM_CODE', ''))

            # Convert to table format to match original format_element_json
            table_data = []
            for element in sorted_elements:
                table_data.append({
                    "ID": str(element.get('FELEM_ID', '')),
                    "Element": element.get('FELEM_CODE', ''),
                    "Data Type": element.get('DATA_TYPE', '')
                })

            return self.format_table_data(table_data)
        except Exception:
            return self.format_table_data(elements)

    def format_table_data(self, data: List[Dict[str, Any]]) -> str:
        """Format generic table data for display."""
        if not data:
            return "No data found"

        try:
            if self._prettytable_available:
                import prettytable
                table = prettytable.PrettyTable()
                if data:
                    # Color headers like the original
                    headers = list(data[0].keys())
                    colored_headers = [self.colorize(header, "attr_color") for header in headers]
                    table.field_names = colored_headers

                    row_count = 0
                    for row in data:
                        row_count += 1
                        table_row = []
                        for field in headers:
                            attr_value = (
                                json.dumps(row[field])
                                if isinstance(row[field], (list, dict))
                                else str(row.get(field, ''))
                            )
                            # Color data like the original
                            colored_value = self.colorize(attr_value, "dim")
                            table_row.append(colored_value)
                        table.add_row(table_row)

                    # Format like the original
                    table.align = "l"
                    if hasattr(prettytable, "TableStyle"):
                        table.set_style(prettytable.TableStyle.SINGLE_BORDER)
                    else:
                        table.set_style(prettytable.SINGLE_BORDER)
                    table.hrules = 1
                    return table.get_string()
        except Exception:
            # Fallback to simple formatting if prettytable fails
            if not data:
                return "No data to display"
            else:
                # Fall back to simple formatting
                if not data:
                    return "No data"

                headers = list(data[0].keys())
                rows = [headers]
                rows.append(["-" * len(h) for h in headers])

                for row in data:
                    rows.append([str(row.get(field, '')) for field in headers])

                return self._format_table_rows(rows)

    def format_threshold_list(self, thresholds: List[Dict[str, Any]], ftype_lookup: Dict[int, str] = None) -> str:
        """Format a list of thresholds for display."""
        if not thresholds:
            return "No thresholds found"

        try:
            # Sort thresholds by GPLAN_ID for consistent ordering
            sorted_thresholds = sorted(thresholds, key=lambda x: x.get('GPLAN_ID', 0))
            table_data = []
            for threshold in sorted_thresholds:
                # Use CFG_GENERIC_THRESHOLD field names
                threshold_data = {
                    "ID": str(threshold.get('GPLAN_ID', '')),
                    "Behavior": threshold.get('BEHAVIOR', ''),
                    "Feature Type": self._convert_ftype_id_to_code(threshold, ftype_lookup),
                    "Candidate Cap": str(threshold.get('CANDIDATE_CAP', '')),
                    "Scoring Cap": str(threshold.get('SCORING_CAP', '')),
                    "Send To Redo": threshold.get('SEND_TO_REDO', '')
                }
                table_data.append(threshold_data)

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting thresholds: {e}"

    def format_generic_plan_list(self, plans: List[Dict[str, Any]], ftype_lookup: Dict[int, str] = None) -> str:
        """Format a list of generic plans for display."""
        if not plans:
            return "No generic plans found"

        try:
            table_data = []
            for plan in plans:
                plan_data = {
                    "ID": str(plan.get('GBOM_ID', '')),
                    "Feature": self._convert_ftype_id_to_code(plan, ftype_lookup),
                    "Element": plan.get('FELEM_CODE', ''),
                    "Function": plan.get('FUNC_CODE', ''),
                    "Score": str(plan.get('FELEM_SCORE', '')),
                    "Frequency": str(plan.get('FELEM_FREQ', ''))
                }
                table_data.append(plan_data)

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting generic plans: {e}"

    def set_paging_enabled(self, enabled: bool) -> None:
        """Enable or disable automatic paging."""
        self._enable_paging = enabled

    def format_rule_list(self, rules: List[Dict[str, Any]]) -> str:
        """Format a list of rules for display."""
        if not rules:
            return "No rules found"

        try:
            # Sort rules by ID for consistent ordering
            sorted_rules = sorted(rules, key=lambda x: x.get('ERRULE_ID', 0))
            table_data = []
            for rule in sorted_rules:
                rule_data = {
                    "ID": str(rule.get('ERRULE_ID', '')),
                    "Code": rule.get('ERRULE_CODE', ''),
                    "Tier": str(rule.get('ERRULE_TIER', '')),
                    "Resolve": rule.get('RESOLVE', ''),
                    "Relate": rule.get('RELATE', ''),
                    "Qual Fragment": rule.get('QUAL_ERFRAG_CODE', ''),
                    "Disq Fragment": rule.get('DISQ_ERFRAG_CODE', '') or 'None'
                }
                table_data.append(rule_data)

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting rules: {e}"

    def format_fragment_list(self, fragments: List[Dict[str, Any]]) -> str:
        """Format a list of fragments for display."""
        if not fragments:
            return "No fragments found"

        try:
            # Sort fragments by ID for consistent ordering
            sorted_fragments = sorted(fragments, key=lambda x: x.get('ERFRAG_ID', 0))
            table_data = []
            for fragment in sorted_fragments:
                fragment_data = {
                    "ID": str(fragment.get('ERFRAG_ID', '')),
                    "Code": fragment.get('ERFRAG_CODE', ''),
                    "Description": fragment.get('ERFRAG_DESC', ''),
                    "Source": fragment.get('ERFRAG_SOURCE', '') or 'None',
                    "Depends": fragment.get('ERFRAG_DEPENDS', '') or 'None'
                }
                table_data.append(fragment_data)

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting fragments: {e}"

    def format_function_list(self, functions: List[Dict[str, Any]]) -> str:
        """Format a list of functions for display."""
        if not functions:
            return "No functions found"

        try:
            # Sort functions by CFUNC_ID
            sorted_functions = sorted(functions, key=lambda x: x.get('CFUNC_ID', 0))

            table_data = []
            for func in sorted_functions:
                table_data.append({
                    "ID": str(func.get('CFUNC_ID', '')),
                    "Function": func.get('CFUNC_FUNC', ''),
                    "Language": func.get('CFUNC_LANG', '') or "None",
                    "Version": str(func.get('VERSION', '') or 1)
                })

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting functions: {e}"

    def format_call_list(self, calls: List[Dict[str, Any]], ftype_lookup: Dict[int, str] = None) -> str:
        """Format a list of calls for display."""
        if not calls:
            return "No calls found"

        try:
            # Handle non-iterable objects (like Mock objects in tests)
            if not hasattr(calls, '__iter__') or isinstance(calls, str):
                return "No calls found"

            # Sort calls by their ID field (whichever is available)
            def get_call_id(call):
                return call.get('CFCALL_ID') or call.get('ERFRAG_ID') or call.get('SFCALL_ID') or call.get('DFCALL_ID', 0)

            sorted_calls = sorted(calls, key=get_call_id)

            table_data = []
            for call in sorted_calls:
                # Handle different call types with flexible field mapping
                call_data = {
                    "ID": str(call.get('CFCALL_ID') or call.get('ERFRAG_ID') or call.get('SFCALL_ID') or call.get('DFCALL_ID', '')),
                    "Function": call.get('CFUNC_CODE') or call.get('EFUNC_CODE') or call.get('SFUNC_CODE') or call.get('DFUNC_CODE', ''),
                    "Feature": self._convert_ftype_id_to_code(call, ftype_lookup),
                    "Element": call.get('FELEM_CODE', ''),
                    "Exec Order": str(call.get('EXEC_ORDER', ''))
                }
                table_data.append(call_data)

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting calls: {e}"

    def format_call_details(self, call: Dict[str, Any]) -> str:
        """Format call details for display."""
        if not self._prettytable_available:
            lines = ["Call Details:"]
            for key, value in call.items():
                lines.append(f"  {key}: {value}")
            return '\n'.join(lines)

        table = prettytable.PrettyTable()
        table.field_names = [self.colorize("Property", "attr_color"), self.colorize("Value", "attr_color")]
        table.align = "l"
        table.set_style(prettytable.TableStyle.SINGLE_BORDER)
        table.hrules = 1

        for key, value in call.items():
            # Format key to be more readable
            formatted_key = key.replace('_', ' ').title()
            formatted_value = str(value) if value is not None else ""
            table.add_row([formatted_key, formatted_value])

        return table.get_string()

    def format_rule_details(self, rule: Dict[str, Any]) -> str:
        """Format rule details for display."""
        if not self._prettytable_available:
            lines = ["Rule Details:"]
            for key, value in rule.items():
                lines.append(f"  {key}: {value}")
            return '\n'.join(lines)

        table = prettytable.PrettyTable()
        table.field_names = [self.colorize("Property", "attr_color"), self.colorize("Value", "attr_color")]
        table.align = "l"
        table.set_style(prettytable.TableStyle.SINGLE_BORDER)
        table.hrules = 1

        for key, value in rule.items():
            # Format key to be more readable
            formatted_key = key.replace('_', ' ').title()
            formatted_value = str(value) if value is not None else ""
            table.add_row([formatted_key, formatted_value])

        return table.get_string()

    def format_fragment_details(self, fragment: Dict[str, Any]) -> str:
        """Format fragment details for display."""
        if not self._prettytable_available:
            lines = ["Fragment Details:"]
            for key, value in fragment.items():
                lines.append(f"  {key}: {value}")
            return '\n'.join(lines)

        table = prettytable.PrettyTable()
        table.field_names = [self.colorize("Property", "attr_color"), self.colorize("Value", "attr_color")]
        table.align = "l"
        table.set_style(prettytable.TableStyle.SINGLE_BORDER)
        table.hrules = 1

        for key, value in fragment.items():
            # Format key to be more readable
            formatted_key = key.replace('_', ' ').title()
            formatted_value = str(value) if value is not None else ""
            table.add_row([formatted_key, formatted_value])

        return table.get_string()

    def format_behavior_override_list(self, overrides: List[Dict[str, Any]], ftype_lookup: Dict[int, str] = None) -> str:
        """Format a list of behavior overrides for display."""
        if not overrides:
            return "No behavior overrides found"

        try:
            # Sort overrides by BFRULE_ID
            sorted_overrides = sorted(overrides, key=lambda x: x.get('BFRULE_ID', 0))

            table_data = []
            for override in sorted_overrides:
                override_data = {
                    "ID": str(override.get('BFRULE_ID', '')),
                    "Feature": self._convert_ftype_id_to_code(override, ftype_lookup),
                    "Behavior": override.get('BEHAVIOR', ''),
                    "Exec Order": str(override.get('EXEC_ORDER', '')),
                    "Description": override.get('DESCRIPTION', '')
                }
                table_data.append(override_data)

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting behavior overrides: {e}"

    def format_reference_code_list(self, codes: List[Dict[str, Any]]) -> str:
        """Format a list of reference codes for display."""
        if not codes:
            return "No reference codes found"

        try:
            # Sort reference codes by RCLASS_ID
            sorted_codes = sorted(codes, key=lambda x: x.get('RCLASS_ID', 0))

            table_data = []
            for code in sorted_codes:
                code_data = {
                    "ID": str(code.get('RCLASS_ID', '')),
                    "Code": code.get('RCLASS_CODE', ''),
                    "Description": code.get('RCLASS_DESC', ''),
                    "Is Default": str(code.get('IS_DEFAULT', '')),
                    "Order": str(code.get('RCLASS_ORDER', ''))
                }
                table_data.append(code_data)

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting reference codes: {e}"

    def format_system_parameter_list(self, parameters: List[Dict[str, Any]]) -> str:
        """Format a list of system parameters for display."""
        if not parameters:
            return "No system parameters found"

        try:
            # Handle non-iterable objects (like Mock objects in tests)
            if not hasattr(parameters, '__iter__') or isinstance(parameters, str):
                return "No system parameters found"

            # Sort system parameters by OOM_ID
            sorted_parameters = sorted(parameters, key=lambda x: x.get('OOM_ID', 0))

            table_data = []
            for param in sorted_parameters:
                param_data = {
                    "ID": str(param.get('OOM_ID', '')),
                    "Type": param.get('OOM_TYPE', ''),
                    "Level": param.get('OOM_LEVEL', ''),
                    "Value": str(param.get('OOM_VALUE', '')),
                    "Description": param.get('OOM_DESC', '')
                }
                table_data.append(param_data)

            return self.format_table_data(table_data)
        except Exception as e:
            return f"Error formatting system parameters: {e}"

    def format_config_section_details(self, section: Dict[str, Any]) -> str:
        """Format configuration section details for display."""
        if not self._prettytable_available:
            lines = ["Configuration Section Details:"]
            for key, value in section.items():
                lines.append(f"  {key}: {value}")
            return '\n'.join(lines)

        table = prettytable.PrettyTable()
        table.field_names = [self.colorize("Property", "attr_color"), self.colorize("Value", "attr_color")]
        table.align = "l"
        table.set_style(prettytable.TableStyle.SINGLE_BORDER)
        table.hrules = 1

        for key, value in section.items():
            # Format key to be more readable
            formatted_key = key.replace('_', ' ').title()
            formatted_value = str(value) if value is not None else ""
            table.add_row([formatted_key, formatted_value])

        return table.get_string()

    def print_with_paging(self, text: str, max_lines: int = None) -> None:
        """Print text with automatic paging supporting horizontal scrolling.

        Args:
            text: Text to display
            max_lines: Maximum lines before paging (auto-detect if None)
        """
        if not text:
            return

        # In test mode or paging disabled, just print all
        if not self._enable_paging or hasattr(sys, '_called_from_test'):
            print(text)
            return

        # Try to use a better pager if available
        if self._use_external_pager(text):
            return

        # Fallback to internal paging with horizontal scrolling support
        self._internal_pager(text, max_lines)

    def _use_external_pager(self, text: str) -> bool:
        """Try to use external pager (less) for better horizontal scrolling.

        Args:
            text: Text to display

        Returns:
            True if external pager was used, False otherwise
        """
        try:
            import subprocess
            import shutil

            # Check if less is available
            if shutil.which('less'):
                # Use less with horizontal scrolling support
                process = subprocess.Popen(
                    ['less', '-S', '-R'],  # -S: no line wrapping, -R: color support
                    stdin=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=text)
                return True
        except (ImportError, OSError, subprocess.SubprocessError):
            pass

        return False

    def _internal_pager(self, text: str, max_lines: int = None) -> None:
        """Internal pager with basic horizontal scrolling simulation.

        Args:
            text: Text to display
            max_lines: Maximum lines before paging
        """
        lines = text.split('\n')

        # Auto-detect terminal size
        try:
            import shutil
            terminal_size = shutil.get_terminal_size()
            if max_lines is None:
                max_lines = terminal_size.lines - 3
            terminal_width = terminal_size.columns
        except (ValueError, OSError):
            max_lines = max_lines or 20
            terminal_width = 120  # Fallback width

        # If content fits on screen, print normally
        if len(lines) <= max_lines:
            # Check for wide lines that need horizontal handling
            needs_horizontal_handling = any(len(line.encode('utf-8', 'ignore')) > terminal_width for line in lines)
            if needs_horizontal_handling:
                self._print_wide_content(lines, terminal_width)
            else:
                print(text)
            return

        # Interactive paging with horizontal scrolling
        current_line = 0
        horizontal_offset = 0

        while current_line < len(lines):
            # Clear screen for better experience
            if current_line > 0:
                print("\033[2J\033[H", end="")  # Clear screen and move cursor to top

            # Show current page with horizontal offset
            end_line = min(current_line + max_lines, len(lines))
            displayed_lines = []

            for i in range(current_line, end_line):
                line = lines[i]
                # Apply horizontal offset
                if horizontal_offset > 0 and len(line) > horizontal_offset:
                    displayed_line = line[horizontal_offset:]
                else:
                    displayed_line = line

                # Truncate to terminal width if still too long
                if len(displayed_line.encode('utf-8', 'ignore')) > terminal_width:
                    # Find safe truncation point
                    truncated = displayed_line[:terminal_width-3] + "..."
                    displayed_lines.append(truncated)
                else:
                    displayed_lines.append(displayed_line)

            for line in displayed_lines:
                print(line)

            # Show status and prompt
            remaining_lines = len(lines) - end_line
            total_lines = len(lines)
            current_range = f"{current_line + 1}-{end_line}"

            status = f"Lines {current_range} of {total_lines}"
            if horizontal_offset > 0:
                status += f" (offset: {horizontal_offset} chars)"
            if remaining_lines > 0:
                status += f" ({remaining_lines} more lines)"

            prompt = f"\n{status}\n"
            prompt += "[Enter=next, b=back, q=quit, a=all, →/←=scroll left/right]: "

            try:
                response = input(self.colorize(prompt, "highlight2")).strip().lower()

                if response in ('q', 'quit'):
                    break
                elif response in ('a', 'all'):
                    # Show everything remaining without paging
                    for i in range(end_line, len(lines)):
                        print(lines[i])
                    break
                elif response in ('b', 'back'):
                    # Go back one page
                    current_line = max(0, current_line - max_lines)
                elif response in ('→', 'right', '>'):
                    # Scroll right
                    horizontal_offset += 20
                elif response in ('←', 'left', '<'):
                    # Scroll left
                    horizontal_offset = max(0, horizontal_offset - 20)
                else:
                    # Default: next page (Enter or any other key)
                    current_line = end_line
                    horizontal_offset = 0  # Reset horizontal offset when moving to next page

                # If we've shown everything, we're done
                if current_line >= len(lines):
                    break

            except (EOFError, KeyboardInterrupt):
                break

    def _print_wide_content(self, lines: list, terminal_width: int) -> None:
        """Print wide content with truncation indicators.

        Args:
            lines: List of lines to print
            terminal_width: Terminal width
        """
        for line in lines:
            if len(line.encode('utf-8', 'ignore')) > terminal_width:
                truncated = line[:terminal_width-10] + " [...more]"
                print(truncated)
            else:
                print(line)