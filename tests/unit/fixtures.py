#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch

import pytest
from ops import testing

from charm import OAIRANCUOperator


class CUCharmFixtures:
    patcher_check_output = patch("charm.check_output")
    patcher_k8s_privileged = patch("charm.K8sPrivileged")
    patcher_k8s_multus = patch("charm.KubernetesMultusCharmLib")
    patcher_gnb_identity = patch("charm.GnbIdentityProvides.publish_gnb_identity_information")
    patcher_f1_set_information = patch("charm.F1Provides.set_f1_information")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_gnb_identity = CUCharmFixtures.patcher_gnb_identity.start()
        self.mock_check_output = CUCharmFixtures.patcher_check_output.start()
        self.mock_f1_set_information = CUCharmFixtures.patcher_f1_set_information.start()
        self.mock_k8s_privileged = CUCharmFixtures.patcher_k8s_privileged.start().return_value
        self.mock_k8s_multus = CUCharmFixtures.patcher_k8s_multus.start().return_value
        yield
        request.addfinalizer(self.tearDown)

    def tearDown(self) -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = testing.Context(
            charm_type=OAIRANCUOperator,
        )
