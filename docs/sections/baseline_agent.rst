.. _baseline_agent:

Baseline Agent v2
=================

In this section, we describe the baseline agent v2 :class:`~tac.agents.v2.examples.baseline.BaselineAgent`. This agent inherits from :class:`~tac.agents.v2.base.participant_agent.ParticipantAgent` and implements the :class:`~tac.agents.v2.examples.strategy.BaselineStrategy`. :class:`~tac.agents.v2.base.participant_agent.ParticipantAgent` is a TAC specific implementation of a generic :class:`~tac.agents.v2.agent.Agent`.


Main Loop and Event Loop
------------------------

A generic :class:`~tac.agents.v2.agent.Agent` can be started via :meth:`~tac.agents.v2.agent.Agent.start`. This starts the :class:`~tac.agents.v2.mail.MailBox` and a main loop implemented in :meth:`~tac.agents.v2.agent.Agent.run_main_loop`.

The mailbox is responsible for handling incoming and outgoing messages. The :class:`~tac.agents.v2.mail.InBox` enqueues incoming messages on an :attr:`~tac.agents.v2.mail.MailBox.in_queue` for later processing, the :class:`~tac.agents.v2.mail.OutBox` picks messages from the :attr:`~tac.agents.v2.mail.MailBox.out_queue` and sends them to the OEF.

The main loop deals with processing enqueued events/messages. It has the methods :meth:`~tac.agents.v2.agent.Agent.act` and :meth:`~tac.agents.v2.agent.Agent.react` which handle the active and reactive agent behaviours.


Actions and Reactions
---------------------

The v2 architecture distinguishes between `actions` and `reactions`. Actions are scheduled behaviours by the agent whereas reactions are behaviours which the agent makes in response to individual messages it receives.

We split both actions and reactions into three domains: :class:`~tac.agents.v2.base.actions.ControllerActions` and :class:`~tac.agents.v2.base.reactions.ControllerReactions`,  :class:`~tac.agents.v2.base.actions.OEFActions` and :class:`~tac.agents.v2.base.reactions.OEFReactions` and :class:`~tac.agents.v2.base.actions.DialogueActions` and :class:`~tac.agents.v2.base.reactions.DialogueReactions` related. Dialogues are agent to agent communications and maintained in :class:`~tac.agents.v2.base.dialogues.Dialogues`.


Handlers
--------

The three types of handlers :class:`~tac.agents.v2.base.handlers.ControllerHandler`, :class:`~tac.agents.v2.base.handlers.OEFHandler` and :class:`~tac.agents.v2.base.handlers.DialogueHandler` inherit from the actions and reactions of their specific type. They are resonsible for handling the implemented behaviours.


Strategy
--------

The strategy of a :class:`~tac.agents.v2.base.participant_agent.ParticipantAgent` has to implement is defined via an interface :class:`~tac.agents.v2.base.strategy.Strategy`. We also provide a sample implementation of a strategy called :class:`~tac.agents.v2.examples.strategy.BaselineStrategy` and utilised by the :class:`~tac.agents.v2.examples.baseline.BaselineAgent`.

The `advanced.py` template can be used to build a :class:`~tac.agents.v2.examples.baseline.BaselineAgent` with a custom strategy.

We have implemented a basic model of a :class:`~tac.platform.game.WorldState` which can be used and extended to enrich an agents strategy.


Agent State and World State
---------------------------

The :class:`~tac.agents.v2.base.participant_agent.ParticipantAgent` keeps track of its state via :class:`~tac.platform.game.AgentState` and it can keep track of its environment via :class:`~tac.platform.game.WorldState`.


Controller Registration
-----------------------

The :class:`~tac.agents.v2.base.participant_agent.ParticipantAgent` implements the registration with the controller via :meth:`~tac.agents.v2.base.actions.OEFActions.search_for_tac`.


Services (/Goods) Registration
------------------------------

Once the game has started, the :class:`~tac.agents.v2.base.participant_agent.ParticipantAgent` can register on the OEF's Service Directory either as a *seller*, as a *buyer* or both. To be specific, the agent can either register the goods it is willing to sell, the goods it is willing to buy or both. The registration options are available in :class:`~tac.agents.v2.base.strategy.RegisterAs`. The registration and unregistering of services is handled via the OEF action :meth:`~tac.agents.v2.base.actions.OEFActions.update_services`.


Services (/Goods) Search
------------------------

The :class:`~tac.agents.v2.base.participant_agent.ParticipantAgent` can search for the demand and supply registered by other agents on the OEF's Service Directory. The search options are available in :class:`~tac.agents.v2.base.strategy.SearchFor`. The search is handled via the OEF action :meth:`~tac.agents.v2.base.actions.OEFActions.search_services`.


Negotiation
------------

The :class:`~tac.agents.v2.base.participant_agent.ParticipantAgent` implements the FIPA negotiation protocol. A FIPA negotiation starts with a call for proposal (:class:`~oef.messages.CFP`) which contains a :class:`~oef.query.Query` referencing the services which are demanded or supplied by the sending agent. The receiving agent then responds, if it implements the FIPA negotiation protocol, with a suitable proposal (:class:`~oef.messages.Propose`) which contains a list of :class:`~oef.schema.Description` objects (think individual proposals). The first agent responds to the proposal with either a :class:`~oef.messages.Decline` or an :class:`~oef.messages.Accept`. Assuming the agent accepts, it will also send the :class:`~tac.platform.protocol.Transaction` to the :class:`~tac.platform.controller.ControllerAgent`. Finally, the second agent can close the negotiation by responding with a matching :class:`~oef.messages.Accept` and a submission of the :class:`~tac.platform.protocol.Transaction` to the :class:`~tac.platform.controller.ControllerAgent`. The controller only settles a transaction if it receives matching transactions from each one of the two trading parties referenced in the transaction.

.. mermaid:: ../_static/diagrams/fipa_negotiation_1.mmd
    :align: center
    :caption: A successful FIPA negotiation between two agents.

Trade can break down at various stages in the negotiation due to the :class:`~tac.agents.v2.base.strategy.Strategy` employed by the agents:

.. mermaid:: ../_static/diagrams/fipa_negotiation_2.mmd
    :align: center
    :caption: An unsuccessful FIPA negotiation between two agents breaking down after proposal.

.. mermaid:: ../_static/diagrams/fipa_negotiation_3.mmd
    :align: center
    :caption: An unsuccessful FIPA negotiation between two agents breaking down after cfp.
