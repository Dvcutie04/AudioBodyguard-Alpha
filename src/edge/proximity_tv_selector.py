from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ProximityEvidence:
    device_id: str
    distance_m: float
    observed_at: float
    eligible: bool


def _finite_number(value):
    return type(value) in (int,float) and math.isfinite(value)


def select_nearest_tv(evidence, *, now, radius_m, max_age_s, ambiguity_m, switch_margin_m, current_device_id=None):
    """Select from trusted eligibility and measured proximity; grant no authority."""
    settings=(now,radius_m,max_age_s,ambiguity_m,switch_margin_m)
    if not all(_finite_number(value) for value in settings):
        raise ValueError("selection settings must be finite numbers")
    if radius_m<=0 or max_age_s<=0 or ambiguity_m<0 or switch_margin_m<ambiguity_m:
        raise ValueError("invalid proximity selection settings")
    candidates=[]
    seen=set()
    for item in evidence:
        if not isinstance(item,ProximityEvidence):
            return None
        if type(item.device_id) is not str or not item.device_id.strip():
            return None
        if item.device_id in seen:
            return None
        seen.add(item.device_id)
        if item.eligible is not True:
            continue
        if not _finite_number(item.distance_m) or not _finite_number(item.observed_at):
            continue
        if not 0<=item.distance_m<=radius_m or not 0<=now-item.observed_at<=max_age_s:
            continue
        candidates.append(item)
    candidates.sort(key=lambda item:(item.distance_m,item.device_id))
    if not candidates:
        return None
    nearest=candidates[0]
    current=next((item for item in candidates if item.device_id==current_device_id),None)
    if current is not None and current.distance_m-nearest.distance_m<=switch_margin_m:
        return current.device_id
    if len(candidates)>1 and candidates[1].distance_m-nearest.distance_m<=ambiguity_m:
        return None
    return nearest.device_id
