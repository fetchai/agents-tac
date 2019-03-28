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
import logging
from abc import abstractmethod
from typing import List

logger = logging.getLogger("tac")


def callback(fut):
    """Callback to audit exception from asyncio tasks."""
    try:
        _ = fut.result()
    except Exception as e:
        logger.exception('Unexpected error')
        raise e


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
            return '"{}" -> "{}": {}\n'.format(self.sender, self.receiver, self.message)

    class Note(Drawable):

        def __init__(self, msg: str, over: str):
            self.msg = msg
            self.over = over

        def draw(self):
            return 'note over "{}"\n{}\nend note\n'.format(self.msg, self.over).replace("'", "\"")

    def __init__(self):
        self.drawables = []  # type: List[PlantUMLGenerator.Drawable]

    def add_drawable(self, dw: Drawable):
        self.drawables.append(dw)

    def dump(self, file: str):
        with open(file, "w") as fout:
            fout.writelines("@startuml\n")
            for d in self.drawables:
                fout.write(d.draw())
            fout.writelines("@enduml\n")


plantuml_gen = PlantUMLGenerator()

