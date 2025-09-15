"""Main entry point for modular sz_configtool."""

import argparse
import pathlib
import sys
from typing import Optional

# Import from existing modules (absolute imports)
from .core.unified_manager import UnifiedConfigurationManager
try:
    from .._config_display import ConfigDisplayFormatter
except (ImportError, ValueError):
    from _config_display import ConfigDisplayFormatter
from .shell.main_shell import ConfigToolShell


def parse_cli_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    arg_parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Modular Senzing Configuration Tool.\nFollows Python best practices for maintainability.",
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
        action="store_true",
        default=False,
        help="force mode - no confirmation prompts",
    )
    arg_parser.add_argument(
        "-t",
        "--debug-trace",
        dest="verbose_logging",
        action="store_true",
        default=False,
        help="enable verbose logging for Senzing SDK",
    )
    arg_parser.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        default=False,
        help="disable colored output",
    )
    arg_parser.add_argument(
        "--hist-disable",
        dest="hist_disable",
        action="store_true",
        default=False,
        help="disable command history",
    )

    return arg_parser.parse_args()


def main() -> int:
    """Main entry point for the modular configuration tool.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    args = parse_cli_args()

    # Initialize components
    config_manager = UnifiedConfigurationManager(args.ini_file_name, verbose_logging=args.verbose_logging)
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

    return 0


if __name__ == "__main__":
    sys.exit(main())