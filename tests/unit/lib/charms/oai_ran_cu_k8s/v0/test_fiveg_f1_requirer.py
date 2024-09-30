# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch

import pytest
import scenario
from charms.oai_ran_cu_k8s.v0.fiveg_f1 import FivegF1ProviderAvailableEvent

from tests.unit.lib.charms.oai_ran_cu_k8s.v0.test_charms.test_requirer_charm.src.charm import (
    WhateverCharm,
)


class TestFivegF1Requires:
    @pytest.fixture(autouse=True)
    def setUp(self, request):
        yield
        request.addfinalizer(self.tearDown)

    def tearDown(self) -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = scenario.Context(
            charm_type=WhateverCharm,
            meta={
                "name": "whatever-charm",
                "requires": {"fiveg_f1": {"interface": "fiveg_f1"}},
            },
            actions={"set-f1-information": {"params": {"port": {"type": "string"}}}},
        )

    def test_given_fiveg_f1_relation_created_when_relation_changed_then_event_with_provider_f1_ip_address_and_port_is_emitted(  # noqa: E501
        self,
    ):
        fiveg_f1_relation = scenario.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
            remote_app_data={
                "f1_ip_address": "1.2.3.4",
                "f1_port": "1234",
            },
        )
        state_in = scenario.State(
            relations=[fiveg_f1_relation],
            leader=True,
        )

        self.ctx.run(self.ctx.on.relation_changed(fiveg_f1_relation), state_in)

        assert len(self.ctx.emitted_events) == 2
        assert isinstance(self.ctx.emitted_events[1], FivegF1ProviderAvailableEvent)
        assert self.ctx.emitted_events[1].f1_ip_address == "1.2.3.4"
        assert self.ctx.emitted_events[1].f1_port == "1234"

    def test_given_valid_f1_port_when_set_f1_information_then_requirer_f1_port_is_pushed_to_the_relation_databag(  # noqa: E501
        self,
    ):
        fiveg_f1_relation = scenario.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
        )
        state_in = scenario.State(
            relations=[fiveg_f1_relation],
            leader=True,
        )
        params = {
            "port": "1234",
        }

        state_out = self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        relation = state_out.get_relation(fiveg_f1_relation.id)
        assert relation.local_app_data["f1_port"] == "1234"

    def test_given_invalid_f1_port_when_fiveg_f1_provider_available_then_error_is_raised(self):
        fiveg_f1_relation = scenario.Relation(
            endpoint="fiveg_f1",
            interface="fiveg_f1",
        )
        state_in = scenario.State(
            relations=[fiveg_f1_relation],
            leader=True,
        )
        params = {
            "port": "Not a valid port",
        }

        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("set-f1-information", params=params), state_in)

        assert "Invalid relation data" in str(e.value)
