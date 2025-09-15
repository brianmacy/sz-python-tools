"""Base shell functionality."""

import cmd
from typing import Optional, TYPE_CHECKING

try:
    from ..._tool_helpers import colorize_cmd_prompt
except (ImportError, ValueError):
    from _tool_helpers import colorize_cmd_prompt

if TYPE_CHECKING:
    try:
        from ..._config_core import ConfigurationManager
        from ..._config_display import ConfigDisplayFormatter
    except (ImportError, ValueError):
        from _config_core import ConfigurationManager
        from _config_display import ConfigDisplayFormatter

try:
    import atexit
    import readline
except ImportError:
    readline = None


class BaseShell(cmd.Cmd):
    """Base shell class with common functionality."""

    def __init__(self, config_manager: 'ConfigurationManager',
                 display_formatter: 'ConfigDisplayFormatter',
                 force_mode: bool = False,
                 hist_disable: bool = False):
        """Initialize the base shell.

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

        # Output format settings
        self.current_output_format_record = "json"
        self.current_output_format_list = "json"

        # Set up prompt (simplified for now)
        self.prompt = "(szcfg) "

        # Set up command completion and history
        if readline and not hist_disable:
            self._setup_history()

    def _setup_history(self) -> None:
        """Set up command history if readline is available."""
        if not readline:
            return

        # History settings
        readline.set_history_length(1000)

        # Try to load existing history
        import pathlib
        hist_file = pathlib.Path.home() / ".sz_configtool_history"
        try:
            if hist_file.exists():
                readline.read_history_file(str(hist_file))
        except (OSError, IOError):
            pass

        # Save history on exit
        def save_history():
            try:
                readline.write_history_file(str(hist_file))
            except (OSError, IOError):
                pass

        atexit.register(save_history)

    def check_arg_for_output_format(self, output_type: str, arg: str) -> str:
        """Check and extract output format from command arguments.

        Args:
            output_type: Type of output ("record" or "list")
            arg: Command argument string

        Returns:
            Cleaned argument string without format specifier
        """
        if not arg:
            return ""

        words = arg.split()
        if not words:
            return ""

        # Check if last word is a format specifier
        last_word = words[-1].lower()
        valid_formats = ["table", "json", "jsonl"]

        if last_word in valid_formats:
            if output_type == "record":
                self.current_output_format_record = last_word
            else:  # list
                self.current_output_format_list = last_word
            # Return args without format specifier
            return " ".join(words[:-1])

        return arg

    def id_or_code_parm(self, arg_str: str, int_tag: str, str_tag: str,
                       int_field: str, str_field: str) -> tuple:
        """Parse ID or code parameter.

        Args:
            arg_str: Argument string to parse
            int_tag: Tag for integer parameter
            str_tag: Tag for string parameter
            int_field: Database field name for integer
            str_field: Database field name for string

        Returns:
            Tuple of (search_value, search_field)
        """
        if not arg_str:
            raise ValueError(f"{int_tag} or {str_tag} is required")

        arg_str = arg_str.strip()

        # Try to parse as integer first
        try:
            search_value = int(arg_str)
            return search_value, int_field
        except ValueError:
            # Not an integer, treat as code
            return arg_str, str_field

    def validate_parms(self, parm_dict: dict, required_list: list = None,
                      optional_list: list = None) -> bool:
        """Validate command parameters.

        Args:
            parm_dict: Dictionary of parameters to validate
            required_list: List of required parameter names
            optional_list: List of optional parameter names

        Returns:
            True if validation passes, False otherwise
        """
        if required_list is None:
            required_list = []
        if optional_list is None:
            optional_list = []

        # Check required parameters
        for req_parm in required_list:
            if req_parm not in parm_dict or not parm_dict[req_parm]:
                print(self.display_formatter.format_error(
                    f"Required parameter '{req_parm}' is missing or empty"
                ))
                return False

        # Check for unexpected parameters
        allowed_parms = set(required_list + optional_list)
        for parm in parm_dict:
            if parm not in allowed_parms:
                print(self.display_formatter.format_error(
                    f"Unexpected parameter '{parm}'"
                ))
                return False

        return True

    def default(self, line: str) -> None:
        """Handle unrecognized commands."""
        cmd_parts = line.split()
        if cmd_parts:
            print(self.display_formatter.format_error(
                f"Unknown command: {cmd_parts[0]}. Type 'help' for available commands."
            ))

    def do_help(self, help_topic: str) -> None:
        """Display help for commands."""
        if not help_topic.strip():
            # Show general help
            self._show_general_help()
        else:
            # Show specific command help
            cmd_name = help_topic.strip()
            method_name = f"do_{cmd_name}"

            if hasattr(self, method_name):
                method = getattr(self, method_name)
                if hasattr(method, '__doc__') and method.__doc__:
                    print(self.display_formatter.format_info(method.__doc__.strip()))
                else:
                    print(self.display_formatter.format_info(f"No help available for '{cmd_name}'"))
            else:
                print(self.display_formatter.format_error(f"Unknown command: {cmd_name}"))

    def _show_general_help(self) -> None:
        """Show general help information."""
        help_text = """
sz_configtool - Senzing Configuration Management Tool
====================================================

Basic Commands:
  help                      - Display help for commands.
  quit                      - Exit the configuration tool.
  exit                      - Exit the configuration tool.

Usage:
  help <command>        - Show detailed help for specific command
  <command> [args]      - Execute the specified command
  quit/exit            - Exit the configuration tool
"""
        print(self.display_formatter.format_info(help_text))

    def do_quit(self, arg: str) -> bool:
        """Exit the configuration tool."""
        print(self.display_formatter.format_info("Goodbye!"))
        return True

    def do_exit(self, arg: str) -> bool:
        """Exit the configuration tool."""
        return self.do_quit(arg)