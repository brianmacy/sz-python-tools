"""Data Source command group."""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import BaseShell


class DataSourceCommands:
    """Mixin class for data source related commands."""

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
                lines = []
                for ds in data_sources:
                    lines.append(self.display_formatter.format_json(json.dumps(ds), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                # Print as JSON array
                output = self.display_formatter.format_json(json.dumps(data_sources, indent=2), pretty=True)
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