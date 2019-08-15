# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""
This module contains the classes which define the actions of an agent.

- OEFActions: The OEFActions class defines the actions of an agent towards the OEF.
"""

import logging

from oef.schema import Description, DataModel, AttributeSchema

from tac.agents.v1.agent import Liveness
from tac.platform.controller.interfaces import OEFActionInterface
from tac.agents.v1.mail import OutBox, OutContainer
from tac.helpers.crypto import Crypto

logger = logging.getLogger(__name__)

CONTROLLER_DATAMODEL = DataModel("tac", [
    AttributeSchema("version", int, True, "Version number of the TAC Controller Agent."),
])


class OEFActions(OEFActionInterface):
    """The OEFActions class defines the actions of an agent towards the OEF."""

    def __init__(self, crypto: Crypto, liveness: Liveness, out_box: 'OutBox', agent_name: str) -> None:
        """
        Instantiate the OEFActions.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param out_box: the outbox of the agent
        :param agent_name: the agent name

        :return: None
        """
        self.crypto = crypto
        self.liveness = liveness
        self.out_box = out_box
        self.agent_name = agent_name

    def register_tac(self) -> None:
        """
        Register on the OEF as a TAC controller agent.

        :return: None.
        """
        desc = Description({"version": 1}, data_model=CONTROLLER_DATAMODEL)
        logger.debug("[{}]: Registering with {} data model".format(self.agent_name, desc.data_model.name))
        self.out_box.out_queue.put(OutContainer(service_description=desc, message_id=1))
