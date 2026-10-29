# Contributing to VerdantOS

Thank you for your interest in contributing to VerdantOS!

## Governance & Phase Delivery
VerdantOS development strictly follows a **Contract-First** and **Phase Gate** architectural framework. All pull requests must align with the open phase roadmap in `docs/execution/PLAN.md`.

## Contribution Rules
1. **Contract First**: Any change modifying REST APIs (`contracts/openapi/`), Event Streams (`contracts/events/`), or Database Schemas (`db/migrations/`) must be reviewed and approved prior to code implementation.
2. **ISO 50001 Alignment**: Every domain capability must map to at least one clause in `docs/blueprint/17-traceability.md`.
3. **CI Pipeline Pass**: All pull requests must pass `.github/workflows/ci.yml` gates.

## Submitting Pull Requests
1. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
2. Run local pre-commit test suites.
3. Submit a Pull Request targeting the `main` branch with a clear descriptive summary.
