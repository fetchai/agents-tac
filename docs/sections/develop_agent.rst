.. _develop_agent:

Developing Your Own Agent
=========================

In this section we describe a number of approaches you could take to develop your own agent.


Basic: Tuning the Agent's Parameters
------------------------------------

We have developed a :class:`~tac.agents.v1.examples.baseline.BaselineAgent` and a :class:`~tac.agents.v1.examples.strategy.BaselineStrategy` for you. You can run this agent via the `basic template`_.

.. _basic template: https://github.com/fetchai/agents-tac/blob/master/templates/v1/basic.py

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


Advanced: Changing the Agent's Strategy
---------------------------------------


An intermediate approach to developing your own agent is to adjust the strategy of your agent whilst still relying on our :class:`~tac.agents.v1.examples.baseline.BaselineAgent` implementation. This way you can focus on the decision making component of the agent relevant for the TAC.

The strategy interface is defined in :class:`~tac.agents.v1.base.strategy.Strategy`. It defines the following methods:

- :meth:`~tac.agents.v1.base.strategy.Strategy.supplied_good_quantities` to specify the list of quantities which are supplied by the agent.
- :meth:`~tac.agents.v1.base.strategy.Strategy.supplied_good_pbks` to specify the set of good public keys which are supplied by the agent.
- :meth:`~tac.agents.v1.base.strategy.Strategy.demanded_good_quantities` to specify the list of quantities which are demanded by the agent.
- :meth:`~tac.agents.v1.base.strategy.Strategy.demanded_good_pbks` to specify the set of good public keys which are demanded by the agent.
- :meth:`~tac.agents.v1.base.strategy.Strategy.get_proposals` to specify the proposals from the agent in the role of seller/buyer.

The 

write a section dedicated to how the supplied_good_quantities, supplied_good_pbks, demanded_good_quantities and demanded_good_pbks methods get involved in a generic negotiation, potentially supported by sequence diagrams.


Expert: Start from Scratch
--------------------------

The :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` is one possible implementation of an agent campable of competing in the TAC. You can build your own implementation by starting from scratch entirely or building on top of our basic :class:`~tac.agents.v1.agent.Agent`. We are excited to see what you will build!