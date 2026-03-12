# Contributing to goodolclint.uptime_kuma

## Development Prerequisites

- Python >= 3.9
- ansible-core >= 2.14
- antsibull-changelog
- Docker (for integration tests)

## Architecture Decisions

<!-- Populated during development — see CLAUDE.md for initial decisions -->

## Running Tests

### Unit tests

```bash
python -m pytest tests/unit/
```

### Integration tests

```bash
ansible-test integration --docker
```

## Adding a New Module

1. Add module file to `plugins/modules/uptime_kuma_<resource>.py`
2. Implement DOCUMENTATION, EXAMPLES, RETURN blocks (no stubs)
3. Implement idempotency logic using the base API client
4. Add unit tests under `tests/unit/plugins/modules/`
5. Add integration test target under `tests/integration/targets/`
6. Add a changelog fragment

## PR Guidelines

- Idempotency verified (run twice, assert changed=false on second run)
- ansible-lint profile=production clean
- All DOCUMENTATION/EXAMPLES/RETURN blocks complete
- FQCN used throughout all examples
- Changelog fragment present

## Release Procedure

1. Update version in galaxy.yml
2. Run: `antsibull-changelog release`
3. Commit: `chore: release vX.Y.Z`
4. Tag: `git tag vX.Y.Z`
5. Push tag to trigger release workflow
