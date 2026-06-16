from fastapi import APIRouter
from trading_core.config import AppConfig
from trading_core.risk.kill_switch import KillSwitch

router = APIRouter(prefix="/api/risk", tags=["risk"])
_kill_switch = KillSwitch(AppConfig().risk)


@router.get("/state")
def get_risk_state() -> dict[str, object]:
    return {"kill_switch_active": _kill_switch.active, "reason": _kill_switch.reason}


@router.post("/kill-switch/activate")
def activate_kill_switch() -> dict[str, object]:
    _kill_switch.activate("api manual activation")
    return get_risk_state()


@router.post("/kill-switch/deactivate")
def deactivate_kill_switch() -> dict[str, object]:
    _kill_switch.deactivate()
    return get_risk_state()
