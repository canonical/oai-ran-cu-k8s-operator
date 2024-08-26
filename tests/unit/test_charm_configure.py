#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import tempfile

import scenario
from ops.pebble import Layer

from tests.unit.fixtures import CUCharmFixtures


class TestCharmConfigure(CUCharmFixtures):
    def test_given_statefulset_is_not_patched_when_config_changed_then_statefulset_is_patched(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = scenario.Mount(
                location="/tmp/conf",
                src=tmpdir,
            )
            container = scenario.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = scenario.State(
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = False
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run("config_changed", state_in)

            self.mock_k8s_privileged.patch_statefulset.assert_called_with(container_name="cu")

    def test_given_statefulset_is_patched_when_config_changed_then_statefulset_is_not_patched(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = scenario.Mount(
                location="/tmp/conf",
                src=tmpdir,
            )
            container = scenario.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = scenario.State(
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run("config_changed", state_in)

            self.mock_k8s_privileged.patch_statefulset.assert_not_called()

    def test_given_workload_is_ready_to_be_configured_when_config_changed_then_cu_config_file_is_generated_and_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = scenario.Mount(
                location="/tmp/conf",
                src=tmpdir,
            )
            container = scenario.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = scenario.State(
                model=scenario.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.2.3.4"

            self.ctx.run("config_changed", state_in)

            with open("tests/unit/resources/expected_config.conf") as expected_config_file:
                expected_config = expected_config_file.read()

            with open(f"{tmpdir}/cu.conf") as cu_conf:
                assert cu_conf.read().strip() == expected_config.strip()

    def test_given_cu_config_file_is_up_to_date_when_config_changed_then_cu_config_file_is_not_pushed_to_the_workload_container(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = scenario.Mount(
                location="/tmp/conf",
                src=tmpdir,
            )
            container = scenario.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = scenario.State(
                model=scenario.Model(name="whatever"),
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

            self.ctx.run("config_changed", state_in)

            with open(f"{tmpdir}/cu.conf") as cu_conf:
                assert cu_conf.read().strip() == expected_config.strip()
            assert os.stat(tmpdir + "/cu.conf").st_mtime == config_modification_time

    def test_given_charm_configuration_is_done_when_config_changed_then_pebble_layer_is_created(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            config_mount = scenario.Mount(
                location="/tmp/conf",
                src=tmpdir,
            )
            container = scenario.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = scenario.State(
                model=scenario.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            state_out = self.ctx.run("config_changed", state_in)

            assert state_out.containers[0].layers["cu"] == Layer(
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
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            fiveg_gnb_relation = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
            )
            config_mount = scenario.Mount(
                location="/tmp/conf",
                src=tmpdir,
            )
            container = scenario.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = scenario.State(
                model=scenario.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation, fiveg_gnb_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run("config_changed", state_in)

            self.mock_gnb_identity.assert_called_once_with(
                relation_id=fiveg_gnb_relation.relation_id,
                gnb_name="whatever-oai-ran-cu-k8s-cu",
                tac=1,
            )

    def test_given_charm_is_configured_and_running_when_f1_relation_is_added_then_f1_interface_ip_and_port_is_published(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            f1_relation = scenario.Relation(
                endpoint="fiveg_f1",
                interface="fiveg_f1",
            )
            config_mount = scenario.Mount(
                location="/tmp/conf",
                src=tmpdir,
            )
            container = scenario.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = scenario.State(
                model=scenario.Model(name="whatever"),
                leader=True,
                containers=[container],
                relations=[n2_relation, f1_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run("config_changed", state_in)

            self.mock_f1_set_information.assert_called_once_with(
                ip_address="192.168.251.7",
                port=2153,
            )

    def test_given_charm_is_active_when_config_changed_then_updated_f1_interface_ip_and_port_is_published(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            f1_relation = scenario.Relation(
                endpoint="fiveg_f1",
                interface="fiveg_f1",
            )
            config_mount = scenario.Mount(
                location="/tmp/conf",
                src=tmpdir,
            )
            container = scenario.Container(
                name="cu",
                mounts={"config": config_mount},
                can_connect=True,
            )
            state_in = scenario.State(
                model=scenario.Model(name="whatever"),
                config={"f1-ip-address": "10.3.5.1/24", "f1-port": 3522},
                leader=True,
                containers=[container],
                relations=[n2_relation, f1_relation],
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"

            self.ctx.run("config_changed", state_in)

            self.mock_f1_set_information.assert_called_with(ip_address="10.3.5.1", port=3522)
