.. _registration_phase:

Registration Phase
==================

In this section, we describe the *registration phase*,
during which the participant can register their own agent
for the competition.

To do so, the participant must register with the *controller agent*
that will be running and be connected to the OEF throughout the duration
of the competition.

At the end of the registration time, the controller
generates the game data for every participant (that is, the initial
good holdings and the utility parameters for the goods).
Then, the agent can start to negotiate and
to submit transactions to the controller agent.

In the following sections, we will explain:

* the initial setup of the controller agent;
* how to register/unregister to TAC;
* how the trading phase will start;
* how to handle errors (e.g. potential disconnection from the network)


Setup of the controller agent
------------------------------

Before the registration phase starts, the organizer
of the TAC will run the *controller agent*, which is
a special agent that manages the TAC. Specifically, the main tasks are:

1. Handling of registration/unregistration of the participants.
2. Generating the game data for each agent and triggering the start of the competition.
3. Accepting/Rejecting valid/invalid transactions submitted by the trading agents.
4. Providing agents with state updates (e.g. when the agent reconnects after a disconnection)


Register as 'tac' service
---------------------------

The controller agent registers itself to the OEF as a service.

The data model name is ``"tac"`` and as attribute we have ``"version"``,
which is an integer value. The TAC controller agent will register with ``"version"=VERSION_ID``.

The controller agent will wait for *registration_timeout*. At the end, if there are enough
participant, it will start the competition. Otherwise, it will send back a "Cancelled" message to every
registered participant

.. mermaid:: ../diagrams/controller_setup.mmd
    :align: center
    :caption: The setup of the controller agent.


How to register/unregister
--------------------------

In order to complete a registration, a trading agent should do the following steps:

1. Run a search for ``"tac"`` services, with the query ``"version" == VERSION_ID``.
2. On the search result, send a `Register` message to the right TAC controller
3. Waiting for the :class:`~tac.platform.game.base.GameData` message.


Search for controller agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. mermaid:: ../diagrams/search_controller.mmd
    :align: center
    :caption: TAC Agent search for controller agents.


Register to TAC
^^^^^^^^^^^^^^^^

In order to register, a TAC Agent must send a `Register` message to the controller agent.

The message `Register` is an empty message. In order to undo the effect of
the registration, the agent can unregister from the competition by sending the `Unregister`
message.

.. mermaid:: ../diagrams/register_to_tac.mmd
    :align: center
    :caption: an agent registers to TAC.


Start of the competition
------------------------

Once trading agents receive the :class:`~tac.platform.game.base.GameData` message, the competition starts
and the *trading phase* begins.

The message :class:`~tac.platform.game.base.GameData` contains the following information:

- ``money`` (integer): the money amount available to the TAC agent.
- ``endowment`` (list of integers): the endowment for every good.
- ``utility_params`` (list of floats): the utility parameters for every good.
- ``nb_agents`` (integer): the number of agents in the competition.
- ``nb_goods`` (integer): the number of goods in the competition.
- ``tx_fee`` (float): the transaction fee for every trade.
- ``agent_pbk_to_name`` (dictionary[string, string]): mapping the public key of each agent to its name.
- ``good_pbk_to_name`` (dictionary[string, string]): mapping the public key of each good to its name.


Summary
--------

In the following, a transition diagram that sumarize the *registration phase*:

.. mermaid:: ../diagrams/registration.mmd
   :align: center
   :caption: The transition diagram for the registration phase.
