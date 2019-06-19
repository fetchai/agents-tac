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
which is an integer value. The TAC controller agent will register with ``"version"=1``.

The controller agent will wait for *registration_timeout*. At the end, if there are enough
participant, it will start the competition. Otherwise, it will send back a "Cancelled" message to every
registered participant

.. uml:: ../_static/diagrams/controller_setup.uml
    :align: center
    :caption: The setup of the controller agent.

How to register/unregister
--------------------------

In order to complete a registration, a trading agent should do the following steps:

1. Run a search for ``"tac"`` services, with the query ``"version" == 1``.
2. On the search result, send a :class:`~tac.platform.protocol.Register` message to the right TAC controller
3. Waiting for the :class:`~tac.platform.protocol.GameData` message.


.. note::

    All the communications toward the controller agent must be done
    by using the `send_message <https://fetchai.github.io/oef-sdk-python/oef.html#oef.agents.Agent.send_message>`_,
    that is, to send the general-purpose message in the OEF. In the following, we will see what kind of content the
    message should have in order to be understandable by the controller agent.

    E.g. for sending a :class:`~tac.platform.protocol.Register` message, you should first serialize the object by using
    :func:`~tac.platform.protocol.Message.serialize`, and then send the byte-encoded message in a simple message.


Search for controller agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. uml:: ../_static/diagrams/search_controller.uml
    :align: center
    :caption: TAC Agent search for controller agents.

Register to TAC
^^^^^^^^^^^^^^^^

In order to register, a TAC Agent must send a :class:`~tac.platform.protocol.Register` message to the controller agent.

The message :class:`~tac.platform.protocol.Register` is an empty message. In order to undo the effect of
the registration, the agent can unregister from the competition by sending the :class:`~tac.platform.protocol.Unregister`
message.


.. uml:: ../_static/diagrams/register_to_tac.uml
    :align: center
    :caption: an agent registers to TAC.



Start of the competition
------------------------

Once trading agents receive the :class:`~tac.platform.protocol.GameData` message, the competition starts
and the *trading phase* begins.

The message :class:`~tac.platform.protocol.GameData` contains the following information:

- money (integer): the money amount available to the TAC agent.
- endowment (list of integers): the endowment for every good.
- utility_params (list of floats): the utility parameters for every good.
- nb_agents (integer): the number of agents in the competition.
- nb_goods (integer): the number of goods in the competition.
- tx_fee (float): the transaction fee for every trade.
- agent_pbks (list of strings): the public key of each agent.
- agent_names (list of strings): the name of each agent.
- good_pbks (list of strings): the public key of each good.

Summary
--------

In the following, a transition diagram that sumarize the *registration phase*:


.. uml:: ../_static/diagrams/registration.uml
   :align: center
   :caption: The transition diagram for the registration phase.
