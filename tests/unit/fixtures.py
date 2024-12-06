#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import PropertyMock, patch

import pytest
from ops import testing

from charm import OAIRANCUOperator


class CUCharmFixtures:
    patcher_check_output = patch("charm.check_output")
    patcher_k8s_privileged = patch("charm.K8sPrivileged")
    patcher_k8s_multus = patch("charm.KubernetesMultusCharmLib")
    patcher_publish_gnb_information = patch("charm.FivegCoreGnbRequires.publish_gnb_information")
    patcher_gnb_core_remote_tac = patch(
        "charm.FivegCoreGnbRequires.tac", new_callable=PropertyMock
    )
    patcher_gnb_core_remote_plmns = patch(
        "charm.FivegCoreGnbRequires.plmns", new_callable=PropertyMock
    )
    patcher_f1_set_information = patch("charm.F1Provides.set_f1_information")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_publish_gnb_information = CUCharmFixtures.patcher_publish_gnb_information.start()
        self.mock_gnb_core_remote_tac = CUCharmFixtures.patcher_gnb_core_remote_tac.start()
        self.mock_gnb_core_remote_plmns = CUCharmFixtures.patcher_gnb_core_remote_plmns.start()
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
