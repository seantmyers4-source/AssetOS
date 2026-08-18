# AssetOS Minimum Operational Baseline v0.1.2 Corrective Candidate Notes

Control reference: `AOS-HO-00001`

Release state: **Controlled / Non-production / Non-operational**

Parent baseline: `mob-v0.1.1` at `25a32c2aa54f04719e7a48f782b37f5f63a4266c`

Finding: `AOS-PROD-001 — Canonical Evidence Locator Representation / Provider Identity Data-Model Gap`

Corrective candidate identity: `mob-v0.1.2`

Candidate custody lineage: `CUSTODY-R2`

## Summary

AssetOS MOB v0.1.2 is a bounded corrective candidate for provider identity and canonical evidence-locator semantics. It addresses the data-model gap exposed by the first controlled production Asset admission without mutating the existing production Registry.

This candidate does not authorize production Registry migration, further locator repair, validation, publication, second Asset admission, RuntimeOS execution, or AssetOS activation.

## Corrective Scope

- Establishes first-class provider identity fields for evidence references.
- Defines governed provider namespace `google_drive`.
- Preserves immutable provider object ID separately from provenance JSON.
- Defines canonical Google Drive locator format `gdrive://file/<provider_object_id>`.
- Separates canonical locator from human/display filename.
- Validates provider namespace, provider object ID, and canonical locator consistency.
- Requires provider-identity reconciliation before provider-connected locator repair.
- Rejects same-value/no-op locator repair as a locator repair.
- Adds governed locator-history annotation for no-op repair attempts without rewriting historical events.
- Preserves authorization, audit, backup/restore, and minimum-disclosure controls.

## Production State Preserved

The existing production Asset remains authoritative and is not changed by this candidate:

- Asset ID: `AOS-P39J-030Z-B4RH-Q116-M`
- Asset UUID: `5e20035e-0a14-4bd4-bc6e-f085f9eff2b4`
- Evidence reference: `AOS-FIRST-PROD-EVIDENCE-001`
- Verified provider: `google_drive`
- Verified provider object ID: `1aH_sXVfWyGq9Y7KXA-wj7GCBhR1jW9uR`
- Target canonical locator after separately authorized production correction: `gdrive://file/1aH_sXVfWyGq9Y7KXA-wj7GCBhR1jW9uR`

The target canonical locator is specification input only. It is not written to production by this candidate.

## Regression Coverage

Producer coverage verifies:

- v0.1.1 to v0.1.2 synthetic schema migration;
- permanent Asset identity preservation;
- evidence-reference identity preservation;
- provider-object identity preservation;
- canonical locator derivation;
- malformed locator rejection;
- mismatched provider-ID/locator rejection;
- same-filename wrong-object rejection;
- no-op repair rejection;
- valid locator correction and history;
- historical no-op locator event annotation without rewriting history;
- provider identity through backup/restore;
- authorization enforcement;
- audit attribution;
- minimum-disclosure/export behavior;
- clean initialization of a fresh corrective-release Registry.

The installed-artifact regression builds the candidate wheel in the controlled producer environment, then installs that prebuilt wheel into an isolated virtual environment using `--no-deps --no-index`. This keeps the test focused on installed package-resource behavior and avoids treating missing PEP 517 build-backend packages inside a bare runtime venv as an AssetOS runtime defect.

`CUSTODY-R2` supersedes all prior unpublished v0.1.2 transfer bundles after a publication-verification custody discrepancy involving the transferred installed-artifact test harness. It preserves the AOS-PROD-001 implementation scope and records the corrected wheel-first test-harness state in this candidate lineage.

## QA-ACT-002

`QA-ACT-002` remains **Verified with Conditions**. `AOS-PROD-001` does not invalidate the prior real-provider continuity campaign; it refines the production representation model exposed by first admission.

## Production Freeze

Until independent QA and separate production-migration authority:

- `AOS-PROD-001`: **Open**.
- Production Registry migration: **Prohibited**.
- Further locator repair: **Prohibited**.
- Validation: **Held**.
- Publication: **Held**.
- Second Asset admission: **Held**.
- General activation: **Not authorized**.
