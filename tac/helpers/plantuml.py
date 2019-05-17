# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------
import os
import pprint
from abc import abstractmethod
from typing import List

from oef.query import Query


class PlantUMLGenerator:

    class Drawable:

        @abstractmethod
        def draw(self):
            pass

    class Transition(Drawable):
        def __init__(self, sender: str, receiver: str, message: str):
            self.sender = sender
            self.receiver = receiver
            self.message = message

        def draw(self):
            return '"{}" -> "{}": {}\n'.format(self.sender, self.receiver,
                                               self.message.replace("\n", "\\n\\\n").replace("'", "\""))

    class Note(Drawable):

        def __init__(self, msg: str, over: str):
            self.msg = msg
            self.over = over

        def draw(self):
            return 'note over "{}"\n'.format(self.over) + '{}\nend note\n'.format(self.msg).replace("'", "\"")

    def __init__(self):
        self.drawables = []  # type: List[PlantUMLGenerator.Drawable]

    def add_drawable(self, dw: Drawable):
        self.drawables.append(dw)

    def dump(self, directory: str, experiment_name: str) -> None:
        """
        Dump the uml file.

        :param directory: the directory where experiments details are listed.
        :param experiment_name: the name of the folder where the data about experiment will be saved.
        :return: None.
        """
        experiment_dir = directory + "/" + experiment_name

        os.makedirs(experiment_dir, exist_ok=True)
        with open(os.path.join(experiment_dir, "diagram.uml"), "w") as fout:
            fout.writelines("@startuml\n")
            for d in self.drawables:
                fout.write(d.draw())
            fout.writelines("@enduml\n")

    def register_service(self, public_key, service_description):
        self.add_drawable(PlantUMLGenerator.Transition(public_key, "OEF Node", "register_service(model={})"
                                                       .format(service_description.data_model.name)))

    def search_services(self, public_key: str, query: Query, additional_msg: str = ""):
        data_model_string = ("model=" + query.model.name + ", " + additional_msg if additional_msg != "" else "") \
            if query.model is not None else ""
        self.add_drawable(PlantUMLGenerator.Transition(public_key, "OEF Node", "search_services({})"
                                                       .format(data_model_string)))

    def on_search_result(self, public_key, agents):
        self.add_drawable(PlantUMLGenerator
                          .Transition("OEF Node", public_key, "search result: [{}]"
                                      .format(", ".join(sorted(map(lambda x: '"' + x + '"', agents))))))

    def start_competition(self, public_key, current_game):
        for agent_pbk, agent_state in current_game.agent_states.items():
            self.add_drawable(PlantUMLGenerator.Note("{} game state: \n".format(agent_pbk) + str(agent_state) + "\nScore: {}".format(agent_state.get_score()),
                                                     public_key))
            self.add_drawable(PlantUMLGenerator.Transition(public_key, agent_pbk,
                                                           "GameData(money, endowments, preferences, scores, fee)"))

    def handle_valid_transaction(self, public_key, sender, counterparty, transaction_id, _current_game):
        self.add_drawable(PlantUMLGenerator.Note("Transaction {} settled.".format(transaction_id),
                                                 public_key))
        self.add_drawable(PlantUMLGenerator.Note("New holdings:\n" + _current_game.get_holdings_summary(),
                                                 public_key))
        self.add_drawable(PlantUMLGenerator.Note("Details:\n" + "\n"
                                                 .join(["score={}, money={}".format(g.get_score(), g.balance)
                                                        for g in _current_game.agent_states.values()]),
                                                 public_key))

        self.add_drawable(PlantUMLGenerator.Transition(
            public_key, sender, "ConfirmTransaction({})".format(transaction_id)))
        self.add_drawable(PlantUMLGenerator.Transition(
            public_key, counterparty, "ConfirmTransaction({})".format(transaction_id)))

    def handle_invalid_transaction(self, public_key, sender, counterparty, transaction_id):
        self.add_drawable(PlantUMLGenerator.Transition(
            public_key, sender, "Error({})".format(transaction_id)))
        self.add_drawable(PlantUMLGenerator.Transition(
            public_key, counterparty, "Error({})".format(transaction_id)))

    def send_cfp(self, public_key, destination, dialogue_id, content):
        self.add_drawable(PlantUMLGenerator.Transition(public_key, destination, "CFP(dialogue_id={}, {})"
                                                       .format(dialogue_id, content)))

    def decline_cfp(self, public_key, destination, dialogue_id):
        self.add_drawable(PlantUMLGenerator.Note("Decline: holdings\ndo not match query", public_key))
        self.add_drawable(PlantUMLGenerator.Transition(public_key, destination, "Decline({})".format(dialogue_id)))

    def send_propose(self, public_key, origin, dialogue_id, description):
        propose_content = pprint.pformat(dict(filter(lambda x: x[1] > 0, description.values.items())))
        self.add_drawable(PlantUMLGenerator.Transition(public_key, origin, "Propose(dialogue_id={}, {})"
                                                       .format(dialogue_id, propose_content)))


plantuml_gen = PlantUMLGenerator()
