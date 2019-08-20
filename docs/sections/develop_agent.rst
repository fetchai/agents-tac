.. _develop_agent:

Developing Your Own Agent
=========================

In this section we describe a number of approaches you could take to develop your own agent.


Familiarize yourself with Sandbox and Playground
------------------------------------------------

To launch the sandbox from root directory run the launchscript:

`python scripts/launch.py`

This lets you explore the competition setup and how the agents trade.

To launch the playground from root directory run:

`python sandbox/playground.py`

This lets you explore the agent and mailbox interface.


Basic: Tuning the Agent's Parameters
------------------------------------

We have developed a :class:`~tac.agents.participant.examples.baseline.BaselineAgent` and a :class:`~tac.agents.participant.examples.strategy.BaselineStrategy` for you. You can run this agent via the `basic template`_.

.. _basic template: https://github.com/fetchai/agents-tac/blob/master/templates/participant/basic.py

By tuning the parameters the agent's trading performance can be improved.

The relevant parameters for agent tuning are:

- `--agent-timeout`, which specifies the time in (fractions of) seconds to time out an agent between act and react.
- `--max-reactions`, which specifies the maximum number of reactions (messages processed) per call to react.
- `--register-as`, which specifies whether the baseline agent registers as seller, buyer or both on the OEF.
- `--search-for`, which specifies whether the baseline agent searches for sellers, buyers or both on the OEF.
- `--is-world-modeling`, which specifies whether the agent models its environment, specifically the goods' prices.
- `--services-interval`, which specifies the number of seconds to wait before doing another search. Searches kick off negotiations. A lower services interval directly translates to a higher number of negotiations.

To evaluate changes in parameters on agent performance you can run your agent against several agents with baseline parameters in the sandbox (see the quickstart on `main readme`_ or the guide in `sandbox readme`_ for details how to start the sandbox and your agent).

.. _main readme: https://github.com/fetchai/agents-tac/blob/master/README.md

.. _sandbox readme: https://github.com/fetchai/agents-tac/blob/master/sandbox/README.md

Alternatively, you can use our Sandbox Launch App to do a grid parameter search for a population of agents. The Sandbox Launch App can be launched via executing the following command from root directory:

`python tac/gui/panel/app.py`


Advanced: Changing the Agent's Strategy
---------------------------------------


An intermediate approach to developing your own agent is to adjust the strategy of your agent whilst still relying on our :class:`~tac.agents.participant.examples.baseline.BaselineAgent` implementation. This way you can focus on the decision making component of the agent relevant for the TAC.

The strategy interface is defined in :class:`~tac.agents.participant.base.strategy.Strategy`. It defines the following methods:

- :meth:`~tac.agents.participant.base.strategy.Strategy.supplied_good_quantities` to specify the list of quantities which are supplied by the agent.
- :meth:`~tac.agents.participant.base.strategy.Strategy.supplied_good_pbks` to specify the set of good public keys which are supplied by the agent.
- :meth:`~tac.agents.participant.base.strategy.Strategy.demanded_good_quantities` to specify the list of quantities which are demanded by the agent.
- :meth:`~tac.agents.participant.base.strategy.Strategy.demanded_good_pbks` to specify the set of good public keys which are demanded by the agent.
- :meth:`~tac.agents.participant.base.strategy.Strategy.get_proposals` to specify the proposals from the agent in the role of seller/buyer.

The :meth:`~tac.agents.participant.base.strategy.Strategy.supplied_good_quantities` and :meth:`~tac.agents.participant.base.strategy.Strategy.demanded_good_quantities` methods are used to :meth:`~tac.agents.participant.base.game_instance.GameInstance.get_service_description`. The service descriptions thus generated are used for registration on the OEF. Changing these methods therefore directly affects what an agent registers and what services/goods of the agent other agents can therefore find.

The :meth:`~tac.agents.participant.base.strategy.Strategy.supplied_good_pbks` and :meth:`~tac.agents.participant.base.strategy.Strategy.demanded_good_pbks` methods are used to :meth:`~tac.agents.participant.base.game_instance.GameInstance.build_services_query`. The service queries thus generated are used to search for services/goods on the OEF. Changing these methods therefore directly affects what an agent searches on the OEF.

The :meth:`~tac.agents.participant.base.strategy.Strategy.get_proposals` method is used to generate proposals. Changing this method directly affects what an agent proposes. Of particular relevance here is the price at which an agent proposes to sell\buy the goods referenced in the proposal.


Expert: Start from Scratch
--------------------------

The :class:`~tac.agents.participant.base.participant_agent.ParticipantAgent` is one possible implementation of an agent campable of competing in the TAC. You can build your own implementation by starting from scratch entirely or building on top of our basic :class:`~tac.agents.participant.agent.Agent`. We are excited to see what you will build!
