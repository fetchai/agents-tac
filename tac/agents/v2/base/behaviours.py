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
import logging
import pprint
import random

from oef.messages import CFP

from tac.agents.v2.base.game_instance import GameInstance
from tac.agents.v2.base.dialogues import Dialogue
from tac.platform.protocol import Decline, Propose

logger = logging.getLogger(__name__)


class FIPABehaviour:
    """
    Specifies FIPA behaviours
    """

    def __init__(self, game_instance: GameInstance):
        self._game_instance = game_instance

    @property
    def game_instance(self) -> GameInstance:
        return self._game_instance

    def on_cfp(self, cfp: CFP, dialogue: Dialogue) -> None:
        """
        Handles cfp.

        :param cfp: the CFP
        :return: None
        """
        goods_description = self.game_instance.get_service_description(is_supply=dialogue.is_seller)
        new_msg_id = cfp.msg_id + 1
        if not cfp.query.check(goods_description):
            logger.debug("[{}]: Current holdings do not satisfy CFP query.".format(self.name))
            logger.debug("[{}]: sending to {} a Decline{}".format(self.name, cfp.destination,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue.id,
                                                                      "origin": cfp.destination,
                                                                      "target": cfp.msg_id
                                                                  })))
            response = Decline(new_msg_id, dialogue.id, cfp.destination, cfp.msg_id)
        else:
            proposals = [random.choice(self.game_instance.get_proposals(cfp.query, dialogue.is_seller))]
            self.game_instance.lock_manager.store_proposals(proposals, new_msg_id, dialogue.id, cfp.destination, dialogue.is_seller)
            logger.debug("[{}]: sending to {} a Propose{}".format(self.name, cfp.destination,
                                                                  pprint.pformat({
                                                                      "msg_id": new_msg_id,
                                                                      "dialogue_id": dialogue.id,
                                                                      "origin": cfp.destination,
                                                                      "target": cfp.msg_id,
                                                                      "propose": proposals[0].values  # TODO fix if more than one proposal!
                                                                  })))
            response = Propose(new_msg_id, dialogue.id, cfp.destination, cfp.msg_id, proposals)
        return response
