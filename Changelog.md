# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project will adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html),
once its public API is documented.

## [Unreleased]

### Added
- Heartbeats
- Basic state support

### Changed
- simplify module __init__

### Fixed

### Deprecated

### Removed
- The capture module

### Security

## [0.0.3] - 2023-03-01

### Added

- Release to GitHub
- Secure Shell login Module
- Syslog server CLI
- CounterOverTime utility class
- Caputil CLI utility
- Initial docs

### Fixed
- lots of stuff

### Removed
- GlobalConfig class

## [0.0.2] - 2023-02-19

### Added
- Started documenting code
- Syslog trailer (record separator) discovery.
- Some captured syslog/linux data

### Changed
- Transition from SocketServer
- Changed formats to f-strings

### Fixed
- Logging
- Structured data parsing

### Removed
- All code for proprietary systems.

## [0.0.1] - 2023-02-13

### Added

- Python package
- Module & Event system
- README.md
- Example CLI's that process log files as well as syslog data.
- Extensions and modules support logs from proprietary system.

