# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

-

### Changed

-

### Deprecated

-

### Removed

-

### Fixed

-

### Security

-

## [7.1.1]

### Fixed

- Fix Netatmo radiator valves (NRV) set termpature

## [7.1.0] - 2022-10-03

### Added

- Adds Legrand NLIS double switches
- Adds Legrand NLPT relay/teleruptor

### Fixed

- Use dimmer type for Legrand NLF dimmers

## [7.0.1] - 2022-06-05

### Deprecated

- The following modules are deprecated and will be removed in pyatmo 8.0.0
    - camera
    - home_coach
    - public_data
    - thermostat
    - weather_station

## [7.0.0] - 2022-06-05

### Added

- Adds support for Netatmo modulating thermostat
- Adds support for Netatmo doorbell
- Adds support for shutters, lights, energy meters and switches
- Adds support for 3rd party devices from different Legrand brands such as BTicinio, Bubendorff, Smarther, CX3
- Fetch favorite weather sensors
- Add support for third-party Netatmo devices (see `base_url` and `user_prefix` parameters)

### Changed

- Replace freezegun with time-machine

### Deprecated

- The following modules are deprecated and will be removed in pyatmo 8.0.0
    - camera
    - home_coach
    - public_data
    - thermostat
    - weather_station

### Removed

-

### Fixed

- Use async fixture decorators

### Security

-

## [6.2.4] - 2022-01-31

### Fixed

- Crash when home does not contain valid devices

## [6.2.2] - 2021-12-29

### Fixed

- Use ID if schedule name is missing

## [6.2.1] - 2021-12-18

### Fixed

- Catch when no body is contained in the response

## [6.2.0] - 2021-11-19

### Added

- Add support for python3.20
- Introduce climate module #156

### Changed

- Use assignment expressions

## [6.1.0] - 2021-10-03

### Added

- Provide a VS Code devcontainer

### Changed

- Provide separate method for image retrival
- Minor f-string conversions

## [6.0.0] - 2021-09-10

### Changed

- Ensure camera name is not None
- Split persons by home
- BREAKING: Require home_id for person related methods
- version is now managed by setuptools scm

## [5.2.3] - 2021-07-22

### Fixed

- Ignore if API omits unimportant attributes in response

## [5.2.2] - 2021-07-21

### Fixed

- Ignore if API omits unimportant attributes in response

## [5.2.1] - 2021-07-10

### Added

- Distribute type information

### Changed

- Update type annotations

## [5.2.0] - 2021-06-30

### Changed

- [BREAKING] Fix parameter order of set person home/away methods
- Refactor camera person detection checks

## [5.1.0] - 2021-06-14

### Fixed

- Handle error when camera is not reachable more graceful
- Update selfcheck to use the new update methods
- Fix false positive errors when no climate devices are registered

### Security

- Upgrade aiohttp to 3.7.4 or later to fix vulnerability

## [4.2.3] - 2021-05-17

### Fixed

- Extraction of climate schedules was looking for the wrong attribute (Backported from [5.0.1])

## [5.0.1] - 2021-05-09

### Fixed

- Extraction of climate schedules was looking for the wrong attribute

## [5.0.0] - 2021-04-26

### Added

- Async support

### Changed

- [BREAKING] Data retrival extracted into separate update method

## [4.2.2] - 2021-01-20

### Fixed

- Fix error when camera does not return a local url

## [4.2.1] - 2020-12-03

### Changed

- Improve CI & deployment

## [4.2.0] - 2020-11-02

### Changed

- Improve CI & deployment

### Fixed

- Set station name if not contained in the backend data

### Removed

- Remove min and max from weather station

## [4.1.0] - 2020-10-07

### Fixed

- Fix crash when station name is not contained in the backend data

[unreleased]: https://github.com/jabesq/pyatmo/compare/v7.0.1...HEAD
[7.0.1]: https://github.com/jabesq/pyatmo/compare/v7.0.0...v7.0.1
[7.0.0]: https://github.com/jabesq/pyatmo/compare/v6.2.4...v7.0.0
[6.2.4]: https://github.com/jabesq/pyatmo/compare/v6.2.2...v6.2.4
[6.2.2]: https://github.com/jabesq/pyatmo/compare/v6.2.1...v6.2.2
[6.2.1]: https://github.com/jabesq/pyatmo/compare/v6.2.0...v6.2.1
[6.2.0]: https://github.com/jabesq/pyatmo/compare/v6.1.0...v6.2.0
[6.1.0]: https://github.com/jabesq/pyatmo/compare/v6.0.0...v6.1.0
[6.0.0]: https://github.com/jabesq/pyatmo/compare/v5.2.3...v6.0.0
[5.2.3]: https://github.com/jabesq/pyatmo/compare/v5.2.2...v5.2.3
[5.2.2]: https://github.com/jabesq/pyatmo/compare/v5.2.1...v5.2.2
[5.2.1]: https://github.com/jabesq/pyatmo/compare/v5.2.0...v5.2.1
[5.2.0]: https://github.com/jabesq/pyatmo/compare/v5.1.0...v5.2.0
[5.1.0]: https://github.com/jabesq/pyatmo/compare/v5.0.1...v5.1.0
[5.0.1]: https://github.com/jabesq/pyatmo/compare/v5.0.0...v5.0.1
[5.0.1]: https://github.com/jabesq/pyatmo/compare/v4.2.2...v5.0.0
[4.2.3]: https://github.com/jabesq/pyatmo/compare/v4.2.2...v4.2.3
[4.2.2]: https://github.com/jabesq/pyatmo/compare/v4.2.1...v4.2.2
[4.2.1]: https://github.com/jabesq/pyatmo/compare/v4.2.0...v4.2.1
[4.2.0]: https://github.com/jabesq/pyatmo/compare/v4.1.0...v4.2.0
[4.1.0]: https://github.com/jabesq/pyatmo/compare/v4.0.0...v4.1.0
[4.0.0]: https://github.com/jabesq/pyatmo/compare/v3.3.1...v4.0.0
[3.3.1]: https://github.com/jabesq/pyatmo/releases/tag/v3.3.1
