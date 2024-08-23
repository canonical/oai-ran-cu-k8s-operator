# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import logging

from charms.oai_ran_cu_k8s.v0.fiveg_f1 import F1Provides
from ops.charm import ActionEvent, CharmBase
from ops.main import main

logger = logging.getLogger(__name__)


class WhateverCharm(CharmBase):
    def __init__(self, *args):
        """Create a new instance of this object for each event."""
        super().__init__(*args)
        self.fiveg_f1_provider = F1Provides(self, "fiveg_f1")
        self.framework.observe(
            self.on.set_f1_information_action, self._on_set_f1_information_action
        )

    def _on_set_f1_information_action(self, event: ActionEvent):
        ip_address = event.params.get("ip-address", "")
        port = event.params.get("port", "")
        self.fiveg_f1_provider.set_f1_information(ip_address=ip_address, port=port)


if __name__ == "__main__":
    main(WhateverCharm)
