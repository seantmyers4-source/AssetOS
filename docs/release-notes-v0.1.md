# AssetOS Minimum Operational Baseline v0.1 Release Notes

Control reference: `AOS-HO-00001`

Release state: **Controlled / Non-production / Non-operational**

Independently tested implementation commit: `92f6747d4c9a79de3978a441b335744e0fca6c9f`

## Release Summary

AssetOS Minimum Operational Baseline v0.1 is a bounded, controlled, non-production Registry kernel release package for implementation readback and downstream production-admission planning. It does not authorize deployment, production admission, RuntimeOS execution, or AssetOS activation.

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

The following capabilities are not included in MOB v0.1 and their absence is not a defect in this bounded release:

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

- `QA-ACT-001` — Production host hardening not demonstrated: **Open / Activation-blocking**.
- `QA-ACT-002` — Real Google Drive continuity/reconciliation not tested: **Open / Activation-blocking**.
- ARIR-013 release representation: **Closed with activation conditions**.
- ARIR-014 release representation: **Verified with activation conditions**.

The Registry to Google Drive contract is adequate for the controlled non-production release package. Production-connected Drive use remains prohibited pending activation-readiness verification.

## Backup Cryptography

The controlled backup implementation uses Python `cryptography`, Fernet authenticated encryption, PBKDF2-HMAC-SHA256, a random 16-byte salt, 600,000 PBKDF2 iterations, and in-process passphrase handling.

Release acceptance of this bounded cryptographic implementation does not constitute production approval of production secret handling, backup-storage controls, passphrase/key operating procedure, host protection, recovery responsibilities, or operational key/passphrase management. Those matters require later competent Security & Privacy and Architecture & Standards approval.

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

## Historical Release-Readiness Chain

- Original controlled candidate: `8f223f70458cec28afe660aef990f949aae2adec`.
- Initial release-readiness campaign: not ready; QA-RR-001 through QA-RR-009 identified.
- Bounded remediation implementation correction: `0a26b75975c710e75e25c93848006a6337a4810f`.
- Correction-package head independently retested: `92f6747d4c9a79de3978a441b335744e0fca6c9f`.
- Independent QA disposition: release readiness verified with conditions; QA-RR-001 through QA-RR-009 closed.
- Documentation-only finding: QA-DOC-001, corrected in the controlled release-package documentation commit.
- Controlled release authorization: AssetOS Minimum Operational Baseline v0.1, controlled / non-production / non-operational.
