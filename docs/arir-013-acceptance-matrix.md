# ARIR-013 Acceptance Matrix

Control reference: `AOS-HO-00001`

Release representation: **Closed with activation conditions**.

This matrix maps the approved ARIR-013 implementation-measurement requirements into reproducible producer tests and independent QA readback evidence for the controlled non-production MOB v0.1.1 corrective release package. This does not state that production admission or activation testing is complete.

| Area | Requirement | Producer evidence |
|---|---|---|
| Identity | Syntax, allowed characters, length, check symbol | `tests/test_identifiers.py::IdentifierTests` |
| Identity | Approved deterministic check vectors | `test_approved_deterministic_vectors` |
| Identity | Invalid check cannot reserve or assign | `test_identity_invalid_check_cannot_reserve`, `test_invalid_check_symbol_fails_closed` |
| Identity | Uniqueness and reservation | `test_duplicate_active_reservation_is_rejected` |
| Identity | Assignment requires reservation | `test_assignment_without_reservation_is_rejected` |
| Identity | Idempotency and retry | `test_reservation_and_assignment_are_idempotent_by_request` |
| Identity | Changed governed intent fails closed | `qa_adversarial_mob_tests.py::test_reservation_idempotency_rejects_changed_intent`, `test_assignment_idempotency_rejects_changed_intent` |
| Identity | Duplicate request detection | `test_duplicate_request_cannot_manufacture_second_asset` |
| Identity | Valid but unissued ID distinction | `test_valid_but_unissued_is_distinct_from_invalid` |
| Registry | Referential integrity | `migrations/001_mob.sql` foreign keys and fixture load tests |
| Registry | Installed migration discovery | `tests/test_installed_artifact.py::InstalledArtifactTests::test_installed_package_initializes_without_repository_migrations` |
| Registry | Append/supersede history | `test_append_supersede_preserves_history_and_current_view` |
| Registry | Current-view derivation | `asset_records_current` view and lookup tests |
| Registry | Interrupted or uncertain write behavior | `test_uncertain_commit_requires_reconciliation` |
| Registry | Duplicate intake | idempotency and duplicate request tests |
| Taxonomy | Valid Class/Category reference | assignment tests using seeded `taxonomy_terms` |
| Taxonomy | Optional precision may remain unassigned | `test_taxonomy_optional_precision_does_not_require_unknown_term` |
| Taxonomy | Stable references | schema stores `taxonomy_ref`, not display label alone |
| Taxonomy | Assignment state | `taxonomy_assignments.assignment_state` checks |
| Documentation | Evidence-reference identity | `evidence_references.evidence_ref` primary key |
| Documentation | Original/derivative separation | `original_or_derivative` check constraint |
| Documentation | Explicit original/derivative API and history | `qa_adversarial_mob_tests.py::test_original_derivative_states_are_explicit_and_historical` |
| Documentation | Continuity and broken locator preservation | `test_evidence_broken_locator_preserves_relationship` |
| Documentation | Locator repair preserves prior locator and evidence identity | `qa_adversarial_mob_tests.py::test_evidence_locator_repair_preserves_identity_and_history` |
| Documentation | Acceptance and completeness states | evidence schema and synthetic fixture coverage |
| Security | Authorized and denied access | `test_authorization_denial` |
| Security | Privilege separation | `auth.ActorContext` permissions |
| Security | Failed authorization audit | `qa_adversarial_mob_tests.py::test_authorization_failures_and_controlled_operations_are_audited` |
| Security | Restricted fail-closed handling | Restricted fixture contains no real secret and no AI/OCR path |
| Security | Secrets exclusion | fixture metadata and docs explicitly exclude secrets |
| Security | Export protection | `qa_adversarial_mob_tests.py::test_restricted_export_suppresses_protected_fields_and_hashes_payload` |
| Security | Audit attribution | reservation, assignment, publication, evidence, correction, export, backup, and restore events audited |
| Recovery | SQLite-consistent backup | `encrypted_backup` uses SQLite backup API |
| Recovery | Restore and reconciliation | `test_backup_restore_round_trip` |
| Recovery | History preservation | backup restore test plus history test |
| Recovery | Backup/restore audit and secret exclusion | `qa_adversarial_mob_tests.py::test_export_backup_restore_audit_events_and_no_cli_passphrase` |
| Export | Fidelity and integrity hash | `test_controlled_export_has_hash` |
| Search | Governed bounded search | `qa_adversarial_mob_tests.py::test_search_supports_name_taxonomy_external_identifier_and_evidence_ref` |
| Publication | Application-mediated publication gate | `qa_adversarial_mob_tests.py::test_publication_gate_blocks_incomplete_draft_and_publishes_valid_asset` |
| Publication | Conflict/rejected validation blocks publication | `qa_adversarial_mob_tests.py::test_publication_gate_blocks_conflict_validation_record` |

