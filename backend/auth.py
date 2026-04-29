import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional, List
import random
import string
import uuid

from database import get_db
from models import User, Event, OtpSession, Alert

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours per API.md

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# Pydantic models
class BehavioralPayload(BaseModel):
    typing_variance_ms: Optional[float] = None
    time_to_complete_sec: Optional[float] = None
    mouse_move_count: Optional[int] = None
    keypress_count: Optional[int] = None

class RegisterRequest(BaseModel):
    email: str
    password: str
    behavioral: Optional[BehavioralPayload] = None

class LoginRequest(BaseModel):
    email: str
    password: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class OtpSendRequest(BaseModel):
    email: str
    otp_session_id: str

class OtpVerifyRequest(BaseModel):
    otp_session_id: str
    otp_code: str

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == req.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Calculate a mock trust score based on "speed bot" rule
    trust_score = 100
    status_label = "active"
    if req.behavioral and req.behavioral.time_to_complete_sec and req.behavioral.time_to_complete_sec < 4:
        trust_score = 18
        status_label = "quarantined"

    hashed_password = get_password_hash(req.password)
    user = User(
        email=req.email,
        password_hash=hashed_password,
        trust_score=trust_score,
        status=status_label
    )
    
    if req.behavioral:
        user.typing_variance_ms = req.behavioral.typing_variance_ms
        user.time_to_complete_sec = req.behavioral.time_to_complete_sec
        user.mouse_move_count = req.behavioral.mouse_move_count
        user.keypress_count = req.behavioral.keypress_count

    db.add(user)
    db.commit()
    db.refresh(user)

    event = Event(
        user_id=user.id,
        action="register",
        trust_score_at_time=user.trust_score
    )
    db.add(event)
    db.commit()

    if status_label == "quarantined":
         return {
            "user_id": user.id,
            "trust_score": user.trust_score,
            "status": user.status,
            "message": "Account flagged for review"
        }

    return {
        "user_id": user.id,
        "trust_score": user.trust_score,
        "status": user.status,
        "message": "Registration successful"
    }

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        if user:
            event = Event(user_id=user.id, action="login_failed", ip_address=req.ip_address, user_agent=req.user_agent)
            db.add(event)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.status == "blocked" or (user.status == "quarantined" and user.trust_score < 20):
        raise HTTPException(status_code=403, detail={
            "error": "Account suspended pending review",
            "trust_score": user.trust_score
        })

    user.last_ip = req.ip_address
    user.last_login_at = datetime.utcnow()
    db.commit()

    event = Event(user_id=user.id, action="login", ip_address=req.ip_address, user_agent=req.user_agent, trust_score_at_time=user.trust_score)
    db.add(event)
    db.commit()

    # check trust score thresholds (API.md 412-416)
    if user.trust_score < 70:
        # Create OTP session
        otp_session_id = str(uuid.uuid4())
        otp_code = ''.join(random.choices(string.digits, k=6))
        otp_session = OtpSession(
            id=otp_session_id,
            user_id=user.id,
            otp_code=otp_code,
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.add(otp_session)
        db.commit()

        return {
            "token": None,
            "trust_score": user.trust_score,
            "otp_required": True,
            "otp_session_id": otp_session_id,
            "user_id": user.id
        }

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.id}, expires_delta=access_token_expires)
    
    return {
        "token": access_token,
        "trust_score": user.trust_score,
        "otp_required": False,
        "user_id": user.id
    }

def send_email_stub(to_email: str, subject: str, body: str):
    try:
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        if gmail_user and gmail_password:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = gmail_user
            msg["To"] = to_email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_password)
                server.sendmail(gmail_user, [to_email], msg.as_string())
        else:
            print(f"Mock SMTP to {to_email}: {subject} | {body}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@router.post("/otp/send")
def send_otp(req: OtpSendRequest, db: Session = Depends(get_db)):
    session = db.query(OtpSession).filter(OtpSession.id == req.otp_session_id).first()
    if not session or session.used or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
         raise HTTPException(status_code=404, detail="User not found")

    send_email_stub(user.email, "SentinelAI OTP", f"Your OTP is {session.otp_code}")

    event = Event(user_id=user.id, action="otp_sent", trust_score_at_time=user.trust_score)
    db.add(event)
    db.commit()

    return {
        "message": "OTP sent successfully",
        "expires_in_seconds": 300
    }

@router.post("/otp/verify")
def verify_otp(req: OtpVerifyRequest, db: Session = Depends(get_db)):
    session = db.query(OtpSession).filter(
        OtpSession.id == req.otp_session_id, 
        OtpSession.otp_code == req.otp_code,
        OtpSession.used == False,
        OtpSession.expires_at > datetime.utcnow()
    ).first()

    if not session:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    session.used = True
    db.commit()

    user = db.query(User).filter(User.id == session.user_id).first()
    
    event = Event(user_id=user.id, action="otp_verified", trust_score_at_time=user.trust_score)
    db.add(event)
    db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.id}, expires_delta=access_token_expires)
    
    return {
        "token": access_token,
        "user_id": user.id,
        "message": "Login successful"
    }

