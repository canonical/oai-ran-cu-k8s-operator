#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import tempfile

import pytest
from charms.oai_ran_cu_k8s.v0.fiveg_f1 import PLMNConfig
from ops import testing
from ops.pebble import Layer

from tests.unit.fixtures import CUCharmFixtures


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
            core_gnb_relation = testing.Relation(
                endpoint="fiveg_core_gnb", interface="fiveg_core_gnb"
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
                relations=[n2_relation, core_gnb_relation],
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

    @pytest.mark.parametrize(
        "plmns,config_file",
        [
            pytest.param(
                [PLMNConfig(mcc="001", mnc="01", sst=1)],
                "tests/unit/resources/expected_config.conf",
                id="single_plmn",
            ),
            pytest.param(
                [
                    PLMNConfig(mcc="001", mnc="01", sst=1),
                    PLMNConfig(mcc="456", mnc="99", sst=16, sd=7532),
                ],
                "tests/unit/resources/expected_config_multiple_plmns.conf",
                id="two_plmns",
            ),
        ],
    )
    def test_given_workload_is_ready_to_be_configured_when_config_changed_then_cu_config_file_is_generated_and_pushed_to_the_workload_container(  # noqa: E501
        self, plmns, config_file
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
            core_gnb_relation = testing.Relation(
                endpoint="fiveg_core_gnb", interface="fiveg_core_gnb"
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
                relations=[n2_relation, core_gnb_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            self.mock_gnb_core_remote_tac.return_value = 1
            self.mock_gnb_core_remote_plmns.return_value = plmns

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            with open(config_file) as expected_config_file:
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
            self.mock_gnb_core_remote_tac.return_value = 1
            self.mock_gnb_core_remote_plmns.return_value = [PLMNConfig(mcc="001", mnc="01", sst=1)]
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
            core_gnb_relation = testing.Relation(
                endpoint="fiveg_core_gnb", interface="fiveg_core_gnb"
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
                relations=[n2_relation, core_gnb_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            self.mock_gnb_core_remote_tac.return_value = 67
            plmns = [PLMNConfig(mcc="001", mnc="01", sst=99)]
            self.mock_gnb_core_remote_plmns.return_value = plmns

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

    def test_given_core_gnb_remote_tac_and_plmns_are_none_when_fiveg_core_gnb_relation_is_added_then_gnb_name_is_published(  # noqa: E501
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
            fiveg_core_gnb_relation = testing.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
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
                relations=[n2_relation, fiveg_core_gnb_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            self.mock_gnb_core_remote_tac.return_value = None
            self.mock_gnb_core_remote_plmns.return_value = None

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_publish_gnb_information.assert_called_once_with(
                gnb_name="whatever-oai-ran-cu-k8s-cu",
            )

    def test_given_core_gnb_remote_tac_and_plmns_are_available_when_f1_relation_is_added_then_f1_ip_port_tac_and_plmns_are_published(  # noqa: E501
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
            core_gnb_relation = testing.Relation(
                endpoint="fiveg_core_gnb", interface="fiveg_core_gnb"
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
                relations=[n2_relation, f1_relation, core_gnb_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            self.mock_gnb_core_remote_tac.return_value = 87
            plmns = [PLMNConfig(mcc="431", mnc="01", sst=17)]
            self.mock_gnb_core_remote_plmns.return_value = plmns

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_f1_set_information.assert_called_once_with(
                ip_address="192.168.254.7",
                port=2152,
                tac=87,
                plmns=plmns,
            )

    def test_given_core_gnb_remote_tac_and_plmns_are_none_when_config_changed_then_f1_information_is_not_published(  # noqa: E501
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
            fiveg_core_gnb_relation = testing.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
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
                relations=[n2_relation, fiveg_core_gnb_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            self.mock_gnb_core_remote_tac.return_value = None
            self.mock_gnb_core_remote_plmns.return_value = None

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_f1_set_information.assert_not_called()

    def test_given_charm_is_active_when_config_changed_then_updated_f1_interface_ip_port_tac_and_plmns_are_published(  # noqa: E501
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
            core_gnb_relation = testing.Relation(
                endpoint="fiveg_core_gnb", interface="fiveg_core_gnb"
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
                relations=[n2_relation, f1_relation, core_gnb_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            self.mock_gnb_core_remote_tac.return_value = 1
            plmns = [PLMNConfig(mcc="001", mnc="01", sst=1, sd=6)]
            self.mock_gnb_core_remote_plmns.return_value = plmns

            self.ctx.run(self.ctx.on.config_changed(), state_in)

            self.mock_f1_set_information.assert_called_with(
                ip_address=test_f1_ip_address.split("/")[0],
                port=3522,
                tac=1,
                plmns=plmns,
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
            core_gnb_relation = testing.Relation(
                endpoint="fiveg_core_gnb", interface="fiveg_core_gnb"
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
                relations=[n2_relation, f1_relation, core_gnb_relation],
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
