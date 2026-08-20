"""Testes de `src.services.video_service.VideoService.get_video` — controle
de acesso ao vídeo (via clube ou dono direto), usando repositórios falsos
(sem tocar o Supabase real)."""

import os

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")

import pytest
from fastapi import HTTPException

from src.services.video_service import VideoService


class FakeVideoRepo:
    def __init__(self, video: dict):
        self._video = video

    def get_by_id(self, video_id):
        return self._video if video_id == self._video["id"] else None


class FakeMemberRepo:
    def __init__(self, memberships):
        self._memberships = set(memberships)

    def find_membership(self, club_id, user_id):
        return {"club_id": club_id, "user_id": user_id} if (club_id, user_id) in self._memberships else None


def _service(video, memberships=()):
    return VideoService(
        FakeVideoRepo(video),
        match_repo=None,
        job_repo=None,
        member_repo=FakeMemberRepo(memberships),
        athlete_repo=None,
        storage=None,
        celery_client=None,
        settings=None,
    )


def test_get_video_not_found_raises_404():
    video = {"id": "video-1", "owner_type": "athlete", "owner_id": "user-x"}
    service = _service(video)

    with pytest.raises(HTTPException) as exc_info:
        service.get_video("video-does-not-exist", "user-x")

    assert exc_info.value.status_code == 404


def test_get_video_allowed_for_club_member():
    video = {"id": "video-1", "owner_type": "club", "owner_id": "club-1", "video_type": "adversario"}
    service = _service(video, memberships=[("club-1", "user-x")])

    result = service.get_video("video-1", "user-x")

    assert result["video_type"] == "adversario"


def test_get_video_denied_for_non_member():
    video = {"id": "video-1", "owner_type": "club", "owner_id": "club-1", "video_type": "propria_equipe"}
    service = _service(video)

    with pytest.raises(HTTPException) as exc_info:
        service.get_video("video-1", "user-x")

    assert exc_info.value.status_code == 403


def test_get_video_allowed_for_direct_owner():
    video = {"id": "video-1", "owner_type": "athlete", "owner_id": "user-x", "video_type": "propria_equipe"}
    service = _service(video)

    result = service.get_video("video-1", "user-x")

    assert result["id"] == "video-1"


def test_get_video_denied_for_other_athlete():
    video = {"id": "video-1", "owner_type": "athlete", "owner_id": "user-x", "video_type": "propria_equipe"}
    service = _service(video)

    with pytest.raises(HTTPException) as exc_info:
        service.get_video("video-1", "user-y")

    assert exc_info.value.status_code == 403
