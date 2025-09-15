"""System and configuration management commands."""

import json
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import BaseShell


class SystemCommands:
    """Mixin class for system and configuration management commands."""

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
        """
        config_id = None
        if arg.strip():
            try:
                config_id = int(arg.strip())
            except ValueError:
                print(self.display_formatter.format_error(
                    "Configuration ID must be a number"
                ))
                return

        if self.config_manager.load_config(config_id):
            loaded_id = config_id or self.config_manager.get_default_config_id()
            print(self.display_formatter.format_success(
                f"Configuration {loaded_id} loaded successfully"
            ))
        else:
            print(self.display_formatter.format_error(
                "Failed to load configuration"
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

    def do_setTheme(self, arg: str) -> None:
        """Enable or disable colored output.

        Syntax:
            setTheme <on|off>
        """
        if not arg.strip():
            current_state = "on" if self.display_formatter.use_colors else "off"
            print(self.display_formatter.format_info(
                f"Current theme setting: {current_state}"
            ))
            return

        setting = arg.strip().lower()
        if setting in ("on", "true", "1", "yes"):
            self.display_formatter.use_colors = True
            print(self.display_formatter.format_success("Color theme enabled"))
        elif setting in ("off", "false", "0", "no"):
            self.display_formatter.use_colors = False
            print(self.display_formatter.format_success("Color theme disabled"))
        else:
            print(self.display_formatter.format_error(
                "Invalid setting. Use 'on' or 'off'"
            ))

    def do_getConfigSection(self, arg: str) -> None:
        """Get a configuration section.

        Syntax:
            getConfigSection <section_name>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Section name is required"
            ))
            return

        section_name = arg.strip()
        try:
            section_data = self.config_manager.get_config_section(section_name)
            if section_data:
                output = self.display_formatter.format_json(
                    json.dumps(section_data, indent=2), pretty=True
                )
                print(output)
            else:
                print(self.display_formatter.format_error(
                    f"Configuration section '{section_name}' not found"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(
                f"Failed to retrieve section '{section_name}': {e}"
            ))

    def do_templateAdd(self, arg: str) -> None:
        """Add a template to create feature with attributes.

        Syntax:
            templateAdd <template_config>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Template configuration is required"
            ))
            return

        try:
            template_config = json.loads(arg.strip())
            if self.config_manager.add_template(template_config):
                print(self.display_formatter.format_success(
                    "Template added successfully"
                ))
            else:
                print(self.display_formatter.format_error(
                    "Failed to add template"
                ))
        except json.JSONDecodeError as e:
            print(self.display_formatter.format_error(
                f"Invalid JSON configuration: {e}"
            ))

    def do_touch(self, arg: str) -> None:
        """Touch/update configuration timestamp.

        Syntax:
            touch
        """
        if self.config_manager.touch_config():
            print(self.display_formatter.format_success(
                "Configuration timestamp updated"
            ))
        else:
            print(self.display_formatter.format_error(
                "Failed to update configuration timestamp"
            ))

    def do_history(self, arg: str) -> None:
        """Show command history.

        Syntax:
            history [number_of_lines]
        """
        try:
            import readline
            if not readline:
                print(self.display_formatter.format_error(
                    "History not available - readline module not found"
                ))
                return

            # Get number of lines to show
            num_lines = 20  # default
            if arg.strip():
                try:
                    num_lines = int(arg.strip())
                except ValueError:
                    print(self.display_formatter.format_error(
                        "Number of lines must be a number"
                    ))
                    return

            # Show history
            history_length = readline.get_current_history_length()
            start = max(1, history_length - num_lines + 1)

            for i in range(start, history_length + 1):
                line = readline.get_history_item(i)
                if line:
                    print(f"{i:4d}  {line}")

        except ImportError:
            print(self.display_formatter.format_error(
                "History not available - readline module not installed"
            ))