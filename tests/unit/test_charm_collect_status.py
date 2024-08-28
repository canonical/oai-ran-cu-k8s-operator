#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import tempfile

import pytest
import scenario
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from tests.unit.fixtures import CUCharmFixtures


class TestCharmCollectStatus(CUCharmFixtures):
    def test_given_unit_is_not_leader_when_collect_unit_status_then_status_is_blocked(self):
        state_in = scenario.State(leader=False)

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == BlockedStatus("Scaling is not implemented for this charm")

    @pytest.mark.parametrize(
        "config_param,value",
        [
            pytest.param("n3-ip-address", "", id="empty_n3_ip-address"),
            pytest.param("n3-ip-address", "4.5", id="invalid_n3_ip-address"),
            pytest.param("f1-ip-address", "", id="empty_f1_ip-address"),
            pytest.param("f1-ip-address", "5.5.5/3", id="invalid_f1_ip-address"),
            pytest.param("f1-port", int(), id="empty_f1_port"),
            pytest.param("n2-interface-name", "", id="empty_n2_interface_name"),
            pytest.param("n3-interface-name", "", id="empty_n3_interface_name"),
            pytest.param("f1-interface-name", "", id="empty_f1_interface_name"),
            pytest.param("n2-ip-address", "", id="empty_n2_ip_address"),
            pytest.param("n2-ip-address", "3/3", id="invalid_n2_ip_address"),
            pytest.param("mcc", "", id="empty_mcc"),
            pytest.param("mnc", "", id="empty_mnc"),
            pytest.param("sst", int(), id="empty_sst"),
            pytest.param("tac", int(), id="empty_tac"),
        ],
    )
    def test_given_invalid_config_when_collect_unit_status_then_status_is_blocked(
        self, config_param, value
    ):
        state_in = scenario.State(
            leader=True,
            config={
                config_param: value,
            },
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == BlockedStatus(
            f"The following configurations are not valid: ['{config_param}']"
        )

    def test_given_n2_relation_not_created_when_collect_unit_status_then_status_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="cu",
                can_connect=True,
                mounts={"config": config_mount},
            )
            state_in = scenario.State(
                leader=True,
                config={},
                containers=[container],
            )

            state_out = self.ctx.run("collect_unit_status", state_in)

            assert state_out.unit_status == BlockedStatus("Waiting for N2 relation to be created")

    def test_given_workload_container_cant_be_connected_to_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        n2_relation = scenario.Relation(endpoint="fiveg_n2", interface="fiveg_n2")
        container = scenario.Container(
            name="cu",
            can_connect=False,
        )
        state_in = scenario.State(
            leader=True, config={}, relations=[n2_relation], containers=[container]
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for container to be ready")

    def test_given_pod_ip_is_not_available_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        n2_relation = scenario.Relation(endpoint="fiveg_n2", interface="fiveg_n2")
        container = scenario.Container(
            name="cu",
            can_connect=True,
        )
        self.mock_check_output.return_value = b""
        state_in = scenario.State(
            leader=True, config={}, relations=[n2_relation], containers=[container]
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for Pod IP address to be available")

    def test_given_charm_statefulset_is_not_patched_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        n2_relation = scenario.Relation(endpoint="fiveg_n2", interface="fiveg_n2")
        self.mock_k8s_privileged.is_patched.return_value = False
        self.mock_check_output.return_value = b"1.1.1.1"
        container = scenario.Container(
            name="cu",
            can_connect=True,
        )
        state_in = scenario.State(
            leader=True, config={}, relations=[n2_relation], containers=[container]
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for statefulset to be patched")

    def test_give_storage_is_not_attached_when_collect_unit_status_then_status_is_waiting(self):
        n2_relation = scenario.Relation(endpoint="fiveg_n2", interface="fiveg_n2")
        self.mock_k8s_privileged.is_patched.return_value = True
        self.mock_check_output.return_value = b"1.1.1.1"
        container = scenario.Container(
            name="cu",
            can_connect=True,
        )
        state_in = scenario.State(
            leader=True, config={}, relations=[n2_relation], containers=[container]
        )

        state_out = self.ctx.run("collect_unit_status", state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for storage to be attached")

    def test_given_amf_n2_information_is_not_available_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            n2_relation = scenario.Relation(endpoint="fiveg_n2", interface="fiveg_n2")
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="cu",
                can_connect=True,
                mounts={"config": config_mount},
            )
            state_in = scenario.State(
                leader=True, config={}, relations=[n2_relation], containers=[container]
            )

            state_out = self.ctx.run("collect_unit_status", state_in)

            assert state_out.unit_status == WaitingStatus("Waiting for N2 information")

    def test_given_all_status_check_are_ok_when_collect_unit_status_then_status_is_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="cu",
                can_connect=True,
                mounts={"config": config_mount},
            )
            state_in = scenario.State(
                leader=True, config={}, relations=[n2_relation], containers=[container]
            )

            state_out = self.ctx.run("collect_unit_status", state_in)

            assert state_out.unit_status == ActiveStatus()

    def test_given_multus_disabled_when_collect_status_then_status_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="cu",
                can_connect=True,
                mounts={"config": config_mount},
            )
            state_in = scenario.State(
                leader=True, config={}, relations=[n2_relation], containers=[container]
            )
            self.mock_k8s_multus.multus_is_available.return_value = False

            state_out = self.ctx.run("collect_unit_status", state_in)

            assert state_out.unit_status == BlockedStatus("Multus is not installed or enabled")

    def test_given_multus_not_configured_when_collect_status_then_status_is_waiting(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            n2_relation = scenario.Relation(
                endpoint="fiveg_n2",
                interface="fiveg_n2",
                remote_app_data={
                    "amf_hostname": "amf",
                    "amf_port": "38412",
                    "amf_ip_address": "1.2.3.4",
                },
            )
            self.mock_k8s_privileged.is_patched.return_value = True
            self.mock_check_output.return_value = b"1.1.1.1"
            config_mount = scenario.Mount(
                src=temp_dir,
                location="/tmp/conf",
            )
            container = scenario.Container(
                name="cu",
                can_connect=True,
                mounts={"config": config_mount},
            )
            state_in = scenario.State(
                leader=True, config={}, relations=[n2_relation], containers=[container]
            )
            self.mock_k8s_multus.multus_is_available.return_value = True
            self.mock_k8s_multus.is_ready.return_value = False

            state_out = self.ctx.run("collect_unit_status", state_in)

            assert state_out.unit_status == WaitingStatus("Waiting for Multus to be ready")
