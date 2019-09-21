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

from aea.protocols.oef.models import Description, DataModel, Attribute

from aea.agent import Liveness
from aea.crypto.base import Crypto
from aea.mail.base import MailBox
from aea.protocols.oef.message import OEFMessage
from aea.protocols.oef.serialization import OEFSerializer, DEFAULT_OEF
from tac.agents.controller.base.interfaces import OEFActionInterface

logger = logging.getLogger(__name__)

CONTROLLER_DATAMODEL = DataModel("tac", [
    Attribute("version", str, True, "Version number of the TAC Controller Agent."),
])


class OEFActions(OEFActionInterface):
    """The OEFActions class defines the actions of an agent towards the OEF."""

    def __init__(self, crypto: Crypto, liveness: Liveness, mailbox: MailBox, agent_name: str, tac_version_id: str) -> None:
        """
        Instantiate the OEFActions.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param mailbox: the mailbox of the agent
        :param agent_name: the agent name
        :param tac_version: the tac version id

        :return: None
        """
        self.crypto = crypto
        self.liveness = liveness
        self.mailbox = mailbox
        self.agent_name = agent_name
        self.tac_version_id = tac_version_id

    def register_tac(self) -> None:
        """
        Register on the OEF as a TAC controller agent.

        :return: None.
        """
        desc = Description({"version": self.tac_version_id}, data_model=CONTROLLER_DATAMODEL)
        logger.debug("[{}]: Registering with {} data model".format(self.agent_name, desc.data_model.name))
        msg = OEFMessage(oef_type=OEFMessage.Type.REGISTER_SERVICE, id=1, service_description=desc, service_id="")
        msg_bytes = OEFSerializer().encode(msg)
        self.mailbox.outbox.put_message(to=DEFAULT_OEF, sender=self.crypto.public_key, protocol_id=OEFMessage.protocol_id, message=msg_bytes)
