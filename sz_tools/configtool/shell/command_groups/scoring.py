"""Scoring and threshold management commands."""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import BaseShell


class ScoringCommands:
    """Mixin class for scoring and threshold related commands."""

    def do_listThresholds(self, arg: str) -> None:
        """List all thresholds in the configuration.

        Syntax:
            listThresholds [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            thresholds = self.config_manager.get_thresholds()
            if not thresholds:
                print(self.display_formatter.format_info("No thresholds found"))
                return

            # Apply filter if provided
            if filter_expression:
                thresholds = self.config_manager.apply_filter(thresholds, filter_expression)

            if not thresholds:
                print(self.display_formatter.format_info("No matching thresholds found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_threshold_list(thresholds)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for threshold in thresholds:
                    lines.append(self.display_formatter.format_json(json.dumps(threshold), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(thresholds, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list thresholds: {e}"))

    def do_getThreshold(self, arg: str) -> None:
        """Get details of a specific threshold.

        Syntax:
            getThreshold <threshold_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Threshold ID is required"
            ))
            return

        try:
            threshold_id = int(cleaned_arg.strip())
            threshold_record = self.config_manager.get_record('CFG_THRESH', 'THRESH_ID', threshold_id)
            if not threshold_record:
                print(self.display_formatter.format_error(f"Threshold not found"))
                return

            # Transform raw database record to user-friendly JSON format
            threshold = self.config_manager.format_threshold_json(threshold_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_threshold_details(threshold)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(threshold, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Threshold ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get threshold: {e}"))

    def do_setThreshold(self, arg: str) -> None:
        """Set threshold values.

        Syntax:
            setThreshold <threshold_type> <value>
        """
        parts = arg.strip().split(None, 1)
        if len(parts) < 2:
            print(self.display_formatter.format_error(
                "Threshold type and value are required"
            ))
            return

        threshold_type = parts[0]
        try:
            value = float(parts[1])
        except ValueError:
            print(self.display_formatter.format_error(
                "Threshold value must be a number"
            ))
            return

        try:
            if self.config_manager.set_threshold(threshold_type, value):
                print(self.display_formatter.format_success(
                    f"Successfully set {threshold_type} threshold to {value}"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to set {threshold_type} threshold"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set threshold: {e}"))

    def do_listScoringSets(self, arg: str) -> None:
        """List all scoring sets.

        Syntax:
            listScoringSets [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            scoring_sets = self.config_manager.get_scoring_sets()
            if not scoring_sets:
                print(self.display_formatter.format_info("No scoring sets found"))
                return

            # Apply filter if provided
            if filter_expression:
                scoring_sets = self.config_manager.apply_filter(scoring_sets, filter_expression)

            if not scoring_sets:
                print(self.display_formatter.format_info("No matching scoring sets found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_scoring_set_list(scoring_sets)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for scoring_set in scoring_sets:
                    lines.append(self.display_formatter.format_json(json.dumps(scoring_set), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(scoring_sets, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list scoring sets: {e}"))

    def do_getScoringSet(self, arg: str) -> None:
        """Get details of a specific scoring set.

        Syntax:
            getScoringSet <scoring_set_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Scoring set ID is required"
            ))
            return

        try:
            scoring_set_id = int(cleaned_arg.strip())
            scoring_set_record = self.config_manager.get_record('CFG_SSET', 'SSET_ID', scoring_set_id)
            if not scoring_set_record:
                print(self.display_formatter.format_error(f"Scoring set not found"))
                return

            # Transform raw database record to user-friendly JSON format
            scoring_set = self.config_manager.format_scoring_set_json(scoring_set_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_scoring_set_details(scoring_set)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(scoring_set, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Scoring set ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get scoring set: {e}"))

    def do_addScoringSet(self, arg: str) -> None:
        """Add a scoring set.

        Syntax:
            addScoringSet <scoring_set_json>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Scoring set JSON is required"
            ))
            return

        try:
            scoring_set_config = json.loads(arg.strip())
            if self.config_manager.add_scoring_set(scoring_set_config):
                print(self.display_formatter.format_success(
                    "Scoring set added successfully"
                ))
            else:
                print(self.display_formatter.format_error(
                    "Failed to add scoring set"
                ))
        except json.JSONDecodeError as e:
            print(self.display_formatter.format_error(
                f"Invalid JSON configuration: {e}"
            ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add scoring set: {e}"))

    def do_deleteScoringSet(self, arg: str) -> None:
        """Delete a scoring set.

        Syntax:
            deleteScoringSet <scoring_set_id>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Scoring set ID is required"
            ))
            return

        try:
            scoring_set_id = int(arg.strip())
            if self.config_manager.delete_scoring_set(scoring_set_id):
                print(self.display_formatter.format_success(
                    f"Successfully deleted scoring set {scoring_set_id}"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete scoring set {scoring_set_id}"
                ))
        except ValueError:
            print(self.display_formatter.format_error("Scoring set ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete scoring set: {e}"))

    def do_listFragmentTypes(self, arg: str) -> None:
        """List all fragment types.

        Syntax:
            listFragmentTypes [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            fragment_types = self.config_manager.get_fragment_types()
            if not fragment_types:
                print(self.display_formatter.format_info("No fragment types found"))
                return

            # Apply filter if provided
            if filter_expression:
                fragment_types = self.config_manager.apply_filter(fragment_types, filter_expression)

            if not fragment_types:
                print(self.display_formatter.format_info("No matching fragment types found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_fragment_type_list(fragment_types)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for ftype in fragment_types:
                    lines.append(self.display_formatter.format_json(json.dumps(ftype), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(fragment_types, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list fragment types: {e}"))

    def do_getFragmentType(self, arg: str) -> None:
        """Get details of a specific fragment type.

        Syntax:
            getFragmentType <fragment_type_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Fragment type ID is required"
            ))
            return

        try:
            fragment_type_id = int(cleaned_arg.strip())
            fragment_type_record = self.config_manager.get_record('CFG_FRAGTYPE', 'FRAGTYPE_ID', fragment_type_id)
            if not fragment_type_record:
                print(self.display_formatter.format_error(f"Fragment type not found"))
                return

            # Transform raw database record to user-friendly JSON format
            fragment_type = self.config_manager.format_fragment_type_json(fragment_type_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_fragment_type_details(fragment_type)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(fragment_type, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Fragment type ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get fragment type: {e}"))

    def do_listMatchLevels(self, arg: str) -> None:
        """List all match levels.

        Syntax:
            listMatchLevels [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            match_levels = self.config_manager.get_match_levels()
            if not match_levels:
                print(self.display_formatter.format_info("No match levels found"))
                return

            # Apply filter if provided
            if filter_expression:
                match_levels = self.config_manager.apply_filter(match_levels, filter_expression)

            if not match_levels:
                print(self.display_formatter.format_info("No matching match levels found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_match_level_list(match_levels)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for level in match_levels:
                    lines.append(self.display_formatter.format_json(json.dumps(level), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(match_levels, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list match levels: {e}"))

    def do_getMatchLevel(self, arg: str) -> None:
        """Get details of a specific match level.

        Syntax:
            getMatchLevel <match_level_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Match level ID is required"
            ))
            return

        try:
            match_level_id = int(cleaned_arg.strip())
            match_level_record = self.config_manager.get_record('CFG_MLEVEL', 'MLEVEL_ID', match_level_id)
            if not match_level_record:
                print(self.display_formatter.format_error(f"Match level not found"))
                return

            # Transform raw database record to user-friendly JSON format
            match_level = self.config_manager.format_match_level_json(match_level_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_match_level_details(match_level)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(match_level, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Match level ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get match level: {e}"))

    def do_setMatchLevel(self, arg: str) -> None:
        """Set match level configuration.

        Syntax:
            setMatchLevel <level_config_json>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Match level configuration JSON is required"
            ))
            return

        try:
            level_config = json.loads(arg.strip())
            if self.config_manager.set_match_level(level_config):
                print(self.display_formatter.format_success(
                    "Match level configuration updated successfully"
                ))
            else:
                print(self.display_formatter.format_error(
                    "Failed to update match level configuration"
                ))
        except json.JSONDecodeError as e:
            print(self.display_formatter.format_error(
                f"Invalid JSON configuration: {e}"
            ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to set match level: {e}"))