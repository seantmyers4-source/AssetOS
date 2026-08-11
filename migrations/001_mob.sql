PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;

CREATE TABLE information_classes (
  information_class TEXT PRIMARY KEY CHECK (
    information_class IN ('Public', 'Personal', 'Confidential', 'Restricted')
  )
);

CREATE TABLE taxonomy_terms (
  taxonomy_ref TEXT PRIMARY KEY,
  root TEXT NOT NULL CHECK (root = 'Asset'),
  class TEXT NOT NULL,
  category TEXT NOT NULL,
  subcategory TEXT,
  type TEXT,
  state TEXT NOT NULL DEFAULT 'verified'
    CHECK (state IN ('intake_suggestion', 'proposed', 'verified', 'disputed', 'superseded')),
  UNIQUE(root, class, category, subcategory, type)
);

CREATE TABLE asset_id_reservations (
  asset_id TEXT PRIMARY KEY,
  body TEXT NOT NULL UNIQUE,
  check_symbol TEXT NOT NULL,
  state TEXT NOT NULL CHECK (
    state IN ('reserved', 'assigned', 'failed_conflict', 'expired', 'protected')
  ),
  request_id TEXT NOT NULL UNIQUE,
  intended_asset_key TEXT NOT NULL,
  reserved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reserved_by TEXT NOT NULL,
  reserved_authority TEXT NOT NULL,
  assigned_asset_uuid TEXT UNIQUE,
  assigned_at TEXT,
  historical_protection_reason TEXT,
  FOREIGN KEY(assigned_asset_uuid) REFERENCES assets(asset_uuid)
);

CREATE TABLE assets (
  asset_uuid TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL UNIQUE,
  assignment_request_id TEXT NOT NULL UNIQUE,
  intended_asset_key TEXT NOT NULL,
  preferred_name TEXT NOT NULL,
  description TEXT NOT NULL,
  record_state TEXT NOT NULL CHECK (
    record_state IN ('draft', 'active', 'suspended', 'retired', 'merged', 'rejected')
  ),
  validation_state TEXT NOT NULL CHECK (
    validation_state IN ('pending', 'review_required', 'valid', 'invalid', 'conflict', 'rejected')
  ),
  publication_state TEXT NOT NULL CHECK (
    publication_state IN ('unpublished', 'published', 'withdrawn')
  ),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by TEXT NOT NULL,
  created_authority TEXT NOT NULL,
  FOREIGN KEY(asset_id) REFERENCES asset_id_reservations(asset_id)
);

CREATE TABLE asset_assertions (
  assertion_id TEXT PRIMARY KEY,
  asset_uuid TEXT NOT NULL REFERENCES assets(asset_uuid),
  assertion_type TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
  effective_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  reason TEXT NOT NULL,
  source_evidence_ref TEXT,
  change_kind TEXT NOT NULL CHECK (change_kind IN ('genuine_change', 'correction')),
  dispute_state TEXT NOT NULL CHECK (
    dispute_state IN ('none', 'disputed', 'exception', 'review_required')
  ),
  supersedes_assertion_id TEXT REFERENCES asset_assertions(assertion_id),
  superseded_at TEXT
);

CREATE TABLE taxonomy_assignments (
  taxonomy_assignment_id INTEGER PRIMARY KEY,
  asset_uuid TEXT NOT NULL REFERENCES assets(asset_uuid),
  taxonomy_ref TEXT NOT NULL REFERENCES taxonomy_terms(taxonomy_ref),
  assignment_state TEXT NOT NULL CHECK (
    assignment_state IN ('intake_suggestion', 'proposed', 'verified', 'disputed', 'superseded')
  ),
  effective_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  reason TEXT NOT NULL,
  superseded_at TEXT
);

CREATE TABLE information_class_assignments (
  information_class_assignment_id INTEGER PRIMARY KEY,
  asset_uuid TEXT NOT NULL REFERENCES assets(asset_uuid),
  information_class TEXT NOT NULL REFERENCES information_classes(information_class),
  assignment_state TEXT NOT NULL CHECK (
    assignment_state IN ('intake_suggestion', 'proposed', 'verified', 'disputed', 'superseded')
  ),
  effective_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  reason TEXT NOT NULL,
  superseded_at TEXT
);

CREATE TABLE location_assignments (
  location_assignment_id INTEGER PRIMARY KEY,
  asset_uuid TEXT NOT NULL REFERENCES assets(asset_uuid),
  location_ref TEXT NOT NULL,
  assignment_state TEXT NOT NULL DEFAULT 'not_assessed',
  effective_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  superseded_at TEXT
);

CREATE TABLE ownership_custody_assignments (
  ownership_assignment_id INTEGER PRIMARY KEY,
  asset_uuid TEXT NOT NULL REFERENCES assets(asset_uuid),
  ownership_ref TEXT NOT NULL,
  custody_ref TEXT,
  assignment_state TEXT NOT NULL DEFAULT 'unresolved',
  effective_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  superseded_at TEXT
);

