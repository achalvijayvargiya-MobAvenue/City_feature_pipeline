from typing import Protocol, Any
from pydantic import BaseModel

class SourceRequest(BaseModel):
    dataset: str
    version: str
    params: dict = {}

class SourceResponse(BaseModel):
    data: Any
    metadata: dict = {}

class RawArtifact(BaseModel):
    path: str
    hash: str

class SourceAdapter(Protocol):
    source_name: str
    
    def fetch(self, request: SourceRequest) -> SourceResponse:
        ...

    def validate(self, response: SourceResponse) -> None:
        ...

    def save_raw(self, response: SourceResponse) -> RawArtifact:
        ...
