from functools import lru_cache
from time import time

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)

_JWKS_CACHE_TTL_SECONDS = 3600
_jwks_cache: dict[str, object] = {"keys": None, "fetched_at": 0.0}


class CurrentUser(BaseModel):
    id: str
    email: str | None = None


def _get_jwks(supabase_url: str) -> list[dict]:
    """Busca (e cacheia por 1h) o JWKS do Supabase Auth local/hospedado.

    Desde o GoTrue passar a assinar tokens com chaves assimétricas (ES256)
    por padrão, não há mais um `jwt_secret` HS256 fixo — o token precisa ser
    validado contra a chave pública correspondente ao `kid` do header.
    """
    now = time()
    if _jwks_cache["keys"] is not None and now - _jwks_cache["fetched_at"] < _JWKS_CACHE_TTL_SECONDS:
        return _jwks_cache["keys"]  # type: ignore[return-value]

    response = requests.get(f"{supabase_url}/auth/v1/.well-known/jwks.json", timeout=5)
    response.raise_for_status()
    keys = response.json().get("keys", [])
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Valida o JWT emitido pelo Supabase Auth e extrai o usuário autenticado.

    A API usa a service role key para acessar o Postgres (bypassando RLS),
    mas ainda assim decodifica o JWT do usuário para saber quem está fazendo
    a requisição e aplicar as regras de autorização nos services.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente.",
        )

    settings = get_settings()
    token = credentials.credentials

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        ) from exc

    algorithm = unverified_header.get("alg", "HS256")

    try:
        if algorithm == "HS256":
            # Compat com projetos Supabase que ainda usam o jwt_secret legado.
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            jwks = _get_jwks(settings.supabase_url)
            signing_key = next(
                (key for key in jwks if key.get("kid") == unverified_header.get("kid")), None
            )
            if signing_key is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Chave de assinatura do token não encontrada.",
                )
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                audience="authenticated",
            )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não contém identificação de usuário.",
        )

    return CurrentUser(id=user_id, email=payload.get("email"))
