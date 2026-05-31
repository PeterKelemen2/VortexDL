from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.remote_machine import SSHAuthType


class RemoteMachineBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=128)]
    host: Annotated[str, Field(min_length=1, max_length=255)]
    port: int = Field(default=22, ge=1, le=65535)
    username: Annotated[str, Field(min_length=1, max_length=128)]
    auth_type: SSHAuthType = SSHAuthType.password
    download_folder: Annotated[str, Field(min_length=1, max_length=1024)]
    is_active: bool = True


class RemoteMachineCreate(RemoteMachineBase):
    # Required when auth_type == password.
    password: str | None = Field(default=None, max_length=1024)
    # Required when auth_type == key (server-side path to a private key file).
    ssh_key_path: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def _validate_auth(self) -> "RemoteMachineCreate":
        if self.auth_type == SSHAuthType.password and not self.password:
            raise ValueError("password is required when auth_type is 'password'")
        if self.auth_type == SSHAuthType.key and not self.ssh_key_path:
            raise ValueError("ssh_key_path is required when auth_type is 'key'")
        return self


class RemoteMachineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, min_length=1, max_length=128)
    auth_type: SSHAuthType | None = None
    password: str | None = Field(default=None, max_length=1024)
    ssh_key_path: str | None = Field(default=None, max_length=1024)
    download_folder: str | None = Field(default=None, min_length=1, max_length=1024)
    is_active: bool | None = None


class RemoteMachineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    host: str
    port: int
    username: str
    auth_type: SSHAuthType
    ssh_key_path: str | None = None
    download_folder: str
    host_key_fingerprint: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RemoteMachineListResponse(BaseModel):
    items: list[RemoteMachineRead]
    total: int
    page: int
    page_size: int


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    host_key_fingerprint: str | None = None


class RemoteMachineAssignmentRead(BaseModel):
    """A user's view of a machine they are allowed to use."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    host: str
    download_folder: str
    is_active: bool


class AssignUserRequest(BaseModel):
    user_id: int


class AssignedUserRead(BaseModel):
    """Minimal user view for the machine assignment management UI."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None


class RemoteBrowseEntry(BaseModel):
    name: str
    type: Literal["dir", "file"]
    size: int | None = None
    modified: datetime | None = None


class RemoteBrowseResult(BaseModel):
    path: str
    entries: list[RemoteBrowseEntry]
