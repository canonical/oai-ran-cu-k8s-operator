# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


import json

import pytest
from charms.oai_ran_cu_k8s.v0.fiveg_f1 import PLMNConfig
from ops import testing

from tests.unit.lib.charms.oai_ran_cu_k8s.v0.test_charms.test_requirer_charm.src.charm import (
    WhateverCharm,
)

VALID_PLMN = PLMNConfig(mcc="123", mnc="12", sst=1, sd=12)


class TestFivegF1Requires:
    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = testing.Context(
            charm_type=WhateverCharm,
            meta={
                "name": "whatever-charm",
                "requires": {"fiveg_f1": {"interface": "fiveg_f1"}},
            },
            actions={
                "set-f1-information": {"params": {"port": {"type": "string"}}},
                "get-f1-information": {
                    "params": {
                        "expected_ip_address": {"type": "string"},
                        "expected_port": {"type": "string"},
                        "expected_tac": {"type": "string"},
                        "expected_plmns": {"type": "string"},
                    }
                },
                "get-f1-information-invalid": {"params": {}},
            },
        )

    def test_given_valid_f1_port_when_set_f1_information_then_requirer_f1_port_is_pushed_to_the_relation_databag(  # noqa: E501
        self,
    ):
        fiveg_f1_relation = testing.Relation(endpoint="fiveg_f1", interface="fiveg_f1")
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)
        params = {"port": "1234"}

        state_out = self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        relation = state_out.get_relation(fiveg_f1_relation.id)
        assert relation.local_app_data["f1_port"] == "1234"

    def test_given_invalid_f1_port_when_fiveg_f1_provider_available_then_error_is_raised(self):
        fiveg_f1_relation = testing.Relation(endpoint="fiveg_f1", interface="fiveg_f1")
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)
        params = {"port": "Not a valid port"}

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Invalid relation data" in str(e.value)

    def test_given_charm_is_not_leader_when_set_f1_information_then_error_is_raised(self):
        fiveg_f1_relation = testing.Relation(endpoint="fiveg_f1", interface="fiveg_f1")
        state_in = testing.State(relations=[fiveg_f1_relation], leader=False)
        params = {"port": "1234"}

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Unit must be leader to set application relation data." in str(e.value)

    def test_given_f1_relation_does_not_exist_when_set_f1_information_then_error_is_raised(self):
        state_in = testing.State(relations=[], leader=True)
        params = {"port": "1234"}

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Relation fiveg_f1 not created yet." in str(e.value)

    def test_given_remote_app_filled_databag_when_get_f1_information_then_value_is_retrieved(
        self,
    ):
        plmns_as_string = json.dumps([plmn.asdict() for plmn in [VALID_PLMN]])
        fiveg_f1_relation = testing.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
            remote_app_data={
                "f1_ip_address": "1.2.3.4",
                "f1_port": "1234",
                "tac": "12",
                "plmns": plmns_as_string,
            },
        )
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)
        params = {
            "expected_ip_address": "1.2.3.4",
            "expected_port": "1234",
            "expected_tac": "12",
            "expected_plmns": plmns_as_string,
        }

        self.ctx.run(self.ctx.on.action("get-f1-information", params=params), state_in)

    @pytest.mark.parametrize(
        "remote_data",
        [
            pytest.param(
                {
                    "f1_ip_address": "1.2.3.4",
                    "f1_port": "port",
                    "tac": "22",
                },
                id="invalid_port",
            ),
            pytest.param(
                {
                    "f1_ip_address": "1.2.3.4",
                    "f1_port": "1234",
                    "tac": "tac",
                },
                id="invalid_tac",
            ),
        ],
    )
    def test_given_invalid_remote_databag_when_get_f1_information_then_none_is_retrieved(
        self, remote_data
    ):
        plmns_as_string = json.dumps([plmn.asdict() for plmn in [VALID_PLMN]])
        remote_data["plmns"] = plmns_as_string
        fiveg_f1_relation = testing.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
            remote_app_data=remote_data,
        )
        state_in = testing.State(relations=[fiveg_f1_relation], leader=True)

        self.ctx.run(self.ctx.on.action("get-f1-information-invalid", params={}), state_in)

    def test_given_f1_relation_does_not_exist_when_get_f1_information_then_none_is_retrieved(
        self,
    ):
        state_in = testing.State(relations=[], leader=True)

        self.ctx.run(self.ctx.on.action("get-f1-information-invalid", params={}), state_in)
