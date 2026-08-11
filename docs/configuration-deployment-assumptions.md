# Configuration and Deployment Assumptions

Control reference: `AOS-HO-00001`

## Development Assumptions

- Python 3.11 or newer.
- SQLite available through Python standard library.
- OpenSSL command-line utility available for encrypted backup and restore tests.
- Test data is synthetic.
- Local files are development artifacts, not production Registry files.

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
