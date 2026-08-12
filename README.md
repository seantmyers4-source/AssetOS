# AssetOS Minimum Operational Baseline v0.1

Control reference: `AOS-HO-00001`

Release state: **Controlled / Non-production / Non-operational**.

This repository contains the controlled non-operational release package for the approved **AssetOS Minimum Operational Baseline Implementation Specification v0.1**.

The implementation is intentionally bounded:

- development/test SQLite Registry kernel only;
- synthetic and non-production fixtures only;
- no production Asset intake;
- no production permanent Asset-ID issuance;
- no production Google Drive restructuring or permission changes;
- no RuntimeOS execution, deployment, production admission, or AssetOS activation.

## Contents

- `src/assetos_mob/` — Python standard-library implementation.
- `migrations/001_mob.sql` — SQLite schema, constraints, WAL setup assumptions, and current-state views.
- `fixtures/synthetic_assets.json` — representative synthetic fixture set.
- `tests/` and `qa_adversarial_mob_tests.py` — producer baseline and bounded release-blocking correction coverage.
- `docs/` — implementation summary, release notes, ARIR-013 matrix, ARIR-014 Registry to Drive contract, assumptions, and unresolved defects.

## Quick Verification

```bash
python -m unittest discover -s tests
python qa_adversarial_mob_tests.py -v
```

## Production Boundary

Generated, reserved, and assigned identifiers in this package are test-environment events only:

```text
generated test ID != production Asset ID
reserved test ID != production reservation
assigned test ID != production canonical identity
test Registry != production Registry
```

The package is suitable for controlled non-production release readback, not production operation.
