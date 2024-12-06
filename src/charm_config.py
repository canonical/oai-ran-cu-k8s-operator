#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Config of the Charm."""

import dataclasses
import logging
from enum import Enum
from ipaddress import IPv4Address, IPv4Network, ip_network

import ops
from pydantic import (  # pylint: disable=no-name-in-module,import-error
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    ValidationError,
    field_validator,
)
from pydantic.networks import IPvAnyNetwork
from pydantic_core.core_schema import ValidationInfo

logger = logging.getLogger(__name__)


class CharmConfigInvalidError(Exception):
    """Exception raised when a charm configuration is found to be invalid."""

    def __init__(self, msg: str):
        """Initialize a new instance of the CharmConfigInvalidError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class CNIType(str, Enum):
    """Class to define available CNI types for CU operator."""

    bridge = "bridge"
    macvlan = "macvlan"


def to_kebab(name: str) -> str:
    """Convert a snake_case string to kebab-case."""
    return name.replace("_", "-")


class CUConfig(BaseModel):  # pylint: disable=too-few-public-methods
    """Represent the OAI RAN CU operator builtin configuration values."""

    model_config = ConfigDict(alias_generator=to_kebab, use_enum_values=True)
    cni_type: CNIType = CNIType.bridge
    f1_interface_name: StrictStr = Field(default="f1", min_length=1)
    f1_ip_address: str = Field(default="192.168.254.7/24")
    f1_port: int = Field(ge=1, le=65535)
    n3_interface_name: StrictStr = Field(default="n3", min_length=1)
    n3_ip_address: str = Field(default="192.168.251.6/24")
    n3_gateway_ip: IPv4Address = Field(default=IPv4Address("192.168.251.1"))
    upf_subnet: IPvAnyNetwork = Field(default=IPv4Network("192.168.252.0/24"))

    @field_validator("f1_ip_address", "n3_ip_address", mode="before")
    @classmethod
    def validate_ip_network_address(cls, value: str, info: ValidationInfo) -> str:
        """Validate that IP network address is valid."""
        ip_network(value, strict=False)
        return value


@dataclasses.dataclass
class CharmConfig:
    """Represents the state of the OAI RAN CU operator charm.

    Attributes:
        cni_type: Multus CNI plugin to use for the interfaces.
        f1_interface_name: Name of the network interface used for F1 traffic
        f1_ip_address: IP address used by f1 interface
        f1_port: Number of the port used for F1 traffic
        n3_interface_name: Name of the network interface used for N3 traffic
        n3_ip_address: IP address used by n3 interface
        upf_subnet: Subnet for UPF n3 interface
        n3_gateway_ip: Gateway IP address to the UPF Network.
    """

    cni_type: CNIType
    f1_interface_name: StrictStr
    f1_ip_address: str
    f1_port: int
    n3_interface_name: StrictStr
    n3_ip_address: str
    upf_subnet: IPvAnyNetwork
    n3_gateway_ip: IPv4Address

    def __init__(self, *, cu_config: CUConfig):
        """Initialize a new instance of the CharmConfig class.

        Args:
            cu_config: OAI RAN CU operator configuration.
        """
        self.cni_type = cu_config.cni_type
        self.f1_interface_name = cu_config.f1_interface_name
        self.f1_ip_address = cu_config.f1_ip_address
        self.f1_port = cu_config.f1_port
        self.n3_interface_name = cu_config.n3_interface_name
        self.n3_ip_address = cu_config.n3_ip_address
        self.upf_subnet = cu_config.upf_subnet
        self.n3_gateway_ip = cu_config.n3_gateway_ip

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
    ) -> "CharmConfig":
        """Initialize a new instance of the CharmState class from the associated charm."""
        try:
            # ignoring because pyright fails with:
            # "float" is incompatible with "int"
            return cls(cu_config=CUConfig(**dict(charm.config.items())))  # type: ignore[reportArgumentType]
        except ValidationError as exc:
            error_fields: list = []
            for error in exc.errors():
                if param := error["loc"]:
                    error_fields.extend(param)
                else:
                    value_error_msg: ValueError = error["ctx"]["error"]  # type: ignore[reportTypedDictNotRequiredAccess]
                    error_fields.extend(str(value_error_msg).split())
            error_fields.sort()
            error_field_str = ", ".join(f"'{f}'" for f in error_fields)
            raise CharmConfigInvalidError(
                f"The following configurations are not valid: [{error_field_str}]"
            ) from exc
