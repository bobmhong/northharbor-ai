# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffolding
- Guided interview flow for retirement intake
- Monte Carlo simulation engine
- Report generation (Markdown, PDF, JSON, Excel)
- Auth0 authentication integration
- React frontend with chat interface
- Store-backed LLM analytics persistence with MongoDB implementation and indexes

### Changed
- Added managed dev lifecycle tasks: `dev:up`, `dev:down`, and `dev:status`
- Interview responses now use client-facing language instead of internal field labels
- Plan and dashboard listings now show human-readable plan names (`<Client Name> - <Scenario Name>`)
- LLM analytics tracking now captures metrics in all environments and no longer relies on local JSON files
- `task dev:backend` and `task dev:up` now load `direnv` exports before backend startup

### Fixed
- Interview fallback extraction now handles common name, birth year, location, and numeric inputs more reliably
- Validation feedback now explains why inputs are invalid with actionable examples
- Confirm prompts now accept affirmative replies (e.g., "yes") and move forward
- Frontend interview submit flow now recovers from expired sessions after backend reloads
- Optional question prompts now request concrete values instead of ambiguous yes/no consent
- Interview sessions and plans now persist across backend restarts

### Removed
- _None yet_

---

<!-- 
## [0.1.0] - YYYY-MM-DD

### Added
- Feature description

### Changed
- Change description

### Fixed
- Fix description
-->
