# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch
import json
import pytest
from charms.oai_ran_cu_k8s.v0.fiveg_f1 import FivegF1RequirerAvailableEvent, PLMNConfig
from ops import testing

from tests.unit.lib.charms.oai_ran_cu_k8s.v0.test_charms.test_provider_charm.src.charm import (
    WhateverCharm,
)


class TestFivegF1Provides:
    @pytest.fixture(autouse=True)
    def setUp(self, request):
        yield
        request.addfinalizer(self.tearDown)

    def tearDown(self) -> None:
        patch.stopall()

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
                        "tac":  {"type": "string"},
                        "plmns":  {"type": "string"},
                    }
                },
                "set-f1-faulty-information": {
                    "params": {
                        "ip-address": {"type": "string"}, 
                        "port": {"type": "string"},
                        "tac":  {"type": "string"},
                        "plmns":  {"type": "string"},
                    }
                }
            },
        )

    def test_given_valid_f1_interface_data_when_set_f1_information_then_f1_ip_address_and_port_are_pushed_to_the_relation_databag(  # noqa: E501
        self,
    ):
        fiveg_f1_relation = testing.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
        )
        state_in = testing.State(
            relations=[fiveg_f1_relation],
            leader=True,
        )
        plmns = [PLMNConfig(mcc="123", mnc="12", sst=1, sd=12)]
        plmns_as_string = json.dumps([plmn.asdict() for plmn in plmns])
        params = {
            "ip-address": "1.2.3.4",
            "port": "1234",
            "tac": "12",
            "plmns": plmns_as_string,
        }

        state_out = self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        relation = state_out.get_relation(fiveg_f1_relation.id)
        assert relation.local_app_data["f1_ip_address"] == "1.2.3.4"
        assert relation.local_app_data["f1_port"] == "1234"
        assert relation.local_app_data["tac"] == "12"
        assert relation.local_app_data["plmns"] == plmns_as_string
        
    def test_sd_given_valid_f1_interface_data_when_set_f1_information_then_f1_ip_address_and_port_are_pushed_to_the_relation_databag(  # noqa: E501
        self,
    ):
        fiveg_f1_relation = testing.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
        )
        state_in = testing.State(
            relations=[fiveg_f1_relation],
            leader=True,
        )
        plmns = [PLMNConfig(mcc="123", mnc="12", sst=1)]
        plmns_as_string = json.dumps([plmn.asdict() for plmn in plmns])
        params = {
            "ip-address": "1.2.3.4",
            "port": "1234",
            "tac": "12",
            "plmns": plmns_as_string,
        }

        state_out = self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        relation = state_out.get_relation(fiveg_f1_relation.id)
        assert relation.local_app_data["f1_ip_address"] == "1.2.3.4"
        assert relation.local_app_data["f1_port"] == "1234"
        assert relation.local_app_data["tac"] == "12"
        assert relation.local_app_data["plmns"] == plmns_as_string

    @pytest.mark.parametrize(
        "ip_address,port,tac",
        [
            pytest.param("1111.1111.1111.1111","1234","12",id="invalid_ip_address"),
            pytest.param("","1234","12",id="empty_ip_address"),
            pytest.param("1.2.3.4","port","12",id="invalid_port"),
            pytest.param("1.2.3.4","","12",id="empty_port"),
            pytest.param("1.2.3.4","12","tac",id="invalid_tac"),
            pytest.param("1.2.3.4","12","",id="empty_tac"),
        ],
    )
    def test_given_invalid_f1_ip_address_or_port_when_set_f1_information_then_error_is_raised(
        self,ip_address,port,tac
    ):
        fiveg_f1_relation = testing.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
        )
        state_in = testing.State(
            relations=[fiveg_f1_relation],
            leader=True,
        )
        
        plmns = [PLMNConfig(mcc="123", mnc="12", sst=1, sd=12)]
        plmns_as_string = json.dumps([plmn.asdict() for plmn in plmns])
        params = {
            "ip-address": ip_address,
            "port": port,
            "tac": tac,
            "plmns": plmns_as_string,
        }

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-faulty-information", params=params), state_in)

        assert "Invalid relation data" in str(e.value)
        
    @pytest.mark.parametrize(
        "tac,sst,sd",
        [
            pytest.param("0",2,3,id="too_small_tac"),
            pytest.param("16777216",2,3,id="too_big_tac"),
            #pytest.param("1",-1,3,id="too_small_sst"),
            #pytest.param("1",256,3,id="too_big_sst"),
            #pytest.param("1",2,-1,id="too_small_sd"),
            #pytest.param("1",2,16777216,id="too_big_sd"),
        ],
    )
    def test_given_invalid_f1_tac_when_set_f1_information_then_error_is_raised(
        self,tac, sst, sd
    ):
        fiveg_f1_relation = testing.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
        )
        state_in = testing.State(
            relations=[fiveg_f1_relation],
            leader=True,
        )
        
        plmns = [PLMNConfig(mcc="123", mnc="12", sst=sst, sd=sd)]
        plmns_as_string = json.dumps([plmn.asdict() for plmn in plmns])
        params = {
            "ip-address": "1.2.3.4",
            "port": "3",
            "tac": tac,
            "plmns": plmns_as_string,
        }

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Invalid relation data" in str(e.value)

    def test_given_fiveg_f1_relation_created_when_relation_changed_then_event_with_requirer_f1_port_is_emitted(  # noqa: E501
        self,
    ):
        fiveg_f1_relation = testing.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
            remote_app_data={"f1_port": "1234"},
        )
        state_in = testing.State(
            relations=[fiveg_f1_relation],
            leader=True,
        )

        self.ctx.run(self.ctx.on.relation_changed(fiveg_f1_relation), state_in)

        assert len(self.ctx.emitted_events) == 2
        assert isinstance(self.ctx.emitted_events[1], FivegF1RequirerAvailableEvent)
        assert self.ctx.emitted_events[1].f1_port == "1234"
