.. _controller_protocol:

Protocol for the Controller
============================

In this section we describe the protocol to use in order to interact with the controller agent.

Introduction
------------

The messages are sent over the OEF
`Message <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#using-general-purpose-messages>`_,
which is a general purpose message.

It's up to the developer to set the ``msg_id`` and ``dialogue_id`` fields in the :func:`~oef.agents.Agent.send_message`
call. The controller agent will answer with the same ``dialogue_id`` (but a different ``msg_id``).

.. todo::

    The fields ``msg_id`` and ``dialogue_id`` should be set automatically by the ``tac`` package?

    That is, could we provide an ad-hoc framework which will hide these parameters?


The type of messages in this protocol can be divided in two categories:

- :class:`~tac.protocol.Request`, from a TAC Agent to the Controller Agent;
- :class:`~tac.protocol.Response`, from the Controller Agent to a TAC Agent.

Requests
--------

- :class:`~tac.protocol.Register`
- :class:`~tac.protocol.Unregister`
- :class:`~tac.protocol.Transaction`

Responses
---------


- :class:`~tac.protocol.GameData`
- :class:`~tac.protocol.TransactionConfirmation`
- :class:`~tac.protocol.Error`

Error handling
---------------

Errors and exception to the normal flow of execution may happen for many factors. Here we list some and describe
how to catch them.

Handle Controller error
^^^^^^^^^^^^^^^^^^^^^^^^

The controller agent will use the :class:`~tac.protocol.Error` message to notify the participants about
an unexpected state of the request.

An ``Error`` message includes an ``error_msg`` string field that is supposed to contain details about the error.


Handle OEF Errors/Dialogue Errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For the OEF related errors, please look at
`this link <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#error-handling>`_.


