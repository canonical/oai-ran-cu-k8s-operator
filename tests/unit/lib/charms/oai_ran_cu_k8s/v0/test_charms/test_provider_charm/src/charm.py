# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging

from charms.oai_ran_cu_k8s.v0.fiveg_f1 import F1Provides, PLMNConfig
from ops import main
from ops.charm import ActionEvent, CharmBase

logger = logging.getLogger(__name__)


class WhateverCharm(CharmBase):
    def __init__(self, *args):
        """Create a new instance of this object for each event."""
        super().__init__(*args)
        self.fiveg_f1_provider = F1Provides(self, "fiveg_f1")
        self.framework.observe(
            self.on.set_f1_information_action, self._on_set_f1_information_action
        )
        self.framework.observe(
            self.on.set_f1_information_as_string_action,
            self._on_set_f1_information_as_string_action,
        )
        self.framework.observe(
            self.on.get_f1_information_action, self._on_get_f1_information_action
        )

    def _on_set_f1_information_action(self, event: ActionEvent):
        ip_address = event.params.get("ip-address", "")
        port = event.params.get("port", "")
        tac = event.params.get("tac", "")
        plmns = event.params.get("plmns", "")
        self.fiveg_f1_provider.set_f1_information(
            ip_address=ip_address,
            port=port,
            tac=int(tac),
            plmns=[PLMNConfig(**data) for data in json.loads(plmns)],
        )

    def _on_set_f1_information_as_string_action(self, event: ActionEvent):
        ip_address = event.params.get("ip-address", "")
        port = event.params.get("port", "")
        tac = event.params.get("tac", "")
        plmns = event.params.get("plmns", "")
        self.fiveg_f1_provider.set_f1_information(
            ip_address=ip_address,
            port=port,
            tac=tac,
            plmns=[PLMNConfig(**data) for data in json.loads(plmns)],
        )

    def _on_get_f1_information_action(self, event: ActionEvent):
        port_value = event.params.get("expected_port")
        expected_port = int(port_value) if port_value else None
        assert expected_port == self.fiveg_f1_provider.requirer_f1_port


if __name__ == "__main__":
    main(WhateverCharm)
