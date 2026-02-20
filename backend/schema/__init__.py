"""Canonical schema package -- public API re-exports."""

from backend.schema.canonical import (
    AccountsProfile,
    CanonicalPlanSchema,
    ClientProfile,
    FlexibilityOptions,
    HousingProfile,
    IncomeProfile,
    LocationProfile,
    MonteCarloConfig,
    NumericRange,
    PlanStatus,
    PlannedCashflow,
    RetirementPhilosophy,
    RiskSummary,
    SocialSecurityProfile,
    SpendingProfile,
)
from backend.schema.migrations import yaml_plan_to_canonical
from backend.schema.patch_ops import (
    PatchOp,
    PatchResponse,
    PatchResult,
    apply_patches,
)
from backend.schema.provenance import FieldSource, ProvenanceField
from backend.schema.snapshots import (
    MemorySnapshotStore,
    SchemaSnapshot,
    SnapshotStore,
    create_snapshot,
)

__all__ = [
    "AccountsProfile",
    "CanonicalPlanSchema",
    "ClientProfile",
    "FieldSource",
    "FlexibilityOptions",
    "HousingProfile",
    "IncomeProfile",
    "LocationProfile",
    "MemorySnapshotStore",
    "MonteCarloConfig",
    "NumericRange",
    "PatchOp",
    "PatchResponse",
    "PatchResult",
    "PlanStatus",
    "PlannedCashflow",
    "ProvenanceField",
    "RetirementPhilosophy",
    "RiskSummary",
    "SchemaSnapshot",
    "SnapshotStore",
    "SocialSecurityProfile",
    "SpendingProfile",
    "apply_patches",
    "create_snapshot",
    "yaml_plan_to_canonical",
]
