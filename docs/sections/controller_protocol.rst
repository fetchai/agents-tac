.. _controller_protocol:

Protocol for the Controller - TAC protocol
==========================================

In this section we describe the protocol to use in order to interact with the controller agent - the TAC protocol.


Introduction
------------

The messages are sent over the OEF
`Message <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#using-general-purpose-messages>`_,
which is a general purpose message relay.

We use the :class:`~tac.platform.protocols.tac.message.TACMessage` for two categories of messages:


Messages from a TAC Agent to the Controller Agent:
--------------------------------------------------

- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.REGISTER`
- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.UNREGISTER`
- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.TRANSACTION`
- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.GET_STATE_UPDATE`


Messages from the Controller Agent to a TAC Agent:
--------------------------------------------------

- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.CANCELLED`
- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.TAC_ERROR`
- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.GAME_DATA`
- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.TRANSACTION_CONFIRMATION`
- :class:`~tac.platform.protocols.tac.message.TACMessage.Type.STATE_UPDATE`


Error handling
---------------

Errors and exception to the normal flow of execution may happen for many reasons. Here we list some and describe
how to catch them.


Handle Controller error
^^^^^^^^^^^^^^^^^^^^^^^^

The controller agent will use the :class:`~tac.platform.protocols.tac.message.TACMessage` of type :class:`~tac.platform.protocols.tac.message.TACMessage.Type.TAC_ERROR` to notify the participants about
an unexpected state of the request.

An ``Error`` message includes an ``error_msg`` string field that is supposed to contain details about the error.


Handle OEF Errors/Dialogue Errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For the OEF related errors, please look at
`this link <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#error-handling>`_.
