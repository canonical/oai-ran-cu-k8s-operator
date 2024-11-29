# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json

from charms.oai_ran_cu_k8s.v0.fiveg_f1 import F1Requires, PLMNConfig, ProviderAppData
from ops import main
from ops.charm import ActionEvent, CharmBase


class WhateverCharm(CharmBase):
    def __init__(self, *args):
        """Create a new instance of this object for each event."""
        super().__init__(*args)
        self.fiveg_f1_requirer = F1Requires(self, "fiveg_f1")
        self.framework.observe(
            self.on.set_f1_information_action, self._on_set_f1_information_action
        )
        self.framework.observe(
            self.on.get_f1_information_action, self._on_get_f1_information_action
        )
        self.framework.observe(
            self.on.get_f1_information_invalid_action, self._on_get_f1_information_action_invalid
        )

    def _on_set_f1_information_action(self, event: ActionEvent):
        port = event.params.get("port", "")
        self.fiveg_f1_requirer.set_f1_information(port=port)

    def _on_get_f1_information_action(self, event: ActionEvent):
        ip_address = event.params.get("expected_ip_address", "")
        port = event.params.get("expected_port", "")
        tac = event.params.get("expected_tac", "")
        plmns = event.params.get("expected_plmns", "")
        validated_data = {
            "f1_ip_address": ip_address,
            "f1_port": port,
            "tac": int(tac),
            "plmns": [PLMNConfig(**data) for data in json.loads(plmns)],
        }
        provider_app_data = ProviderAppData(**validated_data)

        assert provider_app_data == self.fiveg_f1_requirer.get_provider_f1_information()

    def _on_get_f1_information_action_invalid(self, event: ActionEvent):
        assert self.fiveg_f1_requirer.get_provider_f1_information() is None


if __name__ == "__main__":
    main(WhateverCharm)
