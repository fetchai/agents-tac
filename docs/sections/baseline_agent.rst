.. _baseline_agent:

Baseline Agent v1
=================

In this section, we describe the baseline agent v1 :class:`~tac.agents.v1.examples.baseline.BaselineAgent`. This agent inherits from :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` and implements the :class:`~tac.agents.v1.examples.strategy.BaselineStrategy`. :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` is a TAC specific implementation of a generic :class:`~tac.agents.v1.agent.Agent`.


Main Loop and Event Loop
------------------------

A generic :class:`~tac.agents.v1.agent.Agent` can be started via :meth:`~tac.agents.v1.agent.Agent.start`. This starts the :class:`~tac.agents.v1.mail.MailBox` and a main loop implemented in :meth:`~tac.agents.v1.agent.Agent._run_main_loop`.

The mailbox is responsible for handling incoming and outgoing messages. The :class:`~tac.agents.v1.mail.InBox` enqueues incoming messages on an :attr:`~tac.agents.v1.mail.MailBox.in_queue` for later processing, the :class:`~tac.agents.v1.mail.OutBox` picks messages from the :attr:`~tac.agents.v1.mail.MailBox.out_queue` and sends them to the OEF.

Before the execution of the main loop, the framework will call the user's implementation of the
:meth:`~tac.agents.v1.agent.Agent.setup` method, to let the initialization of the resources needed to the agent.
Upon exit, the framework will call the user's implementation of the
:meth:`~tac.agents.v1.agent.Agent.teardown` method, to let the release of the initialized resources.

The main loop deals with processing enqueued events/messages. It has the methods :meth:`~tac.agents.v1.agent.Agent.act` and :meth:`~tac.agents.v1.agent.Agent.react` which handle the active and reactive agent behaviours.


Actions and Reactions
---------------------

The v1 architecture distinguishes between `actions` and `reactions`. Actions are scheduled behaviours by the agent whereas reactions are behaviours which the agent makes in response to individual messages it receives.

We split both actions and reactions into three domains: :class:`~tac.agents.v1.base.actions.ControllerActions` and :class:`~tac.agents.v1.base.reactions.ControllerReactions`,  :class:`~tac.agents.v1.base.actions.OEFActions` and :class:`~tac.agents.v1.base.reactions.OEFReactions` and :class:`~tac.agents.v1.base.actions.DialogueActions` and :class:`~tac.agents.v1.base.reactions.DialogueReactions`. Dialogues are agent to agent communications and maintained in :class:`~tac.agents.v1.base.dialogues.Dialogues`.


Actions
^^^^^^^

The :class:`~tac.agents.v1.base.actions.ControllerActions` class includes the methods:

- :meth:`~tac.agents.v1.base.actions.ControllerActions.request_state_update` to request the current agent state. This method is not utilised by :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent`.

The :class:`~tac.agents.v1.base.actions.OEFActions` class includes the methods:

- :meth:`~tac.agents.v1.base.actions.OEFActions.search_for_tac` to search for the active :class:`~tac.platform.controller.ControllerAgent`;
- :meth:`~tac.agents.v1.base.actions.OEFActions.update_services` to :meth:`~tac.agents.v1.base.actions.OEFActions.unregister_service` and :meth:`~tac.agents.v1.base.actions.OEFActions.register_service` on the OEF where the registration behaviour is specified via :class:`~tac.agents.v1.base.strategy.RegisterAs` in the :class:`~tac.agents.v1.base.strategy.Strategy`;
- :meth:`~tac.agents.v1.base.actions.OEFActions.search_services` to search for services on the OEF where the search behaviour is specified via :class:`~tac.agents.v1.base.strategy.SearchFor` in the :class:`~tac.agents.v1.base.strategy.Strategy`.

The :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` does not implement any methods in :class:`~tac.agents.v1.base.actions.DialogueActions`. This is because all dialogue related methods are reactions to events. In particular, the search for services (:meth:`~tac.agents.v1.base.actions.OEFActions.search_services`) initiates a chain of reactions leading to a dialogue.


Reactions
^^^^^^^^^

The :class:`~tac.agents.v1.base.reactions.ControllerReactions` class includes the methods:

- :meth:`~tac.agents.v1.base.reactions.ControllerReactions.on_start` which handles the 'start' event emitted by the controller;
- :meth:`~tac.agents.v1.base.reactions.ControllerReactions.on_transaction_confirmed` which handles the 'on transaction confirmed' event emitted by the controller;
- :meth:`~tac.agents.v1.base.reactions.ControllerReactions.on_state_update` which handles the 'on state update' event emitted by the controller;
- :meth:`~tac.agents.v1.base.reactions.ControllerReactions.on_cancelled` which handles the cancellation of the competition from the TAC controller;
- :meth:`~tac.agents.v1.base.reactions.ControllerReactions.on_tac_error` which handles the 'on tac error' event emitted by the controller;
- :meth:`~tac.agents.v1.base.reactions.ControllerReactions.on_dialogue_error` which handles the 'dialogue error' event emitted by the controller.

The :class:`~tac.agents.v1.base.reactions.OEFReactions` class includes the methods:

- :meth:`~tac.agents.v1.base.reactions.OEFReactions.on_search_result` which handles the OEF search results;
- :meth:`~tac.agents.v1.base.reactions.OEFReactions.on_oef_error` which handles the OEF error message;
- :meth:`~tac.agents.v1.base.reactions.OEFReactions.on_dialogue_error` which handles the dialogue error message.

The :class:`~tac.agents.v1.base.reactions.DialogueReactions` class includes the methods:

