CREATE TABLE provider_namespaces (
  provider_namespace TEXT PRIMARY KEY CHECK (
    provider_namespace IN ('google_drive')
  ),
  description TEXT NOT NULL
);

INSERT OR IGNORE INTO provider_namespaces(provider_namespace, description)
VALUES ('google_drive', 'Google Drive file provider namespace');

ALTER TABLE evidence_references ADD COLUMN provider_namespace TEXT REFERENCES provider_namespaces(provider_namespace);
ALTER TABLE evidence_references ADD COLUMN provider_object_id TEXT;
ALTER TABLE evidence_references ADD COLUMN canonical_locator TEXT;
ALTER TABLE evidence_references ADD COLUMN display_name TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS ux_evidence_provider_identity
ON evidence_references(provider_namespace, provider_object_id)
WHERE provider_namespace IS NOT NULL AND provider_object_id IS NOT NULL;

CREATE TABLE evidence_locator_annotations (
  locator_annotation_id INTEGER PRIMARY KEY,
  locator_history_id INTEGER NOT NULL REFERENCES evidence_locator_history(locator_history_id),
  annotation_type TEXT NOT NULL CHECK (
    annotation_type IN ('no_op_repair_attempt', 'not_canonical_locator_transition')
  ),
  annotation TEXT NOT NULL,
  actor TEXT NOT NULL,
  authority TEXT NOT NULL,
  recorded_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
