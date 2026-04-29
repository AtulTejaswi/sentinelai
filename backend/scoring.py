from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List

from auth import get_current_user
from models import User

router = APIRouter()

class ScoringRequest(BaseModel):
    user_id: str
    behavioral: dict
    ip_address: str
    email: str
    user_agent: str
    registrations_from_ip_last_hour: int

@router.post("")
def calculate_score(req: ScoringRequest, current_user: User = Depends(get_current_user)):
    # This is a stub for Akash's scoring engine
    # In real use, this would call scorer.py and ml_model.py
    
    trust_score = 100
    triggered_rules = []
    recommendation = "allow"
    
    # Simple logic
    if req.behavioral.get("time_to_complete_sec", 10) < 4:
        trust_score = 18
        triggered_rules.append("speed_bot")
        recommendation = "quarantine"
        
    return {
        "trust_score": trust_score,
        "ml_anomaly_score": 0.0,
        "triggered_rules": triggered_rules,
        "recommendation": recommendation
    }