## QA-RR Correction Traceability

| Finding | Implementation surface | Test method | Expected result | Producer-observed result | Evidence location |
|---|---|---|---|---|---|
| QA-RR-001 | `AssetOSRegistry.validate_asset`, `AssetOSRegistry.publish_asset` | `python qa_adversarial_mob_tests.py -v` | Draft/invalid/conflict states fail closed; valid synthetic Asset publishes; audit emitted | Pass | `qa_adversarial_mob_tests.py` |
| QA-RR-002 | `reserve_asset_id`, `assign_asset` idempotency reconciliation | `python qa_adversarial_mob_tests.py -v` | Same request plus changed intended Asset key fails closed and is audited | Pass | `qa_adversarial_mob_tests.py` |
| QA-RR-003 | `controlled_export` minimum-disclosure profile | `python qa_adversarial_mob_tests.py -v` | Restricted descriptions, payloads, external IDs, and evidence locators suppressed unless explicitly authorized | Pass | `qa_adversarial_mob_tests.py` |
| QA-RR-004 | `_require_permission` and export denial audit | `python qa_adversarial_mob_tests.py -v` | Unauthorized reserve/export attempts produce `failed_access` audit events | Pass | `qa_adversarial_mob_tests.py` |
| QA-RR-005 | `controlled_export`, `encrypted_backup`, `restore_encrypted_backup` | `python qa_adversarial_mob_tests.py -v` | Export, backup, and restore emit attributable audit events | Pass | `qa_adversarial_mob_tests.py` |
| QA-RR-006 | `backup.py` in-process cryptography implementation | `python qa_adversarial_mob_tests.py -v` | Passphrase not exposed via command line, logs, output, or backup envelope | Pass | `qa_adversarial_mob_tests.py`, `src/assetos_mob/backup.py` |
| QA-RR-007 | `limited_search` joins Taxonomy, external IDs, and evidence refs | `python qa_adversarial_mob_tests.py -v` | Name, description, Class/Category, external ID, and evidence-reference search succeed without extra disclosure | Pass | `qa_adversarial_mob_tests.py` |
| QA-RR-008 | `repair_evidence_locator` and `evidence_locator_history` | `python qa_adversarial_mob_tests.py -v` | Repair preserves stable evidence identity, prior locator, actor, reason, time, and current locator | Pass | `qa_adversarial_mob_tests.py` |
| QA-RR-009 | `add_evidence_reference`, `set_evidence_state`, `evidence_state_history` | `python qa_adversarial_mob_tests.py -v` | Evidence state is explicit; invalid states fail; state changes preserve history | Pass | `qa_adversarial_mob_tests.py` |

## Admission-Readiness Correction Traceability

| Finding | Implementation surface | Test method | Expected result | Producer-observed result | Evidence location |
|---|---|---|---|---|---|
| DEP-INIT-001 | `assetos_mob.db` migration resolver and packaged `assetos_mob.migrations` resources | `python -m unittest discover -s tests -v` | Clean installed artifact discovers packaged `001_mob.sql`, records migration, seeds reference data, and does not depend on repository top-level `migrations` at runtime | Producer pass; independent installed-artifact QA verified candidate `82844ce60021033d47439e62cf8c4bc9f100c634` with evidence-custody condition | `tests/test_installed_artifact.py` |

## Remaining QA Work

Independent QA has verified QA-RR-001 through QA-RR-009 for the controlled non-operational release candidate. DEP-INIT-001 technical correction is independently verified; final lifecycle closure remains pending corrective release publication, clean Windows deployment verification, and applicable evidence-custody closure. Production admission testing remains subject to later activation-readiness controls, including production host hardening and real Google Drive continuity/reconciliation.
