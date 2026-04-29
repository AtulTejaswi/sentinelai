from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from database import get_db
from models import User, Alert, Event
from auth import get_current_user

router = APIRouter()

@router.get("/summary")
def get_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_users = db.query(User).count()
    
    today = datetime.utcnow().date()
    # Filter alerts created today
    flagged_today = db.query(Alert).filter(Alert.timestamp >= today).count()
    bot_waves_detected = db.query(Alert).filter(Alert.type == "bot_wave").count()
    
    quarantined = db.query(User).filter(User.status == "quarantined").count()
    blocked = db.query(User).filter(User.status == "blocked").count()
    
    users = db.query(User).all()
    avg_trust_score = sum(u.trust_score for u in users) / len(users) if users else 0
    
    return {
        "total_users": total_users,
        "flagged_today": flagged_today,
        "bot_waves_detected": bot_waves_detected,
        "quarantined": quarantined,
        "blocked": blocked,
        "avg_trust_score": round(avg_trust_score, 1)
    }

@router.get("/velocity")
def velocity(
    window: str = "1h",
    bucket: str = "1min",
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # window can be 1h, 6h, 24h
    now = datetime.utcnow()
    if window == "6h":
        start_time = now - timedelta(hours=6)
    elif window == "24h":
        start_time = now - timedelta(hours=24)
    else:
        start_time = now - timedelta(hours=1)
        
    # Get all registrations in this window
    regs = db.query(User).filter(User.registered_at >= start_time).order_by(User.registered_at.asc()).all()
    
    # Bucket them (simplified logic for now)
    data = []
    # Just return some dummy buckets if no data for chart visibility
    if not regs:
        data = [{"timestamp": (now - timedelta(minutes=1)).isoformat() + "Z", "registrations": 0}]
    else:
         for r in regs:
             data.append({"timestamp": r.registered_at.isoformat() + "Z", "registrations": 1})

    spike_detected = len(regs) > 50 # Example threshold
    
    return {
        "window": window,
        "data": data,
        "spike_detected": spike_detected,
        "spike_at": now.isoformat() + "Z" if spike_detected else None
    }

@router.get("/trust-distribution")
def trust_dist(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).all()
    
    bands = [
        { "label": "Safe (80-100)",       "count": 0, "color": "green" },
        { "label": "Caution (60-79)",     "count": 0, "color": "yellow" },
        { "label": "Suspicious (40-59)", "count": 0, "color": "orange" },
        { "label": "Quarantined (20-39)","count": 0,  "color": "red" },
        { "label": "Blocked (0-19)",      "count": 0,  "color": "darkred" }
    ]
    
    for u in users:
        if u.trust_score >= 80: bands[0]["count"] += 1
        elif u.trust_score >= 60: bands[1]["count"] += 1
        elif u.trust_score >= 40: bands[2]["count"] += 1
        elif u.trust_score >= 20: bands[3]["count"] += 1
        else: bands[4]["count"] += 1
            
    return {
        "bands": bands,
        "total": len(users)
    }

