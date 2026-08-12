# ARIR-014 Production Registry to Google Drive Evidence Contract

Control reference: `AOS-HO-00001`

State: Controlled Engineering deliverable / requires Architecture, Registry, Documentation, Security, and QA treatment before production use.

## Purpose

Define the minimum contract for a future production-connected Registry to Google Drive evidence integration. This package implements only the Registry-side evidence-reference model and synthetic Drive locator handling.

## Source and Destination

| Side | Authoritative role |
|---|---|
| Google Drive | Authoritative original-evidence repository |
| AssetOS Registry | Governed evidence-reference repository |
| Controlled derivatives/views | Non-authoritative presentation or review artifacts |

Exchange does not transfer authority.

## Identifier Rules

- `evidence_ref` is the stable Registry evidence-reference identity.
- Google Drive file ID, URL, path, folder, or filename is a locator/source attribute, not evidence identity.
- Drive rename or move must update locator history and must not create a new evidence identity by itself.
- Broken, unavailable, moved, access-denied, or recovery-pending locators preserve the evidence relationship.

## Permitted Writes

No production write is authorized by this engineering package.

A future production contract must explicitly identify whether any integration may:

- read Drive metadata;
- read original file content;
- create controlled derivatives;
- update Registry locator state;
- record locator repair history;
- write back to Drive;
- alter Drive permissions;
- rename files;
- move files.

The MOB development package assumes no Drive write permissions.

## Minimum Data Scope

Registry-side evidence references support:

- stable evidence-reference identity;
- Asset association;
- evidence type;
- Drive locator/source;
- original/derivative state;
- information class;
- provenance;
- capture/receipt time;
- event/effective time;
- creator/issuer/importer;
- continuity state;
- acceptance/review state;
- completeness state.

## Security and Privacy

- Public, Personal, Confidential, and Restricted classes remain independent of Taxonomy and lifecycle state.
- Restricted information is default-deny for AI/OCR/automation.
- Secrets must not be stored in ordinary Registry fields, evidence metadata, audit logs, exports, tests, or application payloads.
- Minimum disclosure applies to search, export, logs, and controlled derivatives.
- Controlled export evaluates requester authority, allowed information classes, and protected field sets before disclosing descriptions, payloads, external identifiers, or evidence locators.

## Failure Behavior

Failures fail closed and shall use explicit states:

- unavailable;
- broken;
- access denied;
- moved;
- recovery pending;
- preservation defect;
- disputed;
- rejected.

File presence alone does not establish evidence acceptance, Asset identity, or truth of propositions in the evidence.

## Reconciliation and Audit

Future production integration must audit:

- privileged evidence access;
- failed access;
- locator repair;
- continuity-state changes;
- acceptance-state changes;
- export;
- backup and restore effects on evidence references.

Audit logs are governed information and must not become a second uncontrolled Registry.

## Development-Tested Registry-Side Behavior

The MOB correction candidate implements synthetic, Registry-side behavior for:

- failed-closed authorization on evidence access and controlled export;
- locator repair through `repair_evidence_locator`, preserving evidence-reference identity and prior locator history;
- explicit original, derivative, working-copy, redacted, annotated, and export evidence states;
- bounded evidence-reference search by stable `evidence_ref`;
- minimum-disclosure export suppression for protected evidence locators;
- attributable audit events for export, backup, restore, publication, and denied access.

No real Google Drive connection, Drive metadata read, Drive content read, Drive write, permission change, rename, move, or migration is authorized or implemented by this correction.
