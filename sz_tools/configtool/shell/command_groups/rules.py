"""Rules and validation management commands."""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import BaseShell


class RulesCommands:
    """Mixin class for rules and validation related commands."""

    def do_listGenericPlans(self, arg: str) -> None:
        """List all generic plans.

        Syntax:
            listGenericPlans [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            plans = self.config_manager.get_generic_plans()
            if not plans:
                print(self.display_formatter.format_info("No generic plans found"))
                return

            # Apply filter if provided
            if filter_expression:
                plans = self.config_manager.apply_filter(plans, filter_expression)

            if not plans:
                print(self.display_formatter.format_info("No matching generic plans found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_generic_plan_list(plans)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for plan in plans:
                    lines.append(self.display_formatter.format_json(json.dumps(plan), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(plans, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list generic plans: {e}"))

    def do_getGenericPlan(self, arg: str) -> None:
        """Get details of a specific generic plan.

        Syntax:
            getGenericPlan <plan_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Generic plan ID is required"
            ))
            return

        try:
            plan_id = int(cleaned_arg.strip())
            plan_record = self.config_manager.get_record('CFG_GPLAN', 'GPLAN_ID', plan_id)
            if not plan_record:
                print(self.display_formatter.format_error(f"Generic plan not found"))
                return

            # Transform raw database record to user-friendly JSON format
            plan = self.config_manager.format_generic_plan_json(plan_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_generic_plan_details(plan)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(plan, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Generic plan ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get generic plan: {e}"))

    def do_listBehaviorOverrides(self, arg: str) -> None:
        """List all behavior overrides.

        Syntax:
            listBehaviorOverrides [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            overrides = self.config_manager.get_behavior_overrides()
            if not overrides:
                print(self.display_formatter.format_info("No behavior overrides found"))
                return

            # Apply filter if provided
            if filter_expression:
                overrides = self.config_manager.apply_filter(overrides, filter_expression)

            if not overrides:
                print(self.display_formatter.format_info("No matching behavior overrides found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_behavior_override_list(overrides)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for override in overrides:
                    lines.append(self.display_formatter.format_json(json.dumps(override), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(overrides, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list behavior overrides: {e}"))

    def do_getBehaviorOverride(self, arg: str) -> None:
        """Get details of a specific behavior override.

        Syntax:
            getBehaviorOverride <override_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Behavior override ID is required"
            ))
            return

        try:
            override_id = int(cleaned_arg.strip())
            override_record = self.config_manager.get_record('CFG_BOVER', 'BOVER_ID', override_id)
            if not override_record:
                print(self.display_formatter.format_error(f"Behavior override not found"))
                return

            # Transform raw database record to user-friendly JSON format
            override = self.config_manager.format_behavior_override_json(override_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_behavior_override_details(override)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(override, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Behavior override ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get behavior override: {e}"))

    def do_addBehaviorOverride(self, arg: str) -> None:
        """Add a behavior override.

        Syntax:
            addBehaviorOverride <override_json>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Behavior override JSON is required"
            ))
            return

        try:
            override_config = json.loads(arg.strip())
            if self.config_manager.add_behavior_override(override_config):
                print(self.display_formatter.format_success(
                    "Behavior override added successfully"
                ))
            else:
                print(self.display_formatter.format_error(
                    "Failed to add behavior override"
                ))
        except json.JSONDecodeError as e:
            print(self.display_formatter.format_error(
                f"Invalid JSON configuration: {e}"
            ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add behavior override: {e}"))

    def do_deleteBehaviorOverride(self, arg: str) -> None:
        """Delete a behavior override.

        Syntax:
            deleteBehaviorOverride <override_id>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Behavior override ID is required"
            ))
            return

        try:
            override_id = int(arg.strip())
            if self.config_manager.delete_behavior_override(override_id):
                print(self.display_formatter.format_success(
                    f"Successfully deleted behavior override {override_id}"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete behavior override {override_id}"
                ))
        except ValueError:
            print(self.display_formatter.format_error("Behavior override ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete behavior override: {e}"))

    def do_listRuleTypes(self, arg: str) -> None:
        """List all rule types.

        Syntax:
            listRuleTypes [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            rule_types = self.config_manager.get_rule_types()
            if not rule_types:
                print(self.display_formatter.format_info("No rule types found"))
                return

            # Apply filter if provided
            if filter_expression:
                rule_types = self.config_manager.apply_filter(rule_types, filter_expression)

            if not rule_types:
                print(self.display_formatter.format_info("No matching rule types found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_rule_type_list(rule_types)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for rule_type in rule_types:
                    lines.append(self.display_formatter.format_json(json.dumps(rule_type), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(rule_types, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list rule types: {e}"))

    def do_getRuleType(self, arg: str) -> None:
        """Get details of a specific rule type.

        Syntax:
            getRuleType <rule_type_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Rule type ID is required"
            ))
            return

        try:
            rule_type_id = int(cleaned_arg.strip())
            rule_type_record = self.config_manager.get_record('CFG_RTYPE', 'RTYPE_ID', rule_type_id)
            if not rule_type_record:
                print(self.display_formatter.format_error(f"Rule type not found"))
                return

            # Transform raw database record to user-friendly JSON format
            rule_type = self.config_manager.format_rule_type_json(rule_type_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_rule_type_details(rule_type)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(rule_type, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Rule type ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get rule type: {e}"))

    def do_addGenericPlan(self, arg: str) -> None:
        """Add a generic plan.

        Syntax:
            addGenericPlan <plan_json>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Generic plan JSON is required"
            ))
            return

        try:
            plan_config = json.loads(arg.strip())
            if self.config_manager.add_generic_plan(plan_config):
                print(self.display_formatter.format_success(
                    "Generic plan added successfully"
                ))
            else:
                print(self.display_formatter.format_error(
                    "Failed to add generic plan"
                ))
        except json.JSONDecodeError as e:
            print(self.display_formatter.format_error(
                f"Invalid JSON configuration: {e}"
            ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add generic plan: {e}"))

    def do_deleteGenericPlan(self, arg: str) -> None:
        """Delete a generic plan.

        Syntax:
            deleteGenericPlan <plan_id>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Generic plan ID is required"
            ))
            return

        try:
            plan_id = int(arg.strip())
            if self.config_manager.delete_generic_plan(plan_id):
                print(self.display_formatter.format_success(
                    f"Successfully deleted generic plan {plan_id}"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete generic plan {plan_id}"
                ))
        except ValueError:
            print(self.display_formatter.format_error("Generic plan ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete generic plan: {e}"))

    def do_validate(self, arg: str) -> None:
        """Validate the current configuration.

        Syntax:
            validate [validation_type]
        """
        validation_type = arg.strip() if arg.strip() else "full"

        try:
            validation_result = self.config_manager.validate_configuration(validation_type)
            if validation_result.get('valid', False):
                print(self.display_formatter.format_success(
                    "Configuration validation passed"
                ))
                if validation_result.get('warnings'):
                    print(self.display_formatter.format_warning(
                        f"Warnings: {len(validation_result['warnings'])}"
                    ))
                    for warning in validation_result['warnings']:
                        print(self.display_formatter.format_warning(f"  {warning}"))
            else:
                print(self.display_formatter.format_error(
                    "Configuration validation failed"
                ))
                if validation_result.get('errors'):
                    for error in validation_result['errors']:
                        print(self.display_formatter.format_error(f"  {error}"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to validate configuration: {e}"))

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
                rules = self.config_manager.apply_filter(rules, filter_expression)

            if not rules:
                print(self.display_formatter.format_info("No matching rules found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_rule_list(rules)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for rule in rules:
                    lines.append(self.display_formatter.format_json(json.dumps(rule), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(rules, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list rules: {e}"))

    def do_getRule(self, arg: str) -> None:
        """Get details of a specific rule.

        Syntax:
            getRule <rule_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Rule ID is required"
            ))
            return

        try:
            rule_id = int(cleaned_arg.strip())
            rule_record = self.config_manager.get_record('CFG_RULE', 'RULE_ID', rule_id)
            if not rule_record:
                print(self.display_formatter.format_error(f"Rule not found"))
                return

            # Transform raw database record to user-friendly JSON format
            rule = self.config_manager.format_rule_json(rule_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_rule_details(rule)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(rule, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Rule ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get rule: {e}"))