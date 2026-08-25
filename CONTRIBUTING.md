# Contributing to goodolclint.uptime_kuma

## Development Prerequisites

- Python >= 3.10
- ansible-core >= 2.16
- antsibull-changelog
- Docker (for integration tests)

## Architecture Decisions

Decisions live in `docs/decisions/` and are binding:

- [ADR 0001](docs/decisions/0001-in-repo-python-socketio-client-replaces-the-uptime-kuma-api-wrapper-uptime-kuma-2-x-only.md) — the collection talks to Uptime Kuma 2.x through an in-repo client (`plugins/module_utils/uptime_kuma_api.py`) built on `python-socketio[client]`, the only pip dependency and a documented exception to the stdlib-only rule (there is no REST API; Socket.IO is the only interface). Uptime Kuma 1.x is not supported.
- [ADR 0002](docs/decisions/0002-pr-review-gating-tamper-proof-claude-review-as-a-required-check-codeowners-for-policy-paths.md) — PR review gating.
- [ADR 0003](docs/decisions/0003-credentials-are-compared-normally-and-never-returned-nothing-on-uptime-kuma-2-x-is-write-only.md) — credentials are compared like every other field and never returned; nothing on 2.x is write-only.

Historical: the original CONTRIBUTING ADR-001 (2026-03-13) chose the `uptime-kuma-api` wrapper after weighing a stdlib Socket.IO client, the wrapper, and deferring the collection; ADR 0001 superseded it. ADR-002 (write-only fields excluded from comparison) was superseded by ADR 0003.

## Running Tests

These are the same commands CI runs; all of them must pass before a PR is opened.

### Unit tests (with the module_utils coverage floor)

```bash
python -m pytest tests/unit/ --cov=plugins/module_utils --cov-fail-under=80
```

### Sanity

`ansible-test` needs the collection checked out under an `ansible_collections/goodolclint/uptime_kuma` path:

```bash
ansible-test sanity --python 3.12 --requirements
```

### Integration tests

Against the local dev instance (`tests/dev/up.sh`), with the collection on `ANSIBLE_COLLECTIONS_PATH`:

```bash
ansible-playbook tests/integration/run.yml
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

Releases are cut by the operator only; the review prompt treats a version bump in any other PR as a blocker.

1. In a PR titled `chore: release vX.Y.Z`: update `version` in galaxy.yml and run `antsibull-changelog release`, which folds `changelogs/fragments/` into CHANGELOG.rst.
2. Merge, then tag the merge commit: `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. The Release workflow verifies the tag matches galaxy.yml and that CHANGELOG.rst has a section for it, builds, publishes to Ansible Galaxy with the `GALAXY_API_KEY` repository secret, and creates a GitHub Release with the tarball.

One-time setup: sign in to https://galaxy.ansible.com with GitHub (this creates the `goodolclint` namespace), generate an API token under Collections → API token, and store it as the `GALAXY_API_KEY` secret on this repository.
