# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sz-python-tools is a Python toolkit for working with Senzing entity resolution. It provides various command-line tools for data loading, analysis, configuration, and export operations. The project is part of the Senzing Garage and is still in development.

## Development Commands

### Setup and Dependencies
- `make dependencies-for-development` - Install all development dependencies (one-time setup)
- `make dependencies` - Install runtime dependencies only
- `make venv` - Create virtual environment

### Testing and Quality
- `make test` - Run all tests
- `make lint` - Run all linting tools (pylint, mypy, bandit, black, flake8, isort)
- `make coverage` - Generate code coverage report

Individual linting tools can be run separately:
- `make pylint` - Python linting
- `make mypy` - Type checking
- `make bandit` - Security linting
- `make black` - Code formatting
- `make flake8` - Style checking
- `make isort` - Import sorting

### Development Workflow
- `make clean` - Clean up build artifacts
- `make setup` - OS-specific setup tasks
- `make run CLI_ARGS="..."` - Run tools with arguments

## Project Structure

The project follows a typical Python package structure:

- `sz_tools/` - Main package containing all command-line tools
- `data/` - Sample and test data files
- `docs/` - Documentation files
- `makefiles/` - OS-specific Makefile includes

### Key Components

#### Command-Line Tools (sz_tools/)
Each tool is a standalone executable script:
- `sz_command` - Interactive command interface for Senzing operations
- `sz_audit` - Audit and analysis tools
- `sz_export` - Data export functionality
- `sz_file_loader` - Data loading utilities
- `sz_snapshot` - Create system snapshots
- `sz_explorer` - Data exploration tools
- `sz_create_project` - Project creation utilities
- `sz_setup_config` - Configuration setup
- `sz_configtool` - Configuration management
- `sz_json_analyzer` - JSON data analysis
- `sz_update_project` - Project update utilities

#### Helper Modules
- `_tool_helpers.py` - Common utilities for CLI tools (colors, formatting, engine interaction)
- `_sz_database.py` - Database interaction utilities
- `_project_helpers.py` - Project management helpers

## Architecture Notes

### Tool Design Pattern
All tools follow a consistent pattern:
1. Import common utilities from `_tool_helpers.py`
2. Use Senzing SDK (`senzing` and `senzing_core` packages)
3. Implement command-line interfaces with proper argument parsing
4. Support colored output, JSON formatting, and debugging modes

### Configuration
- Uses `pyproject.toml` for Python packaging and tool configuration
- Supports multiple linting tools with consistent configuration
- Requires Senzing C library installation (`/opt/senzing/er/`)

### Dependencies
- Core dependencies: `senzing >= 4.0.2`, `senzing-core >= 1.0.0`
- Development dependencies include testing and linting tools
- Supports Python 3.9+

## Development Notes

### Environment Setup
The project expects the Senzing C library to be installed at `/opt/senzing/er/`. This is a prerequisite for development and runtime.

### Testing
Tests can be run with `make test` or individual pytest commands. The project uses pytest for testing framework.

### Code Standards
- **PEP8 Compliance**: All code must follow PEP8 standards
- Line length: 120 characters (configured in pyproject.toml)
- Uses black for code formatting
- mypy for type checking with strict mode
- bandit for security analysis
- Multiple pylint customizations for this codebase

### Architecture Principles
- **Separation of Concerns**: UI application code must be separate from core functions
- **Core Functions**: Business logic (configuration editing, data processing, etc.) should be in separate modules
- **Display Functions**: Result formatting and display logic should be in separate modules
- **Unit Testing**: Core functions and display functions must be separately unit tested
- **Modularity**: Each functional area should have its own module with clear interfaces
- **Feature Preservation**: All functionality from the original sz_configtool must be preserved (120 commands)

### Critical Implementation Requirement
**IMPORTANT**: Any refactoring or rewriting of sz_configtool must maintain 100% feature parity with the original. The original sz_configtool contains 120 commands covering:
- Data source management
- Feature configuration and management
- Attribute definitions and mappings
- Element management and relationships
- Comparison functions and expressions
- Business rules and behavior overrides
- Configuration validation and verification
- Advanced scoring and threshold management

A partial implementation that only covers basic operations is insufficient for production use.
- Do not stop until all functionality is complete and tests pass
- Always check the help to see if it needs to be updated when changes are made.
- Always implement a comprehensive testing strategy
- Double check all work is complete, thoroughly tested, and passing all tests.  Find issues before I do.
- Tests should verify help, functionality, parameters, data retrieval, and display.
- When refactoring, verify memory usage and performance is similar to or better than the original.
- Before you are complete make sure you validate all project and user requirements are met for all functionality.
- Don't be lazy.  Do all the work, not part of it.  Remember, you work for me.  I don't work for you.
- Don't tell me you are done if you haven't completed all testing
- When refactoring code, first analyze the existing code, write full unit tests, and then create the refactored framework.  Run the same tests on the refactored framework to confirm they all fail before implementing the code in the refactored framework.
- Make sure code adheres to best practices for maintainability and complexity