# AssetOS Minimum Operational Baseline v0.1.1 Corrective Release Notes

Control reference: `AOS-HO-00001`

Release state: **Controlled / Non-production / Non-operational**

Original governed release: `mob-v0.1`

Original release target: `12c144e4580331a4e7642ddaa1a0f82899078e38`

Verified correction baseline: `82844ce60021033d47439e62cf8c4bc9f100c634`

Target corrective release: `mob-v0.1.1`

## Release Summary

AssetOS Minimum Operational Baseline v0.1.1 is a bounded corrective release package for the non-operational MOB v0.1 line. It incorporates the independently QA-verified `DEP-INIT-001` installed migration-resource packaging correction without expanding MOB capability.

This corrective release does not authorize deployment, production admission, RuntimeOS execution, first controlled Asset admission, or AssetOS activation.

## v0.1 to v0.1.1 Distinction

- `mob-v0.1` is the original controlled release. During synthetic admission-readiness deployment verification, the installed artifact resolved migrations to a nonexistent environment path and discovered zero SQL migrations.
- `mob-v0.1.1` is the bounded corrective release package that preserves the MOB v0.1 capability scope while correcting installed migration-resource packaging/resolution.

The existing `mob-v0.1` tag must remain immutable and must not be moved, deleted, recreated, or repointed.

## Corrected Finding

`DEP-INIT-001 — Installed Schema Resource Packaging / Resolution Defect`

Technical correction: independently verified.

Release integration: in progress through this v0.1.1 corrective release package.

Final lifecycle closure remains pending corrective release publication, clean Windows deployment verification, and applicable evidence-custody closure.

The correction includes:

- installed package-resource migration discovery using `importlib.resources`;
- packaged `assetos_mob.migrations/001_mob.sql`;
- packaged migration-resource namespace;
- `pyproject.toml` package-data declaration;
- installed-artifact regression coverage;
- directly associated controlled documentation.

## Package Identity

Python package version metadata is `0.1.1`.

This version change identifies the corrective distributable. It does not alter executable source, migration content, schema, dependency behavior, test logic, authorization, cryptography, Registry semantics, APIs, or runtime behavior after verified correction candidate `82844ce60021033d47439e62cf8c4bc9f100c634`.

## Included MOB Capabilities

- Asset intake.
- Candidate permanent Asset-ID generation.
- Asset-ID validation.
- Transactional reservation.
- Permanent assignment.
- Canonical Asset creation.
- Validation/publication gate.
- Minimum Taxonomy assignment.
- Information-class assignment.
- Governed evidence references.
- Evidence continuity.
- Original/derivative treatment.
- Bounded authorized retrieval/search.
- Effective-dated append/supersede history.
- Controlled export.
- Encrypted backup/restore.
- Audit behavior.

## Deferred Capabilities

The following capabilities are not included in MOB v0.1.1 and their absence is not a defect in this bounded release:

- TaskOS integration.
- Google Calendar integration.
- Maintenance scheduling.
- Lifecycle automation.
- Automated condition assessment.
- Valuation calculations.
- FinanceOS integration.
- Risk scoring.
- Insurance sufficiency.
- Claim workflows.
- Recovery automation.
- Production OCR.
- Production AI.
- Digital-twin presentation.
- QR generation.
- Physical labels/carriers.
- Public resolver.
- Insurer/provider integrations.
- RuntimeOS execution.

## Release Conditions

- `DEP-QA-001` through `DEP-QA-004`: **Resolved**.
- `DEP-QA-005`: **Open / evidence-custody condition**.
- `QA-ACT-001` — Production host hardening not demonstrated: **Open / Activation-blocking**.
- `QA-ACT-002` — Real Google Drive continuity/reconciliation not tested: **Open / Activation-blocking**.
- ARIR-013 release representation: **Closed with activation conditions**.
- ARIR-014 release representation: **Verified with activation conditions**.

Production-connected Drive use remains prohibited pending activation-readiness verification.

## Production Warning

This release does not authorize:

- real Asset intake;
- production permanent Asset-ID issuance;
- production Registry publication;
- production Taxonomy assignment;
- production information-class assignment;
- production Google Drive evidence association;
- Drive migration;
- production backup;
- deployment;
- RuntimeOS execution;
- AssetOS admission;
- AssetOS activation.

Repository release package does not mean deployment.

## Historical Lineage

- Original controlled candidate: `8f223f70458cec28afe660aef990f949aae2adec`.
- Bounded remediation implementation correction: `0a26b75975c710e75e25c93848006a6337a4810f`.
- Correction-package head independently retested: `92f6747d4c9a79de3978a441b335744e0fca6c9f`.
- Controlled release-package commit for `mob-v0.1`: `12c144e4580331a4e7642ddaa1a0f82899078e38`.
- DEP-INIT-001 discovered during synthetic admission-readiness deployment verification.
- DEP-INIT-001 correction candidate: `82844ce60021033d47439e62cf8c4bc9f100c634`.
- Corrective release target: `mob-v0.1.1`.
