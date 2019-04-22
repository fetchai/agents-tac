.. _registration_phase:

Registration Phase
==================

In this section, we describe the *registration phase*,
where the participant can register their own agent
for the competition.

To do so, the participant must contact the *controller agent*
that will be running on the OEF throughout the duration
of the competition.

In the following sections, we will explain:

* the initial setup of the controller agent;
* how to register/unregister to TAC;
* how the actual competition will start;
* how to handle error (e.g. potential disconnection to the network)

Setup of the controller agent
------------------------------

Before the registration phase starts, the organizer
of TAC will run the *controller agent*, which is
nothing else than another OEF Agent.

The *controller agent* is a special OEF Agent that
manages the TAC. Specifically, the main tasks are:

1. Handling of registration/unregistration of the participants.
2. Triggering of the start of the competition.
3. Accepting/Rejecting valid/invalid transactions submitted by the TAC Agents.

Register as 'tac' service
---------------------------

The controller agent registers himself to the OEF
as a service.

.. todo:

    revise this part.
    an alternative (to avoid search and then registration) could be:
        - the participant registers on a website with a "public key"
        - he receives an email with  the public key of the controller agent
        - during registration phase,
          the controller accepts registrations only from agents with
          the preregistered public key.
    in other words, the trading agents already know in advance what's
    the public key of the controller.

The data model name is ``"tac"`` and as attribute we have ``"version"``,
which is an integer value. The TAC controller agent will register with ``"version"=1``.

The controller agent will wait for *registration time*. At the end, if there are enough
participant, it will start the competition. Otherwise, it will send back a "Cancelled" message to every
registered participant

.. uml:: ../_static/diagrams/controller_setup.uml
    :align: center
    :caption: The setup of the controller agent.

How to register/unregister
--------------------------

In order to complete a registration, a trading agent should do the following steps:

1. Run a search for ``"tac"`` services, with the query ``"version" == 1``.
2. On the search result, send a :class:`~tac.protocol.Register` message to the right TAC controller
3. Waiting for the :class:`~tac.protocol.GameData` message.


.. note::

    All the communications toward the controller agent must be done
    by using the `send_message <https://fetchai.github.io/oef-sdk-python/oef.html#oef.agents.Agent.send_message>`_,
    that is, to send the general-purpose message in the OEF. In the following, we will see what kind of content the
    message should have in order to be understandable by the controller agent.

    E.g. for sending a :class:`~tac.protocol.Register` message, you should first serialize the object by using
    :func:`~tac.protocol.Message.serialize`, and then send the byte-encoded message in a simple message.


Search for controller agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. uml:: ../_static/diagrams/search_controller.uml
    :align: center
    :caption: TAC Agent search for controller agents.

Register to TAC
^^^^^^^^^^^^^^^^

In order to register, a TAC Agent must send a :class:`~tac.protocol.Register` message to the controller agent.

The message :class:`~tac.protocol.Register` is an empty message. In order to undo the effect of
the registration, the agent can unregister from the competition by sending the :class:`~tac.protocol.Unregister`
message.


.. uml:: ../_static/diagrams/search_controller.uml
    :align: center
    :caption: an agent registers to TAC.



Start of the competition
^^^^^^^^^^^^^^^^^^^^^^^^

The message :class:`~tac.protocol.GameData` contains the following information:

- money (integer): the money amount available to the TAC agent.
- endowment (list of integers): the endowment for every good.
- preferences (list of integers): the utility values for every good.
- fee (integer): the transaction fee for every trade.

Once trading agents receive the :class:`~tac.protocol.GameData` message, the competition starts
and the *trading phase* begins.


Handle Errors
-------------

Handle unexpected disconnection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TODO: if the agent didn't store the data, he should be able to ask for them explicitly.
-> reserve a message to ask for details for the current status in the game (holdings, balance, preferences etc.),
e.g. ``GetInfo{}``.

.. todo

    if the agent didn't store the data, he should be able to ask for them explicitly.


Handle OEF Errors/Dialogue Errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For the OEF related errors, please look at
`this link <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#error-handling>`_.

Summary
--------

In the following, a transition diagram that sumarize the *registration phase*:


.. uml:: ../_static/diagrams/registration.uml
   :align: center
   :caption: The transition diagram for the registration phase.
