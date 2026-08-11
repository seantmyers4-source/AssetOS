# AssetOS MOB Implementation Architecture Summary

Control reference: `AOS-HO-00001`

## Controlling Inputs Inspected

- AssetOS Minimum Operational Baseline Implementation Specification v0.1, Google Doc `13-cVtmcIEltbTxr0xFLLIHLpT_QbJFiEhaQ7uNvW38M`, controlled revision `AIroW36G11G6P5SrnxGmKCcqwAozSl2q2P_UNU2MdXBoXMAZGJNFkn3eYUkCZ4oEFp5FPppbEL49omsa3-9pysM1IaSJG-zhfR60v_3wpoak`.
- Identification & Labeling Foundation Candidate v0.1 controlled check-symbol revision.
- Security & Privacy Foundation Candidate v0.1.
- Foundation Interface Baseline v0.1 with ARIR-013 and ARIR-014 carried conditions.

## Implementation Boundary

This is a controlled development/test implementation. It creates no production Registry, performs no real Asset intake, issues no production permanent Asset IDs, changes no Google Drive evidence, and activates no production runtime.

## Runtime Shape

- Python standard-library implementation under `src/assetos_mob`.
- SQLite physical Registry kernel initialized from `migrations/001_mob.sql`.
- Application-mediated access through `AssetOSRegistry`; tests do not require direct user manipulation of SQLite.
- WAL mode, foreign keys, full synchronous mode, and controlled schema migration setup.
- Synthetic fixtures only.

## Implemented MOB Capabilities

- Asset-ID candidate generation and validation.
- Transactional reservation and assignment workflow.
- Idempotent request handling.
- Duplicate active reservation prevention.
- Assignment without valid reservation prevention.
- Uncertain-commit fail-closed simulation.
- Canonical Asset creation.
- Append/supersede canonical assertion history.
- Derived `asset_records_current` view.
- Minimum Taxonomy reference storage: Asset to Class to Category with optional Subcategory/Type unassigned.
- Four approved information classes.
- Evidence references with Drive locator, provenance, continuity, acceptance, and completeness states.
- Bounded exact lookup and limited search.
- Controlled export with integrity hash.
- SQLite-consistent encrypted backup using `sqlite3.Connection.backup` and OpenSSL AES-256-CBC with PBKDF2.
- Restore with backup integrity verification.
- Attributable audit events.

## Current-State Projection

`asset_records_current` is implemented as a derived SQLite view over active, non-superseded canonical assertions. It is not independently writable canonical truth.

## Production Holds Preserved

- Production AI/OCR disabled.
- QR/label production deferred.
- Production Google Drive integration deferred pending ARIR-014 contract approval.
- RuntimeOS execution, release, deployment, and AssetOS activation remain unauthorized.
