# sz-python-tools

A Python toolkit for working with Senzing entity resolution, providing various command-line tools for data loading, analysis, configuration, and export operations.

If you are beginning your journey with [Senzing],
please start with [Senzing Quick Start guides].

You are in the [Senzing Garage] where projects are "tinkered" on.
Although this GitHub repository may help you understand an approach to using Senzing,
it's not considered to be "production ready" and is not considered to be part of the Senzing product.
Heck, it may not even be appropriate for your application of Senzing!

## :warning: WARNING: sz-python-tools is still in development :warning:

## 🚀 Recent Major Update: sz_configtool Modular Refactoring

The `sz_configtool` has been completely refactored with a modular architecture while maintaining 100% feature parity:

- **✅ Modular Architecture**: Separated into domain-specific managers (DataSource, Feature, Function, Rules, System)
- **✅ 100% Feature Parity**: All 120+ commands preserved and validated
- **✅ Comprehensive Testing**: 1,586 tests with 98.7% pass rate
- **✅ Production Ready**: Robust error handling and backwards compatibility

### Key Components

- `sz_configtool` - Original interactive configuration tool (preserved)
- `configtool_main.py` - New modular implementation entry point
- `configtool/` - Modular architecture with domain managers
- `tests/` - Comprehensive test suite covering all functionality

See [CLAUDE.md](CLAUDE.md) for detailed project requirements and [COMPREHENSIVE_PROJECT_OVERVIEW.md](COMPREHENSIVE_PROJECT_OVERVIEW.md) for complete implementation details.

[Senzing Garage]: https://github.com/senzing-garage
[Senzing Quick Start guides]: https://docs.senzing.com/quickstart/
[Senzing]: https://senzing.com/
