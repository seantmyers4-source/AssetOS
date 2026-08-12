# Configuration and Deployment Assumptions

Control reference: `AOS-HO-00001`

## Development Assumptions

- Python 3.11 or newer.
- SQLite available through Python standard library.
- Python `cryptography` dependency available as declared in `pyproject.toml`.
- Test data is synthetic.
- Local files are development artifacts, not production Registry files.

## Bounded Backup Cryptography Assumptions

The controlled non-operational MOB v0.1 release candidate uses the tested in-process Python backup mechanism:

- Python `cryptography`;
- Fernet authenticated encryption;
- PBKDF2-HMAC-SHA256;
- random 16-byte salt per encrypted backup envelope;
- 600,000 PBKDF2 iterations;
- in-process passphrase handling.

OpenSSL command-line encryption is not the active MOB backup implementation.

Release acceptance of this bounded cryptographic implementation does not constitute production approval of secret handling, backup storage, host protection, recovery procedures, or operational key/passphrase management. Those matters remain subject to later competent Security & Privacy and Architecture & Standards approval before production admission or activation.

## SQLite Host Protection Assumptions

The implementation assumes a future trusted private host with:

- encrypted storage;
- protected OS account;
- device locking;
- controlled physical access;
- patching;
- reasonable endpoint protection;
- no public/shared filesystem;
- application-mediated ordinary use.

Database, WAL, SHM, temporary files, restored copies, and backups inherit applicable protection requirements.

## Deployment Assumptions

No production deployment is authorized.

Before production readiness, Engineering must receive competent approval for:

- production host pattern;
- production backup storage location;
- production secret-handling mechanism;
- production Drive integration contract;
- production access model;
- release gate;
- RuntimeOS or operational admission where applicable.
