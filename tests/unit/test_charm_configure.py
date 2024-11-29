#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import tempfile

from charms.oai_ran_cu_k8s.v0.fiveg_f1 import PLMNConfig
from ops import testing
from ops.pebble import Layer

from tests.unit.fixtures import CUCharmFixtures

HARDCODED_PLMNS = [PLMNConfig(mcc="001", mnc="01", sst=1, sd=12)]
HARDCODED_TAC = 1


class TestCharmConfigure(CUCharmFixtures):
    def test_given_statefulset_is_not_patched_when_config_changed_then_statefulset_is_patched(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = False
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_k8s_privileged.patch_statefulset.assert_called_with(container_name="cu")

    def test_given_statefulset_is_patched_when_config_changed_then_statefulset_is_not_patched(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_k8s_privileged.patch_statefulset.assert_not_called()

    def test_given_workload_is_ready_to_be_configured_when_config_changed_then_cu_config_file_is_generated_and_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                model=testing.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            with open("tests/unit/resources/expected_config.conf") as expected_config_file:
                expected_config = expected_config_file.read()

            with open(f"{tmpdir}/cu.conf") as cu_conf:
                assert cu_conf.read().strip() == expected_config.strip()

    def test_given_cu_config_file_is_up_to_date_when_config_changed_then_cu_config_file_is_not_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                model=testing.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            with open("tests/unit/resources/expected_config.conf") as expected_config_file:
                expected_config = expected_config_file.read()
            with open(f"{tmpdir}/cu.conf", "w") as cu_conf:
                cu_conf.write(expected_config.strip())
            config_modification_time = os.stat(tmpdir + "/cu.conf").st_mtime

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            with open(f"{tmpdir}/cu.conf") as cu_conf:
                assert cu_conf.read().strip() == expected_config.strip()
            assert os.stat(tmpdir + "/cu.conf").st_mtime == config_modification_time

    def test_given_charm_configuration_is_done_when_config_changed_then_pebble_layer_is_created(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                model=testing.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            state_out = self.ctx.run(self.ctx.on.config_changed(), state_in)

            container = state_out.get_container("cu")
            assert container.layers["cu"] == Layer(
                {
                    "services": {
                        "cu": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/opt/oai-gnb/bin/nr-softmodem -O /tmp/conf/cu.conf --sa",
                            "environment": {"OAI_GDBSTACKS": "1", "TZ": "UTC"},
                        }
                    }
                }
            )

    def test_given_charm_is_configured_and_running_when_fiveg_gnb_identity_relation_is_added_then_default_tac_is_published(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            fiveg_gnb_relation = testing.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                model=testing.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation, fiveg_gnb_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_gnb_identity.assert_called_once_with(
                relation_id=fiveg_gnb_relation.id,
                gnb_name="whatever-oai-ran-cu-k8s-cu",
                tac=1,
            )

    def test_given_charm_is_configured_and_running_when_f1_relation_is_added_then_f1_interface_ip_and_port_is_published(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            f1_relation = testing.Relation(
                endpoint="fiveg_f1",
                interface="fiveg_f1",
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                model=testing.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation, f1_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_f1_set_information.assert_called_once_with(
                ip_address="192.168.254.7",
                port=2152,
                tac=HARDCODED_TAC,
                plmns=HARDCODED_PLMNS,
            )

    def test_given_charm_is_active_when_config_changed_then_updated_f1_interface_ip_and_port_is_published(  # noqa: E501
        self,
    ):
        test_f1_ip_address = "10.3.5.1/24"
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            f1_relation = testing.Relation(
                endpoint="fiveg_f1",
                interface="fiveg_f1",
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                model=testing.Model(name="whatever"),
                config={"f1-ip-address": test_f1_ip_address, "f1-port": 3522},
                leader=True,
                containers=[container],
                relations=[n2_relation, f1_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_f1_set_information.assert_called_with(
                ip_address=test_f1_ip_address.split("/")[0],
                port=3522,
                tac=HARDCODED_TAC,
                plmns=HARDCODED_PLMNS,
            )

    def test_given_n3_route_not_created_when_config_changed_then_n3_route_is_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            f1_relation = testing.Relation(
                endpoint="fiveg_f1",
                interface="fiveg_f1",
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="",
                        stderr="",
                    ),
                    testing.Exec(
                        command_prefix=[
                            "ip",
                            "route",
                            "replace",
                            "192.168.252.0/24",
                            "via",
                            "192.168.251.1",
                        ],
                        stdout="",
                        stderr="",
                    ),
                },
            )
            state_in = testing.State(
                model=testing.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation, f1_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            assert self.ctx.exec_history[container.name][1].command == [
                "ip",
                "route",
                "replace",
                "192.168.252.0/24",
                "via",
                "192.168.251.1",
            ]

    def test_given_n3_route_created_when_config_changed_then_n3_route_is_not_created(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = testing.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            f1_relation = testing.Relation(
                endpoint="fiveg_f1",
                interface="fiveg_f1",
            )
            config_mount = testing.Mount(
                location="/tmp/conf",
                source=tmpdir,
            )
            container = testing.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["ip", "route", "show"],
                        stdout="192.168.252.0/24 via 192.168.251.1",
                        stderr="",
                    )
                },
            )
            state_in = testing.State(
                model=testing.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation, f1_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            # When testing 7 is out, we should assert that the mock exec was called
            # instead of validating log content
            # Reference: https://github.com/canonical/ops-testing/issues/180
            assert "N3 route created" not in caplog.text
