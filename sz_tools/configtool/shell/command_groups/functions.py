"""Function and expression management commands."""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import BaseShell


class FunctionCommands:
    """Mixin class for function and expression related commands."""

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
                functions = self.config_manager.apply_filter(functions, filter_expression)

            if not functions:
                print(self.display_formatter.format_info("No matching comparison functions found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_comparison_function_list(functions)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for func in functions:
                    lines.append(self.display_formatter.format_json(json.dumps(func), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(functions, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list comparison functions: {e}"))

    def do_getComparisonFunction(self, arg: str) -> None:
        """Get details of a specific comparison function.

        Syntax:
            getComparisonFunction <function_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Comparison function ID is required"
            ))
            return

        try:
            function_id = int(cleaned_arg.strip())
            function_record = self.config_manager.get_record('CFG_CFUNC', 'CFUNC_ID', function_id)
            if not function_record:
                print(self.display_formatter.format_error(f"Comparison function not found"))
                return

            # Transform raw database record to user-friendly JSON format
            function = self.config_manager.format_comparison_function_json(function_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_comparison_function_details(function)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(function, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Comparison function ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get comparison function: {e}"))

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
                functions = self.config_manager.apply_filter(functions, filter_expression)

            if not functions:
                print(self.display_formatter.format_info("No matching expression functions found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_expression_function_list(functions)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for func in functions:
                    lines.append(self.display_formatter.format_json(json.dumps(func), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(functions, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list expression functions: {e}"))

    def do_getExpressionFunction(self, arg: str) -> None:
        """Get details of a specific expression function.

        Syntax:
            getExpressionFunction <function_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Expression function ID is required"
            ))
            return

        try:
            function_id = int(cleaned_arg.strip())
            function_record = self.config_manager.get_record('CFG_EFUNC', 'EFUNC_ID', function_id)
            if not function_record:
                print(self.display_formatter.format_error(f"Expression function not found"))
                return

            # Transform raw database record to user-friendly JSON format
            function = self.config_manager.format_expression_function_json(function_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_expression_function_details(function)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(function, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Expression function ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get expression function: {e}"))

    def do_listStandardizeFunction(self, arg: str) -> None:
        """List all standardize functions.

        Syntax:
            listStandardizeFunction [filter_expression] [table|json|jsonl]
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
                functions = self.config_manager.apply_filter(functions, filter_expression)

            if not functions:
                print(self.display_formatter.format_info("No matching standardize functions found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_standardize_function_list(functions)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for func in functions:
                    lines.append(self.display_formatter.format_json(json.dumps(func), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(functions, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list standardize functions: {e}"))

    def do_getStandardizeFunction(self, arg: str) -> None:
        """Get details of a specific standardize function.

        Syntax:
            getStandardizeFunction <function_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Standardize function ID is required"
            ))
            return

        try:
            function_id = int(cleaned_arg.strip())
            function_record = self.config_manager.get_record('CFG_SFUNC', 'SFUNC_ID', function_id)
            if not function_record:
                print(self.display_formatter.format_error(f"Standardize function not found"))
                return

            # Transform raw database record to user-friendly JSON format
            function = self.config_manager.format_standardize_function_json(function_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_standardize_function_details(function)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(function, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Standardize function ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get standardize function: {e}"))

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
                functions = self.config_manager.apply_filter(functions, filter_expression)

            if not functions:
                print(self.display_formatter.format_info("No matching distinct functions found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_distinct_function_list(functions)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for func in functions:
                    lines.append(self.display_formatter.format_json(json.dumps(func), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(functions, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list distinct functions: {e}"))

    def do_getDistinctFunction(self, arg: str) -> None:
        """Get details of a specific distinct function.

        Syntax:
            getDistinctFunction <function_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Distinct function ID is required"
            ))
            return

        try:
            function_id = int(cleaned_arg.strip())
            function_record = self.config_manager.get_record('CFG_DFUNC', 'DFUNC_ID', function_id)
            if not function_record:
                print(self.display_formatter.format_error(f"Distinct function not found"))
                return

            # Transform raw database record to user-friendly JSON format
            function = self.config_manager.format_distinct_function_json(function_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_distinct_function_details(function)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(function, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Distinct function ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get distinct function: {e}"))

    def do_deleteDistinctCall(self, arg: str) -> None:
        """Delete a distinct function call.

        Syntax:
            deleteDistinctCall <call_id>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Distinct call ID is required"
            ))
            return

        try:
            call_id = int(arg.strip())
            if self.config_manager.delete_distinct_call(call_id):
                print(self.display_formatter.format_success(
                    f"Successfully deleted distinct call {call_id}"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete distinct call {call_id}"
                ))
        except ValueError:
            print(self.display_formatter.format_error("Distinct call ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete distinct call: {e}"))

    def do_listDistinctCalls(self, arg: str) -> None:
        """List all distinct function calls.

        Syntax:
            listDistinctCalls [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            calls = self.config_manager.get_distinct_calls()
            if not calls:
                print(self.display_formatter.format_info("No distinct calls found"))
                return

            # Apply filter if provided
            if filter_expression:
                calls = self.config_manager.apply_filter(calls, filter_expression)

            if not calls:
                print(self.display_formatter.format_info("No matching distinct calls found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_distinct_call_list(calls)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                lines = []
                for call in calls:
                    lines.append(self.display_formatter.format_json(json.dumps(call), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json
                output = self.display_formatter.format_json(json.dumps(calls, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list distinct calls: {e}"))

    def do_getDistinctCall(self, arg: str) -> None:
        """Get details of a specific distinct function call.

        Syntax:
            getDistinctCall <call_id> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Distinct call ID is required"
            ))
            return

        try:
            call_id = int(cleaned_arg.strip())
            call_record = self.config_manager.get_record('CFG_DCALL', 'DCALL_ID', call_id)
            if not call_record:
                print(self.display_formatter.format_error(f"Distinct call not found"))
                return

            # Transform raw database record to user-friendly JSON format
            call = self.config_manager.format_distinct_call_json(call_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_distinct_call_details(call)
                print(output)
            else:  # json
                output = self.display_formatter.format_json(json.dumps(call, indent=2), pretty=True)
                print(output)
        except ValueError:
            print(self.display_formatter.format_error("Distinct call ID must be a number"))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get distinct call: {e}"))