- :meth:`~tac.agents.v1.base.reactions.DialogueReactions.on_new_dialogue` which handles reaction to a new dialogue;
- :meth:`~tac.agents.v1.base.reactions.DialogueReactions.on_existing_dialogue` which handles reaction to an existing dialogue;
- :meth:`~tac.agents.v1.base.reactions.DialogueReactions.on_unidentified_dialogue` which handles reaction to an unidentified dialogue.

The message level handling of a negotiation dialogue is performed in :class:`~tac.agents.v1.base.negotiation_behaviours.FIPABehaviour`.


Handlers
--------

The three types of handlers :class:`~tac.agents.v1.base.handlers.ControllerHandler`, :class:`~tac.agents.v1.base.handlers.OEFHandler` and :class:`~tac.agents.v1.base.handlers.DialogueHandler` inherit from the actions and reactions of their specific type. They are resonsible for handling the implemented behaviours.


Strategy
--------

The strategy of a :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` has to implement is defined via an interface :class:`~tac.agents.v1.base.strategy.Strategy`. We also provide a sample implementation of a strategy called :class:`~tac.agents.v1.examples.strategy.BaselineStrategy` and utilised by the :class:`~tac.agents.v1.examples.baseline.BaselineAgent`.

The `advanced.py` template can be used to build a :class:`~tac.agents.v1.examples.baseline.BaselineAgent` with a custom strategy.

We have implemented a basic model of a :class:`~tac.platform.game.WorldState` which can be used and extended to enrich an agents strategy.


Agent State and World State
---------------------------

The :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` keeps track of its state via :class:`~tac.platform.game.AgentState` and it can keep track of its environment via :class:`~tac.platform.game.WorldState`.


Controller Registration
-----------------------

The :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` initiates the registration with the controller via :meth:`~tac.agents.v1.base.actions.OEFActions.search_for_tac`.


Services (/Goods) Registration
------------------------------

Once the game has started, the :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` can register on the OEF's Service Directory either as a *seller*, as a *buyer* or both. To be specific, the agent can either register the goods it is willing to sell, the goods it is willing to buy or both. The registration options are available in :class:`~tac.agents.v1.base.strategy.RegisterAs`. The registration and unregistering of services is handled via the OEF action :meth:`~tac.agents.v1.base.actions.OEFActions.update_services`.


Services (/Goods) Search
------------------------

The :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` can search for the demand and supply registered by other agents on the OEF's Service Directory. The search options are available in :class:`~tac.agents.v1.base.strategy.SearchFor`. The search is handled via the OEF action :meth:`~tac.agents.v1.base.actions.OEFActions.search_services`.


Negotiation
------------

The :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` implements the FIPA negotiation protocol in :class:`~tac.agents.v1.base.negotiation_behaviours.FIPABehaviour`. A FIPA negotiation starts with a call for proposal (:class:`~oef.messages.CFP`) which contains a :class:`~oef.query.Query` referencing the services which are demanded or supplied by the sending agent. The receiving agent then responds, if it implements the FIPA negotiation protocol, with a suitable proposal (:class:`~oef.messages.Propose`) which contains a list of :class:`~oef.schema.Description` objects (think individual proposals). The first agent responds to the proposal with either a :class:`~oef.messages.Decline` or an :class:`~oef.messages.Accept`. Assuming the agent accepts, it will also send the :class:`~tac.platform.protocol.Transaction` to the :class:`~tac.platform.controller.ControllerAgent`. Finally, the second agent can close the negotiation by responding with a matching :class:`~oef.messages.Accept` and a submission of the :class:`~tac.platform.protocol.Transaction` to the :class:`~tac.platform.controller.ControllerAgent`. The controller only settles a transaction if it receives matching transactions from each one of the two trading parties referenced in the transaction.

.. mermaid:: ../diagrams/fipa_negotiation_1.mmd
    :align: center
    :caption: A successful FIPA negotiation between two agents.

Trade can break down at various stages in the negotiation due to the :class:`~tac.agents.v1.base.strategy.Strategy` employed by the agents:

.. mermaid:: ../diagrams/fipa_negotiation_2.mmd
    :align: center
    :caption: An unsuccessful FIPA negotiation between two agents breaking down after initial accept.

.. mermaid:: ../diagrams/fipa_negotiation_3.mmd
    :align: center
    :caption: An unsuccessful FIPA negotiation between two agents breaking down after proposal.

.. mermaid:: ../diagrams/fipa_negotiation_4.mmd
    :align: center
    :caption: An unsuccessful FIPA negotiation between two agents breaking down after cfp.


Agent Speed
-----------

There are two parameters of the :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` which affect the agent speed directly. First, the `agent_timeout` parameter specifies the duration in (fractions of) seconds for which the :class:`~tac.agents.v1.agent.Agent` times out between :meth:`~tac.agents.v1.agent.Agent.act` and :meth:`~tac.agents.v1.agent.Agent.react`. Lowering this parameter increases the speed at which the agent loop spins. Second, the `services_interval` parameter specifies the length of the interval at which the agent updates its services on the OEF and searches for services on the OEF. Lowering this parameter leads to more frequent updates and searches and therefore higher number of negotiations initiated by the agent.

There is a further parameter of the :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` which affects the agent speed indirectly: the `max_reactions` parameter sets an upper bound on the number of messages which are processed by the :class:`~tac.agents.v1.base.participant_agent.ParticipantAgent` during each call to :meth:`~tac.agents.v1.agent.Agent.react`. Lowering this number slows down the reactive behaviour of the agent relative to the active behaviour of the agent.

