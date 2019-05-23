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

import numpy as np


class PriceBandit(object):
    def __init__(self, price: float):
        """
        Instantiate a price bandit object.

        :param price: the price this bandit is modelling
        :param beta_a: the a parameter of the beta distribution
        :param beta_b: the b parameter of the beta distribution
        """
        self.price = price
        # we assume a uniform random prior
        self.beta_a = 1
        self.beta_b = 1

    def sample(self) -> float:
        """
        Sample from the bandit

        :return: the sampled value
        """
        return np.random.beta(self.beta_a, self.beta_b)

    def update(self, outcome: bool) -> None:
        """
        Update the bandit

        :param outcome: the outcome used for updating
        """
        self.beta_a += outcome
        self.beta_b += 1 - outcome


class GoodPriceModel(object):
    def __init__(self):
        """
        Instantiate a good price model.
        """
        self.price_bandits = dict(
            (price, PriceBandit(price))
            for price in [i / 10 for i in range(201)])

    def update(self, outcome: bool, price: float) -> None:
        """
        Update the respective bandit.

        :param price: the price to be updated
        :param outcome: the negotiation outcome
        :return: None
        """
        bandit = self.price_bandits[price]
        bandit.update(outcome)

    def get_price_expectation(self, constraint: float = 0.0) -> float:
        """
        Get best price (given a constraint)

        :param constraint: the minimum price
        :return: the winning price
        """
        maxsample = -1
        winning_price = 20.0
        for price, bandit in self.price_bandits.items():
            if price <= constraint: continue
            sample = bandit.sample()
            if sample > maxsample:
                maxsample = sample
                winning_price = price
        return winning_price
