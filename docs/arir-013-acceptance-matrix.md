# ARIR-013 Acceptance Matrix

Control reference: `AOS-HO-00001`

This matrix maps the approved ARIR-013 implementation-measurement requirements into reproducible producer tests. It is not independent QA certification.

| Area | Requirement | Producer evidence |
|---|---|---|
| Identity | Syntax, allowed characters, length, check symbol | `tests/test_identifiers.py::IdentifierTests` |
| Identity | Approved deterministic check vectors | `test_approved_deterministic_vectors` |
| Identity | Invalid check cannot reserve or assign | `test_identity_invalid_check_cannot_reserve`, `test_invalid_check_symbol_fails_closed` |
| Identity | Uniqueness and reservation | `test_duplicate_active_reservation_is_rejected` |
| Identity | Assignment requires reservation | `test_assignment_without_reservation_is_rejected` |
| Identity | Idempotency and retry | `test_reservation_and_assignment_are_idempotent_by_request` |
| Identity | Duplicate request detection | `test_duplicate_request_cannot_manufacture_second_asset` |
| Identity | Valid but unissued ID distinction | `test_valid_but_unissued_is_distinct_from_invalid` |
| Registry | Referential integrity | `migrations/001_mob.sql` foreign keys and fixture load tests |
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
| Documentation | Continuity and broken locator preservation | `test_evidence_broken_locator_preserves_relationship` |
| Documentation | Acceptance and completeness states | evidence schema and synthetic fixture coverage |
| Security | Authorized and denied access | `test_authorization_denial` |
| Security | Privilege separation | `auth.ActorContext` permissions |
| Security | Restricted fail-closed handling | Restricted fixture contains no real secret and no AI/OCR path |
| Security | Secrets exclusion | fixture metadata and docs explicitly exclude secrets |
| Security | Export protection | controlled export is minimum-disclosure and hash-attributed |
| Security | Audit attribution | reservation, assignment, evidence, correction events audited |
| Recovery | SQLite-consistent backup | `encrypted_backup` uses SQLite backup API |
| Recovery | Restore and reconciliation | `test_backup_restore_round_trip` |
| Recovery | History preservation | backup restore test plus history test |
| Export | Fidelity and integrity hash | `test_controlled_export_has_hash` |

## Remaining QA Work

Independent QA should inspect the schema, run the tests in a clean environment, add adversarial fixtures, and verify that no implementation path can silently convert generated/reserved/assigned development IDs into production identifiers.
