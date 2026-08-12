# Unresolved Defect Register

Control reference: `AOS-HO-00001`

## Current Status

Engineering has implemented bounded corrections for QA-RR-001 through QA-RR-009. Producer status is:

**Correction implemented / Pending independent QA**

No independent QA defect is marked finally closed by Engineering.

## Release-Blocking QA Findings

| Finding | Prior status | Correction commit | Implementation change | Test evidence | Producer disposition | QA status |
|---|---|---|---|---|---|---|
| QA-RR-001 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Added application-mediated validation/publication gate with fail-closed prerequisites and publication audit | `qa_adversarial_mob_tests.py::test_publication_gate_blocks_incomplete_draft_and_publishes_valid_asset`, `test_publication_gate_blocks_conflict_validation_record` | Correction implemented | Pending independent QA |
| QA-RR-002 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Reconciled idempotency against original Asset ID and intended Asset key for reservation and assignment | `test_reservation_idempotency_rejects_changed_intent`, `test_assignment_idempotency_rejects_changed_intent` | Correction implemented | Pending independent QA |
| QA-RR-003 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Replaced whole-current-record export with minimum-disclosure profile and protected-field suppression | `test_restricted_export_suppresses_protected_fields_and_hashes_payload` | Correction implemented | Pending independent QA |
| QA-RR-004 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Added attributable failed-access audit events for denied mediated operations | `test_authorization_failures_and_controlled_operations_are_audited` | Correction implemented | Pending independent QA |
| QA-RR-005 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Added export, backup, and restore audit events | `test_export_backup_restore_audit_events_and_no_cli_passphrase` | Correction implemented | Pending independent QA |
| QA-RR-006 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Replaced OpenSSL command-line secret transport with in-process authenticated encryption | `test_export_backup_restore_audit_events_and_no_cli_passphrase` | Correction implemented | Pending independent QA |
| QA-RR-007 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Expanded bounded search to preferred name/description, Taxonomy, external IDs, and evidence refs while limiting disclosure | `test_search_supports_name_taxonomy_external_identifier_and_evidence_ref` | Correction implemented | Pending independent QA |
| QA-RR-008 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Added controlled evidence locator repair with prior-locator history | `test_evidence_locator_repair_preserves_identity_and_history` | Correction implemented | Pending independent QA |
| QA-RR-009 | Release-blocking | `0a26b75975c710e75e25c93848006a6337a4810f` | Added explicit evidence original/derivative state API and state history | `test_original_derivative_states_are_explicit_and_historical` | Correction implemented | Pending independent QA |

## Non-Blocking Limitations

| ID | Title | Classification | Severity | Required disposition |
|---|---|---|---|---|
| AOS-ENG-LIM-001 | Production host hardening not implemented | Authorized deferral | Medium | Resolve before production release readiness. |
| AOS-ENG-LIM-002 | Production Google Drive connector not implemented | Authorized deferral / ARIR-014 dependency | High | Complete controlled ARIR-014 contract review before production-connected integration. |
| AOS-ENG-LIM-003 | AI/OCR production pipeline absent | Authorized production hold | Low | Preserve hold unless future authority authorizes AI/OCR. |
| QA-ACT-001 | Production host hardening not demonstrated | Activation-blocking | High | Resolve through later deployment/admission controls. |
| QA-ACT-002 | Real Drive continuity/reconciliation not tested | Activation-blocking | High | Resolve through later deployment/admission controls. |
| AOS-ENG-LIM-005 | Authorization model is minimal development kernel | Engineering implementation limitation | Medium | Replace or harden before production admission. |

These limitations do not authorize implementation drift or production activation.
