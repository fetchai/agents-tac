.. _trading_phase:

Trading Phase
==================

After the :ref:`registration_phase` there is the *trading phase*, where the actual competition takes place.

At this point, every participant should have received from the controller agent the data of the game.

In the following sections, we will see how an agent can play the game and improve his score. In particular:

1. what is the initial state of an agent.
2. what is a *transaction*;
3. how a transaction can be submitted to the controller agent;
4. how to negotiate with other trading agents.

Game data
----------

As we said, every agent that registered to the competition will eventually receive their endowment
in order to devise a strategy and to start playing.

More precisely, the :class:`~tac.protocol.GameData` contains the following information:

- money (integer): the money amount available to the TAC agent.
- endowment (list of integers): the endowment for every good.
- preferences (list of integers): the utility values for every good.
- fee (integer): the transaction fee for every trade.

.. note::

    An agent is not aware of, among other things:
        - how many agents are competing
        - the game endowment of any other participant
        - the utilities of any other participant

Example
^^^^^^^

**Example**: Let ``agent_1`` and ``agent_2`` be participants of a TAC game.
Assume that there are two types of good: ``good_1`` and ``good_2``.

This table describes the holdings of the agents. That is, how many
instances of goods the agents hold:

+---------+--------+--------+
|         | good_1 | good_2 |
+---------+--------+--------+
| agent_1 | 2      | 1      |
+---------+--------+--------+
| agent_2 | 0      | 1      |
+---------+--------+--------+


This other table describes the utility values for every good, for every agent.

+---------+--------+--------+
|         | good_1 | good_2 |
+---------+--------+--------+
| agent_1 | 20     | 10     |
+---------+--------+--------+
| agent_2 | 10     | 20     |
+---------+--------+--------+


And this table shows the balance of every agent, that is, how many money they have left.

+---------+-------+
|         | money |
+---------+-------+
| agent_1 | 0     |
+---------+-------+
| agent_2 | 20    |
+---------+-------+

The scores for an agent can be computed in this way:

.. math:: M + \sum_i u_i * h_i

Where :math:`M` is the money amount left, :math:`u_i` is the utility value for good :math:`i`, and :math:`h_i` is
``1`` if the quantity of good is non-zero, ``0`` otherwise (in other word, we ignore duplicates of good instances).

In the example:

- ``agent_1`` score: :math:`0 + (20 \cdot 1 + 10 \cdot 1) = 30`
- ``agent_2`` score: :math:`20 + (10 \cdot 0 + 20 \cdot 1) = 30`

TAC Transaction
----------------

A transaction in the TAC competition is an exchange of good instances and money between a buyer and a seller agent.

The message that represents a transaction request to the controller agent
is :class:`~tac.protocol.Transaction`. It contains these fields:

- ``transaction_id`` (string): a string that uniquely identifies a transaction.
- ``buyer`` (bool): whether the sender of the transaction request is the buyer of the transaction.
  in other words, ``True`` if the sender agent, in this transaction, takes the role of a buyer; ``False`` otherwise
  (he is the seller).
- ``counterparty`` (string): the identifier of the counterparty agent in the transaction.
- ``amount`` (integer): the amount of money involved in the transaction.
- ``quantities_by_good_id``: a map from good identifiers to the number of instances traded.
  If a good id is not contained in the set of keys, we assume that the quantity involved in the transaction is 0.


Transaction example
^^^^^^^^^^^^^^^^^^^

Borrowing the example in the previous section, a transaction in that scenario might be:

- ``agent_2`` is the buyer, whereas the ``agent_1`` is the seller
- the ``quantities_by_good_id`` field contains the following map:
    * ``0`` -> ``1``
    * ``1`` -> ``0``
  that is, the buyer is interested in only ``1`` quantity of the good of index ``0``: ``good_1``.
- the amount is ``10``.


Submit a transaction
---------------------

In order to submit a transaction, both parties must submit a transaction request to the controller agent, using the
:class:`~tac.protocol.Transaction` message.


.. todo::

    TODO for now only one must submit, but obviously has to be changed.

Once the controller receives two matching and valid transaction requests from both parties,
the transaction is *settled*, which implies:

- The controller agent updates the holdings and balances of both the buyer agent and the seller agent.
- The controller sends a :class:`~tac.protocol.TransactionConfirmation` message to the buyer and the seller.


.. uml:: ../_static/diagrams/

Invalid transaction
^^^^^^^^^^^^^^^^^^^

A transaction is *valid* if:
 - the buyer has enough balance to pay the transaction amount, and
 - the seller has at least the good quantities to sell declared in the transaction.


As soon as the controller agents receives an invalid transaction request, he will reply with
a :class:`~tac.protocol.Error` containing a message

.. todo::

    should we have a reserved message for every kind of error? E.g. ``GenericError``, ``TransactionError``, etc.


Negotiation with other agents
------------------------------

One of the OEF features is the support for (a subset of) the FIPA protocol, that is well-suited for
handling negotiations.

Hence, the trading agents can negotiate with each other by using the
`FIPA Protocol <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#using-fipa-for-negotiation>`_.
API exposed by the SDK.


Handle unexpected disconnection
--------------------------------

.. todo::

    TODO: if the agent didn't store the data, he should be able to ask for them explicitly.
    -> reserve a message to ask for details for the current status in the game (holdings, balance, preferences etc.),
    e.g. ``GetInfo{}``.


