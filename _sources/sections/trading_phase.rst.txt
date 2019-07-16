.. _trading_phase:

Trading Phase
==================

After the :ref:`registration_phase` there is the *trading phase*, where the actual competition takes place.

At this point, every participant should have received from the controller agent the data of the game.

In the following sections, we will see how an agent can play the game and improve its score. In particular:

1. what is the initial state of an agent.
2. what is a *transaction*;
3. how a transaction can be submitted to the controller agent;
4. how to negotiate with other trading agents.


Game data
----------

As we said, every agent that registered to the competition will eventually receive their endowment
in order to devise a strategy and to start playing.

More precisely, the :class:`~tac.platform.protocol.GameData` contains the following information:

- ``money`` (integer): the money amount available to the TAC agent.
- ``endowment`` (list of integers): the endowment for every good.
- ``utility_params`` (list of floats): the utility parameters for every good.
- ``nb_agents`` (integer): the number of agents in the competition.
- ``nb_goods`` (integer): the number of goods in the competition.
- ``tx_fee`` (float): the transaction fee for every trade.
- ``agent_pbk_to_name`` (dictionary[string, string]): mapping the public key of each agent to its name.
- ``good_pbk_to_name`` (dictionary[string, string]): mapping the public key of each good to its name.

.. note::

    An agent is not aware of:
        - the endowment of any other participant
        - the utility_params of any other participant


Example
^^^^^^^

**Example**: Let ``agent_1`` and ``agent_2`` be participants of a TAC game.
Assume that there are two types of good: ``good_1`` and ``good_2``.

This table describes the holdings of the agents. That is, how many
instances of goods the agents hold:

+---------+--------+--------+
|         | good_1 | good_2 |
+---------+--------+--------+
| agent_1 | 1      | 2      |
+---------+--------+--------+
| agent_2 | 4      | 1      |
+---------+--------+--------+


This table shows the utility parameters for every good, for every agent.

+---------+--------+--------+
|         | good_1 | good_2 |
+---------+--------+--------+
| agent_1 | 80.0   | 20.0   |
+---------+--------+--------+
| agent_2 | 30.0   | 70.0   |
+---------+--------+--------+


And this table shows the balance of every agent, that is, how much money they have.

+---------+-------+
|         | money |
+---------+-------+
| agent_1 | 200   |
+---------+-------+
| agent_2 | 100   |
+---------+-------+

The scores for an agent can be computed in this way:

.. math:: M + \sum_i u_i * f(q_i)

Where :math:`M` is the money amount left, :math:`u_i` is the utility parameter for good :math:`i`, and :math:`q_i` is
the quantity of good :math:`i`, and if :math:`q_i > 0`

.. math:: f(q_i) = ln(q_i)

else

.. math:: f(q_i) = - 1000

In the example:

- ``agent_1`` score: :math:`200 + (80.0 \cdot f(1) + 20.0 \cdot f(2)) = 213.86`
- ``agent_2`` score: :math:`100 + (30.0 \cdot f(4) + 70.0 \cdot f(1)) = 141.59`


TAC Transaction
----------------

A transaction in the TAC competition is an exchange of good instances and money between a buyer and a seller agent.

The message that represents a transaction request to the controller agent
is :class:`~tac.platform.protocol.Transaction`. It contains these fields:

- ``transaction_id`` (string): a string that uniquely identifies a transaction.
- ``buyer`` (bool): whether the sender of the transaction request is the buyer of the transaction.
  in other words, ``True`` if the sender agent, in this transaction, takes the role of a buyer; ``False`` otherwise
  (it is the seller).
- ``counterparty`` (string): the public key of the counterparty agent in the transaction.
- ``amount`` (integer): the amount of money involved in the transaction (i.e. the price).
- ``quantities_by_good_pbk``: a map from good public keys to the number of instances traded.
  If a good public key is not contained in the set of all good public keys, we assume that the quantity involved in the transaction is 0.


Transaction example
^^^^^^^^^^^^^^^^^^^

Borrowing the example in the previous section, a transaction in that scenario might be:

- ``agent_1`` is the buyer, whereas the ``agent_2`` is the seller
- the ``quantities_by_good_pbk`` field contains the following map:
    * ``good_1`` -> ``1``
    * ``good_2`` -> ``0``

  that is, the buyer is interested in only ``1`` quantity of the good with public key ``good_1``.
- the amount is ``10``.


Submit a transaction
---------------------

In order to submit a transaction, both parties must submit a transaction request to the controller agent, using the
:class:`~tac.platform.protocol.Transaction` message.

Once the controller receives two matching and valid transaction requests from both parties,
the transaction is *settled*, which implies:

- The controller agent updates the good holdings and money balances of both the buyer agent and the seller agent.
- The controller sends a :class:`~tac.platform.protocol.TransactionConfirmation` message to the buyer and the seller.


Invalid transaction
^^^^^^^^^^^^^^^^^^^

A transaction is *valid* if:
 - the buyer has enough balance to pay the transaction amount, and
 - the seller has at least the good quantities to sell declared in the transaction.


As soon as the controller agents receives an invalid transaction request, he will reply with
a :class:`~tac.platform.protocol.Error` containing a message


Negotiation with other agents
------------------------------

One of the OEF features is the support for (a subset of) the FIPA protocol, that is well-suited for
handling negotiations.

Hence, the trading agents can negotiate with each other by using the
`FIPA Protocol <https://fetchai.github.io/oef-sdk-python/user/communication-protocols.html#using-fipa-for-negotiation>`_.
API exposed by the SDK.


Handle unexpected disconnection
--------------------------------

A trading agent can request from the controller agent her current state in the game with the :class:`~tac.platform.protocol.GetStateUpdate` message.
