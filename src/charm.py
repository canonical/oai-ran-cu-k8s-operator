#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the OAI RAN Central Unit (CU) for K8s."""

import json
import logging
from ipaddress import IPv4Address
from subprocess import check_output
from typing import List, Optional, Tuple

from charms.kubernetes_charm_libraries.v0.multus import (
    KubernetesMultusCharmLib,
    NetworkAnnotation,
    NetworkAttachmentDefinition,
)
from charms.loki_k8s.v1.loki_push_api import LogForwarder
from charms.oai_ran_cu_k8s.v0.fiveg_f1 import F1Provides
from charms.oai_ran_cu_k8s.v0.fiveg_f1 import PLMNConfig as F1_PLMNConfig
from charms.sdcore_amf_k8s.v0.fiveg_n2 import N2Requires
from charms.sdcore_nms_k8s.v0.fiveg_core_gnb import FivegCoreGnbRequires, PLMNConfig
from jinja2 import Environment, FileSystemLoader
from lightkube.models.meta_v1 import ObjectMeta
from ops import ActiveStatus, BlockedStatus, CollectStatusEvent, WaitingStatus, main
from ops.charm import CharmBase
from ops.pebble import ExecError, Layer

from charm_config import CharmConfig, CharmConfigInvalidError, CNIType
from k8s_privileged import K8sPrivileged

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/tmp/conf"
CONFIG_FILE_NAME = "cu.conf"
F1_RELATION_NAME = "fiveg_f1"
N2_RELATION_NAME = "fiveg_n2"
CORE_GNB_RELATION_NAME = "fiveg_core_gnb"
DU_F1_DEFAULT_PORT = 2152
WORKLOAD_VERSION_FILE_NAME = "/etc/workload-version"
LOGGING_RELATION_NAME = "logging"


