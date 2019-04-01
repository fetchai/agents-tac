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

"""DB ORM models for TAC."""


from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import relationship

engine = create_engine('sqlite:///:memory:', echo=True)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Base = declarative_base()


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    nb_agents = Column(Integer)
    nb_goods = Column(Integer)
    initial_money_amount = Column(Integer)
    agents = relationship("ParticipantDetail")


class ParticipantDetail(Base):
    __tablename__ = "participant_details"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    endowments = relationship("Endowment")
    preferences = relationship("Preference")


class Endowment(Base):
    __tablename__ = "endowments"



class Preference(Base):
    __tablename__ = "preferences"



class Purchase(Base):
    __tablename__ = 'purchases'


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    buyer = Column(String)
    seller = Column(String)
    amount = Column(Integer)

    game_id = Column(Integer, ForeignKey('games.id'))
    purchase_id = Column(Integer, ForeignKey('purchases.id'))
    user = relationship("Purchase", back_populates="purchases")
