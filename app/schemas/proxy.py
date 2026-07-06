from pydantic import BaseModel
from typing import Optional


class ProxyImportRequest(BaseModel):
    proxies: list[str]


class ProxyReplaceRequest(BaseModel):
    proxies: list[str]


class ProxyMarkDeadRequest(BaseModel):
    proxy_id: int
    error: str = "unknown"
