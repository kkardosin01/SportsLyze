from datetime import datetime

from pydantic import BaseModel, EmailStr


class ClubCreate(BaseModel):
    name: str
    official_email_domain: str
    admin_full_name: str
    admin_email: EmailStr


class ClubOut(BaseModel):
    id: str
    name: str
    official_email_domain: str
    verified_at: datetime | None
    created_at: datetime


class ClubMemberInvite(BaseModel):
    email: EmailStr
    role: str  # coordenador | preparador | analista


class ClubMemberOut(BaseModel):
    id: str
    club_id: str
    user_id: str
    role: str
    created_at: datetime
