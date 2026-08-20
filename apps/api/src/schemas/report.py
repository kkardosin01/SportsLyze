from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReportRequest(BaseModel):
    format: Literal["pdf", "slides", "audio"] = "pdf"


class ReportOut(BaseModel):
    id: str
    scope: Literal["match", "player"]
    match_id: str | None
    athlete_id: str | None
    format: Literal["pdf", "slides", "audio"]
    version: int
    generated_at: datetime
    download_url: str
