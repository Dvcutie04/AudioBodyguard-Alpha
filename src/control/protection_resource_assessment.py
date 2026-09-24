from dataclasses import dataclass
from enum import Enum

from src.edge.resource_governor import AdmissionDecision


class ProtectionResourceReason(str,Enum):
    ADMITTED="ADMITTED"
    MEMORY_BUDGET_EXCEEDED="MEMORY_BUDGET_EXCEEDED"
    LATENCY_BUDGET_EXCEEDED="LATENCY_BUDGET_EXCEEDED"
    LOW_POWER_ENERGY_REJECTED="LOW_POWER_ENERGY_REJECTED"
    THERMAL_PRESSURE_REJECTED="THERMAL_PRESSURE_REJECTED"
    INVALID_RESOURCE_DECISION="INVALID_RESOURCE_DECISION"


class ProtectionRemediationAction(str,Enum):
    UNLOAD_OPTIONAL_MODELS="UNLOAD_OPTIONAL_MODELS"
    SELECT_LOWER_LATENCY_MODEL="SELECT_LOWER_LATENCY_MODEL"
    SELECT_LOWER_ENERGY_MODEL="SELECT_LOWER_ENERGY_MODEL"
    WAIT_FOR_THERMAL_RECOVERY="WAIT_FOR_THERMAL_RECOVERY"
    REDUCE_EXECUTION_TIER="REDUCE_EXECUTION_TIER"


@dataclass(frozen=True,slots=True)
class ProtectionResourceAssessment:
    eligible: bool
    reason: ProtectionResourceReason
    remediation_actions: tuple[ProtectionRemediationAction,...]

    @classmethod
    def from_admission(cls,decision) -> "ProtectionResourceAssessment":
        invalid=cls(False,ProtectionResourceReason.INVALID_RESOURCE_DECISION,())
        if not isinstance(decision,AdmissionDecision) or type(decision.admitted) is not bool or not isinstance(decision.reason,str):
            return invalid
        if decision.admitted is True:
            if decision.reason!="ADMITTED" or decision.selected_accelerator is None:
                return invalid
            return cls(True,ProtectionResourceReason.ADMITTED,())
        if decision.selected_accelerator is not None:
            return invalid
        if decision.reason=="MEMORY_BUDGET_EXCEEDED":
            return cls(False,ProtectionResourceReason.MEMORY_BUDGET_EXCEEDED,(ProtectionRemediationAction.UNLOAD_OPTIONAL_MODELS,ProtectionRemediationAction.REDUCE_EXECUTION_TIER))
        if decision.reason=="LATENCY_BUDGET_EXCEEDED":
            return cls(False,ProtectionResourceReason.LATENCY_BUDGET_EXCEEDED,(ProtectionRemediationAction.SELECT_LOWER_LATENCY_MODEL,ProtectionRemediationAction.REDUCE_EXECUTION_TIER))
        if decision.reason=="LOW_POWER_ENERGY_REJECTED":
            return cls(False,ProtectionResourceReason.LOW_POWER_ENERGY_REJECTED,(ProtectionRemediationAction.SELECT_LOWER_ENERGY_MODEL,ProtectionRemediationAction.REDUCE_EXECUTION_TIER))
        if decision.reason=="THERMAL_PRESSURE_REJECTED":
            return cls(False,ProtectionResourceReason.THERMAL_PRESSURE_REJECTED,(ProtectionRemediationAction.WAIT_FOR_THERMAL_RECOVERY,ProtectionRemediationAction.SELECT_LOWER_ENERGY_MODEL))
        return invalid
