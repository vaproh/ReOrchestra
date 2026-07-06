from pydantic import BaseModel
from typing import Optional


class ProxyImportRequest(BaseModel):
    proxies: list[str]
