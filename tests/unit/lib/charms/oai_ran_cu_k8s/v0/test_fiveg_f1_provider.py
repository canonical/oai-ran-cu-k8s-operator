# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json

import pytest
from charms.oai_ran_cu_k8s.v0.fiveg_f1 import PLMNConfig
from ops import testing
from pydantic import ValidationError

from tests.unit.lib.charms.oai_ran_cu_k8s.v0.test_charms.test_provider_charm.src.charm import (
    WhateverCharm,
)

VALID_IP = "1.2.3.4"
VALID_PLMN = PLMNConfig(mcc="123", mnc="12", sst=1, sd=12)


class TestFivegF1Provides:
    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = testing.Context(
            charm_type=WhateverCharm,
            meta={
                "name": "whatever-charm",
                "provides": {"fiveg_f1": {"interface": "fiveg_f1"}},
            },
            actions={
                "set-f1-information": {
                    "params": {
                        "ip-address": {"type": "string"},
                        "port": {"type": "string"},
                        "tac": {"type": "string"},
                        "plmns": {"type": "string"},
                    }
                },
                "set-f1-information-as-string": {
                    "params": {
                        "ip-address": {"type": "string"},
                        "port": {"type": "string"},
                        "tac": {"type": "string"},
                        "plmns": {"type": "string"},
                    }
                },
                "get-f1-information": {
                    "params": {
                        "expected_port": {"type": "string"},
                    }
                },
            },
        )

    @pytest.mark.parametrize(
        "plmns",
        [
            pytest.param([VALID_PLMN], id="sd_is_present"),
            pytest.param([PLMNConfig(mcc="123", mnc="12", sst=1)], id="sd_is_none"),
            pytest.param([VALID_PLMN, VALID_PLMN], id="many_lists"),
        ],
    )
    def test_given_valid_f1_interface_data_when_set_f1_information_then_f1_ip_address_port_tac_and_plmns_are_pushed_to_the_relation_databag(  # noqa: E501
        self, plmns
    ):
        fiveg_f1_relation = testing.Relation(endpoint="fiveg_f1", interface="fiveg_f1")
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)
        plmns_as_string = json.dumps([plmn.asdict() for plmn in plmns])
        params = {"ip-address": VALID_IP, "port": "1234", "tac": "12", "plmns": plmns_as_string}

        state_out = self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        relation = state_out.get_relation(fiveg_f1_relation.id)
        assert relation.local_app_data["f1_ip_address"] == VALID_IP
        assert relation.local_app_data["f1_port"] == "1234"
        assert relation.local_app_data["tac"] == "12"
        assert relation.local_app_data["plmns"] == plmns_as_string

    def test_given_charm_is_not_leader_when_set_f1_information_then_error_is_raised(self):
        fiveg_f1_relation = testing.Relation(endpoint="fiveg_f1", interface="fiveg_f1")
        state_in = testing.State(relations=[fiveg_f1_relation], leader=False)
        plmns_as_string = json.dumps([plmn.asdict() for plmn in [VALID_PLMN]])
        params = {"ip-address": VALID_IP, "port": "3", "tac": "123", "plmns": plmns_as_string}

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Unit must be leader to set application relation data." in str(e.value)

    def test_given_f1_relation_does_not_exist_when_set_f1_information_then_error_is_raised(self):
        state_in = testing.State(relations=[], leader=True)
        plmns_as_string = json.dumps([plmn.asdict() for plmn in [VALID_PLMN]])
        params = {"ip-address": VALID_IP, "port": "3", "tac": "123", "plmns": plmns_as_string}

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Relation fiveg_f1 not created yet." in str(e.value)

    @pytest.mark.parametrize(
        "tac",
        [
            pytest.param("0", id="too_small_tac"),
            pytest.param("16777216", id="too_big_tac"),
        ],
    )
    def test_given_invalid_range_tac_when_set_f1_information_then_error_is_raised(self, tac):
        fiveg_f1_relation = testing.Relation(endpoint="fiveg_f1", interface="fiveg_f1")
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)
        plmns_as_string = json.dumps([plmn.asdict() for plmn in [VALID_PLMN]])
        params = {"ip-address": VALID_IP, "port": "3", "tac": tac, "plmns": plmns_as_string}

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Invalid relation data" in str(e.value)

    def test_given_empty_plmns_list_when_set_f1_information_then_error_is_raised(self):
        fiveg_f1_relation = testing.Relation(endpoint="fiveg_f1", interface="fiveg_f1")
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)
        params = {"ip-address": VALID_IP, "port": "3", "tac": "23", "plmns": "[]"}

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Invalid relation data" in str(e.value)

    @pytest.mark.parametrize(
        "ip_address,port,tac",
        [
            pytest.param("1111.1111.1111.1111", "1234", "12", id="invalid_ip_address"),
            pytest.param("", "1234", "12", id="empty_ip_address"),
            pytest.param(VALID_IP, "port", "12", id="invalid_port"),
            pytest.param(VALID_IP, "", "12", id="empty_port"),
            pytest.param(VALID_IP, "12", "tac", id="invalid_tac"),
            pytest.param(VALID_IP, "12", "", id="empty_tac"),
        ],
    )
    def test_given_invalid_string_format_ip_address_port_or_tac_when_set_f1_information_then_error_is_raised(  # noqa: E501
        self, ip_address, port, tac
    ):
        fiveg_f1_relation = testing.Relation(endpoint="fiveg_f1", interface="fiveg_f1")
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)
        plmns_as_string = json.dumps([plmn.asdict() for plmn in [VALID_PLMN]])
        params = {"ip-address": ip_address, "port": port, "tac": tac, "plmns": plmns_as_string}

        with pytest.raises(Exception) as e:
            self.ctx.run(
                self.ctx.on.action("set-f1-information-as-string", params=params),
                state_in,
            )

        assert "Invalid relation data" in str(e.value)

    @pytest.mark.parametrize(
        "remote_port,expected_port",
        [
            pytest.param("1234", "1234", id="valid_port"),
            pytest.param("invalid", "", id="invalid_port"),
        ],
    )
    def test_given_remote_app_filled_databag_when_get_f1_information_then_value_is_retrieved(  # noqa: E501
        self, remote_port, expected_port
    ):
        fiveg_f1_relation = testing.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
            remote_app_data={"f1_port": remote_port},
        )
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)
        params = {"expected_port": expected_port}

        self.ctx.run(self.ctx.on.action("get-f1-information", params=params), state_in)

    def test_given_f1_relation_does_not_exist_when_get_f1_information_then_none_value_is_retrieved(  # noqa: E501
        self,
    ):
        state_in = testing.State(relations=[], leader=True)
        params = {"expected_port": ""}
        self.ctx.run(self.ctx.on.action("get-f1-information", params=params), state_in)

    @pytest.mark.parametrize(
        "mcc,mnc,sst,sd",
        [
            pytest.param(None, "01", 2, 3, id="None_mcc"),
            pytest.param("mcc", "01", 2, 3, id="string_mcc"),
            pytest.param("01", "01", 2, 3, id="2_character_mcc"),
            pytest.param("0122", "01", 2, 3, id="4_character_mcc"),
            pytest.param("001", None, 2, 3, id="None_mnc"),
            pytest.param("001", "mnc", 2, 3, id="string_mnc"),
            pytest.param("001", "1", 2, 3, id="1_character_mnc"),
            pytest.param("001", "1234", 2, 3, id="4_character_mnc"),
            pytest.param("001", "01", None, 3, id="None_sst"),
            pytest.param("001", "01", "sst", 3, id="string_sst"),
            pytest.param("001", "01", -1, 2, id="too_small_sst"),
            pytest.param("001", "01", 256, 2, id="too_big_sst"),
            pytest.param("001", "01", 2, "sd", id="string_sd"),
            pytest.param("001", "01", 2, -1, id="too_small_sd"),
            pytest.param("001", "01", 2, 16777216, id="too_big_sd"),
        ],
    )
    def test_given_invalid_plmns_then_error_is_raised_at_construction(self, mcc, mnc, sst, sd):
        with pytest.raises(ValidationError) as e:
            PLMNConfig(mcc=mcc, mnc=mnc, sst=sst, sd=sd)

        assert "1 validation error for PLMNConfig" in str(e.value)

    @pytest.mark.parametrize(
        "mcc,mnc,sst,sd",
        [
            pytest.param("201", "01", 2, 3, id="2_character_nmc"),
            pytest.param("405", "011", 2, 3, id="3_character_mcc"),
            pytest.param("455", "123", 0, 3, id="smallest_sst"),
            pytest.param("735", "255", 255, 3, id="biggest_sst"),
            pytest.param("135", "123", 2, 0, id="smallest_sd"),
            pytest.param("863", "01", 3, 16777215, id="biggest_sd"),
            pytest.param("245", "01", 3, None, id="None_sd"),
        ],
    )
    def test_given_valid_plmns_then_error_is_not_raised_at_construction(self, mcc, mnc, sst, sd):
        PLMNConfig(mcc=mcc, mnc=mnc, sst=sst, sd=sd)
