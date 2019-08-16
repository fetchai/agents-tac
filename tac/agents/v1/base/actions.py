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

- ControllerActions: The ControllerActions class defines the actions of an agent towards the ControllerAgent.
- OEFActions: The OEFActions class defines the actions of an agent towards the OEF.
- DialogueActions: The DialogueActions class defines the actions of an agent in the context of a Dialogue.
"""

import logging

from oef.query import Query, Constraint, GtEq

from tac.agents.v1.agent import Liveness
from tac.agents.v1.base.interfaces import ControllerActionInterface, OEFActionInterface, DialogueActionInterface
from tac.agents.v1.base.game_instance import GameInstance
from tac.agents.v1.mail.base import MailBox
from tac.agents.v1.mail.messages import ByteMessage, OEFMessage
from tac.helpers.crypto import Crypto
from tac.platform.protocol import GetStateUpdate

logger = logging.getLogger(__name__)


class ControllerActions(ControllerActionInterface):
    """The ControllerActions class defines the actions of an agent towards the ControllerAgent."""

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, mailbox: MailBox, agent_name: str) -> None:
        """
        Instantiate the ControllerActions.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param mailbox: the mailbox of the agent
        :param agent_name: the agent name

        :return: None
        """
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.mailbox = mailbox
        self.agent_name = agent_name

    def request_state_update(self) -> None:
        """
        Request current agent state from TAC Controller.

        :return: None
        """
        msg = GetStateUpdate(self.crypto.public_key, self.crypto).serialize()
        message = ByteMessage(to=self.game_instance.controller_pbk, sender=self.crypto.public_key, message_id=0, dialogue_id=0, content=msg)
        self.mailbox.outbox.put(message)


class OEFActions(OEFActionInterface):
    """The OEFActions class defines the actions of an agent towards the OEF."""

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, mailbox: MailBox, agent_name: str) -> None:
        """
        Instantiate the OEFActions.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param mailbox: the mailbox of the agent
        :param agent_name: the agent name

        :return: None
        """
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.mailbox = mailbox
        self.agent_name = agent_name

    def search_for_tac(self) -> None:
        """
        Search for active TAC Controller.

        We assume that the controller is registered as a service with the 'tac' data model
        and with an attribute version = 1.

        :return: None
        """
        query = Query([Constraint("version", GtEq(1))])
        search_id = self.game_instance.search.get_next_id()
        self.game_instance.search.ids_for_tac.add(search_id)

        message = OEFMessage(to=None, sender=self.crypto.public_key, oef_type=OEFMessage.Type.SEARCH_SERVICES, id=0, query=query)
        self.mailbox.outbox.put(message)

    def update_services(self) -> None:
        """
        Update services on OEF Service Directory.

        :return: None
        """
        self.unregister_service()
        self.register_service()

    def unregister_service(self) -> None:
        """
        Unregister service from OEF Service Directory.

        :return: None
        """
        if self.game_instance.goods_demanded_description is not None:
            self.mailbox.outbox.put(OEFMessage(to=None, sender=self.crypto.public_key, oef_type=OEFMessage.Type.UNREGISTER_SERVICE, id=1, service_description=self.game_instance.goods_demanded_description, service_id=""))
        if self.game_instance.goods_supplied_description is not None:
            self.mailbox.outbox.put(OEFMessage(to=None, sender=self.crypto.public_key, oef_type=OEFMessage.Type.UNREGISTER_SERVICE, id=1, service_description=self.game_instance.goods_supplied_description, service_id=""))

    def register_service(self) -> None:
        """
        Register to the OEF Service Directory.

        In particular, register
            - as a seller, listing the goods supplied, or
            - as a buyer, listing the goods demanded, or
            - as both.

        :return: None
        """
        if self.game_instance.strategy.is_registering_as_seller:
            logger.debug("[{}]: Updating service directory as seller with goods supplied.".format(self.agent_name))
            goods_supplied_description = self.game_instance.get_service_description(is_supply=True)
            self.game_instance.goods_supplied_description = goods_supplied_description
            self.mailbox.outbox.put(OEFMessage(to=None, sender=self.crypto.public_key, oef_type=OEFMessage.Type.UNREGISTER_SERVICE, id=1, service_description=self.game_instance.goods_supplied_description, service_id=""))
        if self.game_instance.strategy.is_registering_as_buyer:
            logger.debug("[{}]: Updating service directory as buyer with goods demanded.".format(self.agent_name))
            goods_demanded_description = self.game_instance.get_service_description(is_supply=False)
            self.game_instance.goods_demanded_description = goods_demanded_description
            self.mailbox.outbox.put(OEFMessage(to=None, sender=self.crypto.public_key, oef_type=OEFMessage.Type.UNREGISTER_SERVICE, id=1, service_description=self.game_instance.goods_demanded_description, service_id=""))

    def search_services(self) -> None:
        """
        Search on OEF Service Directory.

        In particular, search
            - for sellers and their supply, or
            - for buyers and their demand, or
            - for both.

        :return: None
        """
        if self.game_instance.strategy.is_searching_for_sellers:
            query = self.game_instance.build_services_query(is_searching_for_sellers=True)
            if query is None:
                logger.warning("[{}]: Not searching the OEF for sellers because the agent demands no goods.".format(self.agent_name))
                return None
            else:
                logger.debug("[{}]: Searching for sellers which match the demand of the agent.".format(self.agent_name))
                search_id = self.game_instance.search.get_next_id()
                self.game_instance.search.ids_for_sellers.add(search_id)
                self.mailbox.outbox.put(OEFMessage(to=None, sender=self.crypto.public_key, oef_type=OEFMessage.Type.SEARCH_SERVICES, id=search_id, query=query))
        if self.game_instance.strategy.is_searching_for_buyers:
            query = self.game_instance.build_services_query(is_searching_for_sellers=False)
            if query is None:
                logger.warning("[{}]: Not searching the OEF for buyers because the agent supplies no goods.".format(self.agent_name))
                return None
            else:
                logger.debug("[{}]: Searching for buyers which match the supply of the agent.".format(self.agent_name))
                search_id = self.game_instance.search.get_next_id()
                self.game_instance.search.ids_for_buyers.add(search_id)
                self.mailbox.outbox.put(OEFMessage(to=None, sender=self.crypto.public_key, oef_type=OEFMessage.Type.SEARCH_SERVICES, id=search_id, query=query))


class DialogueActions(DialogueActionInterface):
    """The DialogueActions class defines the actions of an agent in the context of a Dialogue."""

    def __init__(self, crypto: Crypto, liveness: Liveness, game_instance: GameInstance, mailbox: MailBox, agent_name: str) -> None:
        """
        Instantiate the DialogueActions.

        :param crypto: the crypto module
        :param liveness: the liveness module
        :param game_instance: the game instance
        :param mailbox: the mailbox of the agent
        :param agent_name: the agent name

        :return: None
        """
        self.crypto = crypto
        self.liveness = liveness
        self.game_instance = game_instance
        self.mailbox = mailbox
        self.agent_name = agent_name
        self.dialogues = game_instance.dialogues
