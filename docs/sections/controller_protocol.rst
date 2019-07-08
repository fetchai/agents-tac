.. _controller_protocol:

Protocol for the Controller
============================

In this section we describe the protocol to use in order to interact with the controller agent.


Introduction
------------

The messages are sent over the OEF
`Message <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#using-general-purpose-messages>`_,
which is a general purpose message relay.

It's up to the developer to set the ``msg_id`` and ``dialogue_id`` fields in the :meth:`~oef.agents.Agent.send_message`
call. The controller agent will answer with the same ``dialogue_id`` (but a different ``msg_id``) and a target which references the ``msg_id`` of the agent's message.

The type of messages in this protocol can be divided in two categories:

- :class:`~tac.platform.protocol.Request`, from a TAC Agent to the Controller Agent;
- :class:`~tac.platform.protocol.Response`, from the Controller Agent to a TAC Agent.


Requests
--------

- :class:`~tac.platform.protocol.Register`
- :class:`~tac.platform.protocol.Unregister`
- :class:`~tac.platform.protocol.Transaction`
- :class:`~tac.platform.protocol.GetStateUpdate`


Responses
---------

- :class:`~tac.platform.protocol.Cancelled`
- :class:`~tac.platform.protocol.Error`
- :class:`~tac.platform.protocol.GameData`
- :class:`~tac.platform.protocol.TransactionConfirmation`
- :class:`~tac.platform.protocol.StateUpdate`


Error handling
---------------

Errors and exception to the normal flow of execution may happen for many reasons. Here we list some and describe
how to catch them.


Handle Controller error
^^^^^^^^^^^^^^^^^^^^^^^^

The controller agent will use the :class:`~tac.platform.protocol.Error` message to notify the participants about
an unexpected state of the request.

An ``Error`` message includes an ``error_msg`` string field that is supposed to contain details about the error.


Handle OEF Errors/Dialogue Errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For the OEF related errors, please look at
`this link <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#error-handling>`_.