class OAIRANCUOperator(CharmBase):
    """Main class to describe Juju event handling for the OAI RAN CU operator for K8s."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)
        if not self.unit.is_leader():
            return
        self._container_name = self._service_name = "cu"
        self._container = self.unit.get_container(self._container_name)
        self._n2_requirer = N2Requires(self, N2_RELATION_NAME)
        self._core_gnb_requirer = FivegCoreGnbRequires(self, CORE_GNB_RELATION_NAME)
        self._f1_provider = F1Provides(self, F1_RELATION_NAME)
        self._logging = LogForwarder(charm=self, relation_name=LOGGING_RELATION_NAME)
        self._k8s_privileged = K8sPrivileged(
            namespace=self.model.name, statefulset_name=self.app.name
        )
        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(charm=self)
        except CharmConfigInvalidError:
            return
        self._kubernetes_multus = KubernetesMultusCharmLib(
            cap_net_admin=True,
            namespace=self.model.name,
            statefulset_name=self.model.app.name,
            pod_name="-".join(self.model.unit.name.rsplit("/", 1)),
            container_name=self._container_name,
            network_annotations=self._generate_network_annotations(),
            network_attachment_definitions=self._network_attachment_definitions_from_config(),
            privileged=True,
        )

        self.framework.observe(self.on.update_status, self._configure)
        self.framework.observe(self.on.config_changed, self._configure)
        self.framework.observe(self.on.cu_pebble_ready, self._configure)
        self.framework.observe(self.on.fiveg_n2_relation_joined, self._configure)
        self.framework.observe(self._n2_requirer.on.n2_information_available, self._configure)
        self.framework.observe(self.on[F1_RELATION_NAME].relation_changed, self._configure)
        self.framework.observe(self.on[CORE_GNB_RELATION_NAME].relation_changed, self._configure)
        self.framework.observe(self.on.remove, self._on_remove)

    def _on_collect_unit_status(self, event: CollectStatusEvent):  # noqa C901
        """Check the unit status and set to Unit when CollectStatusEvent is fired.

        Set the workload version if present in workload
        Args:
            event: CollectStatusEvent
        """
        if not self.unit.is_leader():
            # NOTE: In cases where leader status is lost before the charm is
            # finished processing all teardown events, this prevents teardown
            # event code from running. Luckily, for this charm, none of the
            # teardown code is necessary to perform if we're removing the
            # charm.
            event.add_status(BlockedStatus("Scaling is not implemented for this charm"))
            logger.info("Scaling is not implemented for this charm")
            return
        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(charm=self)
        except CharmConfigInvalidError as exc:
            event.add_status(BlockedStatus(exc.msg))
            return
        if not self._kubernetes_multus.multus_is_available():
            event.add_status(BlockedStatus("Multus is not installed or enabled"))
            logger.info("Multus is not installed or enabled")
            return
        if not self._kubernetes_multus.is_ready():
            event.add_status(WaitingStatus("Waiting for Multus to be ready"))
            logger.info("Waiting for Multus to be ready")
            return
        if not self._container.can_connect():
            event.add_status(WaitingStatus("Waiting for container to be ready"))
            logger.info("Waiting for container to be ready")
            return
        if not _get_pod_ip():
            event.add_status(WaitingStatus("Waiting for Pod IP address to be available"))
            logger.info("Waiting for Pod IP address to be available")
            return
        if not self._k8s_privileged.is_patched(container_name=self._container_name):
            event.add_status(WaitingStatus("Waiting for statefulset to be patched"))
            logger.info("Waiting for statefulset to be patched")
            return
        self.unit.set_workload_version(self._get_workload_version())
        if not self._container.exists(path=BASE_CONFIG_PATH):
            event.add_status(WaitingStatus("Waiting for storage to be attached"))
            logger.info("Waiting for storage to be attached")
            return
        if not self._relation_created(N2_RELATION_NAME):
            event.add_status(BlockedStatus("Waiting for N2 relation to be created"))
            logger.info("Waiting for N2 relation to be created")
            return
        if not self._n2_requirer.amf_hostname:
            event.add_status(WaitingStatus("Waiting for N2 information"))
            logger.info("Waiting for N2 information")
            return
        if not self._relation_created(CORE_GNB_RELATION_NAME):
            event.add_status(BlockedStatus("Waiting for fiveg_core_gnb relation to be created"))
            logger.info("Waiting for fiveg_core_gnb relation to be created")
            return
        if not self._n3_route_exists():
            event.add_status(WaitingStatus("Waiting for the N3 route to be created"))
            logger.info("Waiting for the N3 route to be created")
            return
        if not self._core_gnb_requirer.tac or not self._core_gnb_requirer.plmns:
            event.add_status(WaitingStatus("Waiting for TAC and PLMNs configuration"))
            return
        if not self._is_gnb_name_published():
            event.add_status(
                BlockedStatus("Invalid configuration: gNB name is missing from the relation")
            )
            return
        event.add_status(ActiveStatus())

    def _configure(self, _) -> None:  # noqa C901
        try:
            self._charm_config: CharmConfig = CharmConfig.from_charm(charm=self)
        except CharmConfigInvalidError:
            return
        if not self._kubernetes_multus.multus_is_available():
            return
        self._kubernetes_multus.configure()
        if not self._kubernetes_multus.is_ready():
            return
        if not self._container.can_connect():
            return
        if not self._container.exists(path=BASE_CONFIG_PATH):
            return
        if not _get_pod_ip():
            return
        if not self._relation_created(CORE_GNB_RELATION_NAME):
            return
        self._update_fiveg_core_gnb_relation_data()
        if not self._k8s_privileged.is_patched(container_name=self._container_name):
            self._k8s_privileged.patch_statefulset(container_name=self._container_name)
        if not self._n3_route_exists():
            self._create_n3_route()
        if not self._core_gnb_requirer.tac or not self._core_gnb_requirer.plmns:
            return
        self._update_fiveg_f1_relation_data()

        if not self._relation_created(N2_RELATION_NAME):
            return
        if not self._n2_requirer.amf_hostname:
            return
        if not self._is_gnb_name_published():
            return
        cu_config = self._generate_cu_config()
        if config_update_required := not self._is_cu_config_up_to_date(cu_config):
            self._write_config_file(content=cu_config)
        service_restart_required = config_update_required
        self._configure_pebble(restart=service_restart_required)

    def _on_remove(self, _) -> None:
        """Handle the remove event."""
        if not self.unit.is_leader():
            return
        self._kubernetes_multus.remove()

    def _n3_route_exists(self) -> bool:
        """Return whether the specified route exist."""
        try:
            stdout, stderr = self._exec_command_in_workload_container(command="ip route show")
        except ExecError as e:
            logger.error("Failed retrieving routes: %s", e.stderr)
            return False
        for line in stdout.splitlines():
            if f"{self._charm_config.upf_subnet} via {self._charm_config.n3_gateway_ip}" in line:
                return True
        return False

    def _create_n3_route(self) -> None:
        """Create ip route for the N3 connectivity."""
        try:
            self._exec_command_in_workload_container(
                command=f"ip route replace {self._charm_config.upf_subnet} via {self._charm_config.n3_gateway_ip}"  # noqa: E501
            )
        except ExecError as e:
            logger.error("Failed to create N3 route: %s", e.stderr)
            return
        logger.info("N3 route created")

    def _relation_created(self, relation_name: str) -> bool:
        """Return whether a given Juju relation was created.

        Args:
            relation_name (str): Relation name

        Returns:
            bool: Whether the relation was created.
        """
        return bool(self.model.relations.get(relation_name))

    def _generate_cu_config(self) -> str:
        tac = self._core_gnb_requirer.tac
        plmns = self._core_gnb_requirer.plmns
        if not tac or not plmns:
            logger.warning("TAC and PLMNs config are not available")
            return ""
        if self._f1_provider.requirer_f1_port:
            du_f1_port = self._f1_provider.requirer_f1_port
        else:
            logger.info(
                "DU F1 port information not available. Using default value %s", DU_F1_DEFAULT_PORT
            )
            du_f1_port = DU_F1_DEFAULT_PORT
        if not (
            self._charm_config.f1_ip_address
            and self._charm_config.n3_ip_address
            and (n2_ip_address := _get_pod_ip())
        ):
            logger.warning("Interfaces ip addresses are not available")
            return ""
        if not self._n2_requirer.amf_ip_address:
            logger.warning("AMF IP address not available")
            return ""
        return _render_config_file(
            gnb_name=self._gnb_name,
            cu_f1_interface_name=self._charm_config.f1_interface_name,
            cu_f1_ip_address=str(self._charm_config.f1_ip_address).split("/")[0],
            cu_f1_port=self._charm_config.f1_port,
            du_f1_port=du_f1_port,
            cu_n2_ip_address=n2_ip_address,
            cu_n3_interface_name=self._charm_config.n3_interface_name,
            cu_n3_ip_address=str(self._charm_config.n3_ip_address).split("/")[0],
            amf_external_address=self._n2_requirer.amf_ip_address,
            tac=tac,
            plmns=plmns,
        )

    def _generate_network_annotations(self) -> List[NetworkAnnotation]:
        """Generate a list of NetworkAnnotations to be used by CU's StatefulSet.

        Returns:
            List[NetworkAnnotation]: List of NetworkAnnotations
        """
        return [
            NetworkAnnotation(
                name=f"{self.app.name}-{self._charm_config.n3_interface_name}-net",
                interface=self._charm_config.n3_interface_name,
            ),
            NetworkAnnotation(
                name=f"{self.app.name}-{self._charm_config.f1_interface_name}-net",
                interface=self._charm_config.f1_interface_name,
            ),
        ]

    @staticmethod
    def _get_base_config(address: str) -> dict:
        return {
            "cniVersion": "0.3.1",
            "ipam": {
                "type": "static",
                "addresses": [
                    {
                        "address": address,
                    }
                ],
                "capabilities": {"mac": True},
            },
        }

    def _get_n3_nad_config(self) -> dict:
        n3_nad_config = self._get_base_config(self._charm_config.n3_ip_address)
        return self._add_cni_type_to_nad_config(
            n3_nad_config,
            self._charm_config.n3_interface_name,
            f"{self._charm_config.n3_interface_name}-br",
        )

    def _get_f1_nad_config(self) -> dict:
        f1_nad_config = self._get_base_config(self._charm_config.f1_ip_address)
        return self._add_cni_type_to_nad_config(
            f1_nad_config,
            self._charm_config.f1_interface_name,
            f"{self._charm_config.f1_interface_name}-br",
        )

    def _add_cni_type_to_nad_config(self, nad_config: dict, interface: str, bridge: str) -> dict:
        if self._charm_config.cni_type == CNIType.macvlan:
            nad_config.update(
                {
                    "type": "macvlan",
                    "master": interface,
                }
            )
        elif self._charm_config.cni_type == CNIType.bridge:
            nad_config.update({"type": "bridge", "bridge": bridge})
        elif self._charm_config.cni_type == CNIType.host_device:
            nad_config.update({"type": "host-device", "device": interface})
        return nad_config

    def _network_attachment_definitions_from_config(self) -> list[NetworkAttachmentDefinition]:
        """Return list of Multus NetworkAttachmentDefinitions to be created based on config."""
        return [
            NetworkAttachmentDefinition(
                metadata=ObjectMeta(
                    name=f"{self.app.name}-{self._charm_config.n3_interface_name}-net"
                ),
                spec={"config": json.dumps(self._get_n3_nad_config())},
            ),
            NetworkAttachmentDefinition(
                metadata=ObjectMeta(
                    name=f"{self.app.name}-{self._charm_config.f1_interface_name}-net"
                ),
                spec={"config": json.dumps(self._get_f1_nad_config())},
            ),
        ]

    def _is_cu_config_up_to_date(self, content: str) -> bool:
        """Check whether the CU config file content matches the actual charm configuration.

        Args:
            content (str): desired config file content

        Returns:
            True if config is up-to-date else False
        """
        return self._config_file_is_written() and self._config_file_content_matches(
            content=content
        )

    def _config_file_is_written(self) -> bool:
        return bool(self._container.exists(f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"))

    def _config_file_content_matches(self, content: str) -> bool:
        if not self._container.exists(path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"):
            return False
        existing_content = self._container.pull(path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}")
        return existing_content.read() == content

    def _write_config_file(self, content: str) -> None:
        self._container.push(source=content, path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}")
        logger.info("Config file written")

    def _configure_pebble(self, restart=False) -> None:
        """Configure the Pebble layer.

        Args:
            restart (bool): Whether to restart the CU container.
        """
        plan = self._container.get_plan()
        if plan.services != self._cu_pebble_layer.services:
            self._container.add_layer(self._container_name, self._cu_pebble_layer, combine=True)
            self._container.replan()
            logger.info("New layer added: %s", self._cu_pebble_layer)
        if restart:
            self._container.restart(self._service_name)
            logger.info("Restarted container %s", self._service_name)
            return

    def _update_fiveg_core_gnb_relation_data(self) -> None:
        """Publish gNB name `fiveg_core_gnb` relation data bag."""
        if not self.unit.is_leader():
            return
        if not self._relation_created(CORE_GNB_RELATION_NAME):
            logger.info("No %s relations found.", CORE_GNB_RELATION_NAME)
            return
        try:
            self._core_gnb_requirer.publish_gnb_information(gnb_name=self._gnb_name)
        except ValueError:
            return

    def _is_gnb_name_published(self) -> bool:
        relation = self.model.get_relation(CORE_GNB_RELATION_NAME)
        if not relation:
            return False
        return relation.data[self.app].get("gnb-name") is not None

    def _update_fiveg_f1_relation_data(self) -> None:
        """Publish F1 interface information in the `fiveg_f1` relation data bag."""
        if not self.unit.is_leader():
            return
        if not self._relation_created(F1_RELATION_NAME):
            logger.info("No %s relations found.", F1_RELATION_NAME)
            return
        if not (f1_ip := self._charm_config.f1_ip_address):
            logger.error("F1 IP address is not available")
            return
        core_gnb_tac = self._core_gnb_requirer.tac
        core_gnb_plmns = self._core_gnb_requirer.plmns
        if not core_gnb_tac or not core_gnb_plmns:
            return
        f1_plmns = [F1_PLMNConfig(**vars(plmn)) for plmn in core_gnb_plmns]
        self._f1_provider.set_f1_information(
            ip_address=f1_ip.split("/")[0],
            port=self._charm_config.f1_port,
            tac=core_gnb_tac,
            plmns=f1_plmns,
        )

    def _exec_command_in_workload_container(
        self, command: str, timeout: Optional[int] = 30, environment: Optional[dict] = None
    ) -> Tuple[str, str | None]:
        """Execute command in the workload container.

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            environment: Environment Variables
        """
        process = self._container.exec(
            command=command.split(),
            timeout=timeout,
            environment=environment,
        )
        return process.wait_output()

    @property
    def _gnb_name(self) -> str:
        """The gNB's name contains the model name and the app name.

        Returns:
            str: the gNB's name.
        """
        return f"{self.model.name}-{self.app.name}-cu"

    @property
    def _cu_pebble_layer(self) -> Layer:
        """Return pebble layer for the cu container.

        Returns:
            Layer: Pebble Layer
        """
        return Layer(
            {
                "services": {
                    self._service_name: {
                        "override": "replace",
                        "startup": "enabled",
                        "command": f"/opt/oai-gnb/bin/nr-softmodem -O {BASE_CONFIG_PATH}/{CONFIG_FILE_NAME} --sa",  # noqa: E501
                        "environment": self._cu_environment_variables,
                    },
                },
            }
        )

    @property
    def _cu_environment_variables(self) -> dict:
        return {
            "OAI_GDBSTACKS": "1",
            "TZ": "UTC",
        }

    def _get_workload_version(self) -> str:
        """Return the workload version.

        Checks for the presence of /etc/workload-version file
        and if present, returns the contents of that file. If
        the file is not present, an empty string is returned.

        Returns:
            string: A human-readable string representing the version of the workload
        """
        if self._container.exists(path=WORKLOAD_VERSION_FILE_NAME):
            version_file_content = self._container.pull(path=WORKLOAD_VERSION_FILE_NAME).read()
            return version_file_content
        return ""


def _render_config_file(
    *,
    gnb_name: str,
    cu_f1_interface_name: str,
    cu_f1_ip_address: str,
    cu_f1_port: int,
    du_f1_port: int,
    cu_n2_ip_address: str,
    cu_n3_interface_name: str,
    cu_n3_ip_address: str,
    amf_external_address: str,
    tac: int,
    plmns: list[PLMNConfig],
) -> str:
    """Render CU config file based on parameters.

    Args:
        gnb_name: The name of the gNodeB
        cu_f1_interface_name: Name of the network interface used for F1 traffic
        cu_f1_ip_address: IPv4 address of the network interface used for F1 traffic
        cu_f1_port: Number of the port used by the CU for F1 traffic
        du_f1_port: Number of the port used by the DU for F1 traffic
        cu_n2_ip_address: IPv4 address of the network interface used for N2 traffic
        cu_n3_interface_name: Name of the network interface used for N3 traffic
        cu_n3_ip_address: IPv4 address of the network interface used for N3 traffic
        amf_external_address: AMF hostname
        tac: Tracking Area Code
        plmns: list of PLMN

    Returns:
        str: Rendered CU configuration file
    """
    jinja2_env = Environment(loader=FileSystemLoader("src/templates"))
    template = jinja2_env.get_template("cu.conf.j2")
    return template.render(
        gnb_name=gnb_name,
        cu_f1_interface_name=cu_f1_interface_name,
        cu_f1_ip_address=cu_f1_ip_address,
        cu_f1_port=cu_f1_port,
        du_f1_port=du_f1_port,
        cu_n2_ip_address=cu_n2_ip_address,
        cu_n3_interface_name=cu_n3_interface_name,
        cu_n3_ip_address=cu_n3_ip_address,
        amf_external_address=amf_external_address,
        tac=tac,
        plmn_list=plmns,
    )


def _get_pod_ip() -> Optional[str]:
    """Return the pod IP using juju client.

    Returns:
        str: The pod IP.
    """
    ip_address = check_output(["unit-get", "private-address"])
    return str(IPv4Address(ip_address.decode().strip())) if ip_address else None


if __name__ == "__main__":  # pragma: nocover
    main(OAIRANCUOperator)
