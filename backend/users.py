from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from database import get_db
from models import User, Event
from auth import get_current_user

router = APIRouter()

class StatusUpdateRequest(BaseModel):
    status: str

@router.get("")
def get_users(
    status: Optional[str] = None,
    min_trust: Optional[int] = None,
    max_trust: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    query = db.query(User)
    
    if status:
        query = query.filter(User.status == status)
    if min_trust is not None:
        query = query.filter(User.trust_score >= min_trust)
    if max_trust is not None:
        query = query.filter(User.trust_score <= max_trust)
        
    total = query.count()
    users = query.offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "users": [
            {
                "user_id": u.id,
                "email": u.email,
                "trust_score": u.trust_score,
                "status": u.status,
                "registered_at": u.registered_at.isoformat() + "Z",
                "last_login_at": u.last_login_at.isoformat() + "Z" if u.last_login_at else None,
                "last_ip": u.last_ip,
                "flag_count": 0 # Placeholder for now
            }
            for u in users
        ]
    }

@router.get("/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "user_id": user.id,
        "email": user.email,
        "trust_score": user.trust_score,
        "status": user.status,
        "registered_at": user.registered_at.isoformat() + "Z",
        "behavioral_snapshot": {
            "typing_variance_ms": user.typing_variance_ms,
            "time_to_complete_sec": user.time_to_complete_sec,
            "mouse_move_count": user.mouse_move_count,
            "keypress_count": user.keypress_count
        },
        "ml_anomaly_score": user.ml_anomaly_score,
        "flags": user.triggered_flags.split(",") if user.triggered_flags else []
    }

@router.get("/{user_id}/timeline")
def get_user_timeline(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    events = db.query(Event).filter(Event.user_id == user_id).order_by(Event.timestamp.desc()).all()
    
    return {
        "user_id": user_id,
        "timeline": [
            {
                "event_id": e.id,
                "action": e.action,
                "timestamp": e.timestamp.isoformat() + "Z",
                "ip_address": e.ip_address,
                "country": e.country,
                "user_agent": e.user_agent,
                "trust_score_at_time": e.trust_score_at_time
            }
            for e in events
        ]
    }

@router.patch("/{user_id}/status")
def update_user_status(user_id: str, req: StatusUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if req.status not in ["active", "quarantined", "blocked"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    user.status = req.status
    db.commit()
    
    return {
        "user_id": user.id,
        "status": user.status,
        "message": "User status updated"
    }