CREATE TABLE evidence_references (
  evidence_ref TEXT PRIMARY KEY,
  asset_uuid TEXT NOT NULL REFERENCES assets(asset_uuid),
  evidence_type TEXT NOT NULL,
  drive_locator TEXT,
  original_or_derivative TEXT NOT NULL CHECK (original_or_derivative IN ('original', 'derivative')),
  information_class TEXT NOT NULL REFERENCES information_classes(information_class),
  provenance_json TEXT NOT NULL CHECK (json_valid(provenance_json)),
  capture_time TEXT,
  event_time TEXT,
  creator_issuer_importer TEXT,
  continuity_state TEXT NOT NULL CHECK (
    continuity_state IN ('available', 'unavailable', 'broken', 'access_denied', 'moved', 'recovery_pending', 'preservation_defect')
  ),
  acceptance_state TEXT NOT NULL CHECK (
    acceptance_state IN ('captured', 'associated', 'reviewed', 'accepted_identity_support', 'disputed', 'rejected', 'unavailable')
  ),
  completeness_state TEXT NOT NULL CHECK (
    completeness_state IN ('not_assessed', 'not_required', 'missing', 'partial', 'sufficient', 'complete', 'exception_waiver', 'preservation_unavailable')
  ),
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evidence_locator_history (
  locator_history_id INTEGER PRIMARY KEY,
  evidence_ref TEXT NOT NULL REFERENCES evidence_references(evidence_ref),
  prior_drive_locator TEXT,
  new_drive_locator TEXT,
  continuity_state TEXT NOT NULL,
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  reason TEXT NOT NULL,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE external_identifiers (
  external_identifier_id INTEGER PRIMARY KEY,
  asset_uuid TEXT NOT NULL REFERENCES assets(asset_uuid),
  identifier_type TEXT NOT NULL,
  normalized_value TEXT NOT NULL,
  display_value TEXT,
  issuer_namespace TEXT NOT NULL,
  source_evidence_ref TEXT REFERENCES evidence_references(evidence_ref),
  verification_state TEXT NOT NULL DEFAULT 'proposed',
  information_class TEXT NOT NULL REFERENCES information_classes(information_class),
  ambiguity_flag INTEGER NOT NULL DEFAULT 0 CHECK (ambiguity_flag IN (0, 1)),
  superseded_at TEXT,
  UNIQUE(identifier_type, normalized_value, issuer_namespace, superseded_at)
);

CREATE TABLE relationships (
  relationship_id INTEGER PRIMARY KEY,
  source_asset_uuid TEXT NOT NULL REFERENCES assets(asset_uuid),
  relationship_type TEXT NOT NULL,
  target_asset_uuid TEXT REFERENCES assets(asset_uuid),
  target_external_ref TEXT,
  relationship_state TEXT NOT NULL DEFAULT 'proposed',
  effective_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  superseded_at TEXT,
  CHECK (target_asset_uuid IS NOT NULL OR target_external_ref IS NOT NULL)
);

CREATE TABLE validation_records (
  validation_record_id INTEGER PRIMARY KEY,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  validation_type TEXT NOT NULL,
  validation_state TEXT NOT NULL CHECK (
    validation_state IN ('unknown', 'invalid', 'pending', 'stale', 'unavailable', 'conflict', 'review_required', 'rejected', 'valid')
  ),
  details_json TEXT NOT NULL CHECK (json_valid(details_json)),
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE change_events (
  change_event_id INTEGER PRIMARY KEY,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  change_type TEXT NOT NULL,
  prior_state_json TEXT CHECK (prior_state_json IS NULL OR json_valid(prior_state_json)),
  new_state_json TEXT CHECK (new_state_json IS NULL OR json_valid(new_state_json)),
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  reason TEXT NOT NULL,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_events (
  audit_event_id INTEGER PRIMARY KEY,
  event_type TEXT NOT NULL CHECK (
    event_type IN (
      'failed_access', 'privileged_access', 'permission_configuration_change',
      'asset_id_reservation', 'permanent_assignment', 'publication',
      'correction_supersession', 'export', 'backup', 'restore',
      'destructive_administrative_action', 'evidence_reference_access'
    )
  ),
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  subject_id TEXT,
  event_payload_json TEXT NOT NULL CHECK (json_valid(event_payload_json)),
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE controlled_exports (
  export_id INTEGER PRIMARY KEY,
  export_version TEXT NOT NULL,
  export_timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  integrity_hash TEXT NOT NULL,
  minimum_disclosure_profile TEXT NOT NULL,
  actor TEXT NOT NULL,
  authority TEXT NOT NULL
);

CREATE VIEW asset_records_current AS
SELECT
  a.asset_uuid,
  a.asset_id,
  a.preferred_name,
  a.description,
  a.record_state,
  a.validation_state,
  a.publication_state,
  aa.assertion_id AS current_assertion_id,
  aa.payload_json AS current_payload_json,
  aa.effective_time,
  aa.recorded_time
FROM assets a
JOIN asset_assertions aa ON aa.asset_uuid = a.asset_uuid
WHERE aa.assertion_type = 'canonical_record'
  AND aa.superseded_at IS NULL;
