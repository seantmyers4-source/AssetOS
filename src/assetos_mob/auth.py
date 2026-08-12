"""Minimal authorization separation for the MOB development kernel."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import AuthorizationError

READ = "read"
INTAKE_CREATE = "intake_create"
VALIDATION = "validation"
RESERVATION = "reservation"
ASSIGNMENT = "assignment"
PUBLICATION = "publication"
CORRECTION = "correction_supersession"
EVIDENCE_REFERENCE_ACCESS = "evidence_reference_access"
EXPORT = "export"
BACKUP = "backup"
RESTORE = "restore"
ADMINISTRATION = "administration"
DESTRUCTIVE_ADMIN = "destructive_administrative_action"

ALL_PERMISSIONS = {
    READ,
    INTAKE_CREATE,
    VALIDATION,
    RESERVATION,
    ASSIGNMENT,
    PUBLICATION,
    CORRECTION,
    EVIDENCE_REFERENCE_ACCESS,
    EXPORT,
    BACKUP,
    RESTORE,
    ADMINISTRATION,
    DESTRUCTIVE_ADMIN,
}


@dataclass(frozen=True)
class ActorContext:
    actor: str
    authority: str
    permissions: frozenset[str]

    def require(self, permission: str) -> None:
        if permission not in ALL_PERMISSIONS:
            raise AuthorizationError(f"unknown permission: {permission}")
        if permission not in self.permissions:
            raise AuthorizationError(f"{self.actor} lacks {permission}")

    def can(self, permission: str) -> bool:
        if permission not in ALL_PERMISSIONS:
            raise AuthorizationError(f"unknown permission: {permission}")
        return permission in self.permissions


ENGINEERING_TEST_ACTOR = ActorContext(
    actor="assetos-engineering-test",
    authority="AssetOS Engineering & Automation / synthetic development",
    permissions=frozenset(ALL_PERMISSIONS - {DESTRUCTIVE_ADMIN}),
)
