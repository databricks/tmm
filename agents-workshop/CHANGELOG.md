# Changelog

All notable changes to this project will be documented in this file.

## [3.0.0] - 2025-07-19

### Changed
- Reduced tool calls in AI Playground for improved latency
- Implemented more specific judges with fewer evaluations required
- Now includes before and after prompts in the Agent defintion
- Removed unused tools from Agent definition for eval section

## [2.0.0] - 2025-06-24

### Changed
- Updated lab to MLflow 3.0+ evaluations
- Introduced new evaluation judges
- Set Claude as the default model
- Shifted eval quality improvement focus to prompt modification instead of retriever adjustments

### Improved
- Qvaluation quality through prompt changes instead of retriever settings

## [1.0.0] - 2025-01-06

### Added
- Initial release of the lab
- Core functionality for quality improvement through retriever value modifications
- Base evaluation system

---

*This changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.*