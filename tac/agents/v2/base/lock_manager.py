# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This module contains a class to manage locked agent states."""

import datetime
import logging
import time
from collections import defaultdict, deque
from threading import Thread
from typing import Dict, Tuple, Deque, List

from oef.schema import Description

from tac.agents.v2.base.dialogues import DialogueLabel, Dialogue
from tac.helpers.crypto import Crypto
from tac.agents.v2.base.helpers import generate_transaction_id
from tac.platform.protocol import Transaction

logger = logging.getLogger(__name__)

MESSAGE_ID = int
TRANSACTION_ID = str


class LockManager(object):
    """Class to handle pending proposals/acceptances and locks."""

    def __init__(self, agent_name: str, pending_transaction_timeout: int = 30, task_timeout: float = 2.0) -> None:
        """
        Initialize a LockManager.

        :param agent_name: The name of the agent the manager refers to.
        :param pending_transaction_timeout: seconds to wait before a transaction/message can be removed from any pool.
        :param task_timeout: seconds to sleep for the task

        :return: None
        """
        self.agent_name = agent_name

        self.pending_tx_proposals = defaultdict(lambda: {})  # type: Dict[DialogueLabel, Dict[MESSAGE_ID, Transaction]]
        self.pending_tx_acceptances = defaultdict(lambda: {})  # type: Dict[DialogueLabel, Dict[MESSAGE_ID, Transaction]]

        self.locks = {}  # type: Dict[TRANSACTION_ID, Transaction]
        self.locks_as_buyer = {}  # type: Dict[TRANSACTION_ID, Transaction]
        self.locks_as_seller = {}  # type: Dict[TRANSACTION_ID, Transaction]

        self.pending_transaction_timeout = pending_transaction_timeout
        self._cleanup_locks_task = None
        self._cleanup_locks_task_is_running = False
        self._cleanup_locks_task_timeout = task_timeout

        self._last_update_for_pending_messages = deque()  # type: Deque[Tuple[datetime.datetime, Tuple[DialogueLabel, MESSAGE_ID]]]
        self._last_update_for_transactions = deque()  # type: Deque[Tuple[datetime.datetime, TRANSACTION_ID]]

    def cleanup_locks_job(self) -> None:
        """
        Periodically check for transactions in one of the pending pools.

        If they have been there for too much time, remove them.

        :return: None
        """
        while self._cleanup_locks_task_is_running:
            time.sleep(self._cleanup_locks_task_timeout)
            self._cleanup_pending_messages()
            self._cleanup_pending_transactions()

    def _cleanup_pending_messages(self) -> None:
        """
        Remove all the pending messages (i.e. either proposals or acceptances) that have been stored for an amount of time longer than the timeout.

        :return: None
        """
        timeout = datetime.timedelta(0, self.pending_transaction_timeout)
        queue = self._last_update_for_pending_messages

        if len(queue) == 0:
            return

        next_date, next_item = self._last_update_for_pending_messages[0]

        while datetime.datetime.now() - next_date > timeout:
            # remove the element from the queue
            queue.popleft()

            # extract dialogue label and message id
            dialogue_label, message_id = next_item
            logger.debug("[{}]: Removing message {}, {}".format(self.agent_name, dialogue_label, message_id))

            # remove (safely) the associated pending proposal (if present)
            self.pending_tx_proposals.get(dialogue_label, {}).pop(message_id, None)
            self.pending_tx_proposals.pop(dialogue_label, None)

            # remove (safely) the associated pending acceptance (if present)
            self.pending_tx_acceptances.get(dialogue_label, {}).pop(message_id, None)
            self.pending_tx_acceptances.pop(dialogue_label, None)

            # check the next pending message, if present
            if len(queue) == 0:
                break
            next_date, next_item = queue[0]

    def _cleanup_pending_transactions(self) -> None:
        """
        Remove all the pending messages (i.e. either proposals or acceptances) that have been stored for an amount of time longer than the timeout.

        :return: None
        """
        queue = self._last_update_for_transactions
        timeout = datetime.timedelta(0, self.pending_transaction_timeout)

        if len(queue) == 0:
            return

        next_date, next_item = queue[0]

        while datetime.datetime.now() - next_date > timeout:

            # remove the element from the queue
            queue.popleft()

            # extract dialogue label and message id
            transaction_id = next_item
            logger.debug("[{}]: Removing transaction: {}".format(self.agent_name, transaction_id))

            # remove (safely) the associated pending proposal (if present)
            self.locks.pop(transaction_id, None)
            self.locks_as_buyer.pop(transaction_id, None)
            self.locks_as_seller.pop(transaction_id, None)

            # check the next transaction, if present
            if len(queue) == 0:
                break
            next_date, next_item = queue[0]

    def _register_transaction_with_time(self, transaction_id: str) -> None:
        """
        Register a transaction with a creation datetime.

        :param transaction_id: the transaction id

        :return: None
        """
        now = datetime.datetime.now()
        self._last_update_for_transactions.append((now, transaction_id))

    def _register_message_with_time(self, dialogue: Dialogue, msg_id: int) -> None:
        """
        Register a message with a creation datetime.

        :param dialogue: the dialogue
        :param msg_id: the message id

        :return: None
        """
        now = datetime.datetime.now()
        message_id = (dialogue.dialogue_label, msg_id)
        self._last_update_for_pending_messages.append((now, message_id))

    def add_pending_proposal(self, dialogue: Dialogue, proposal_id: int, transaction: Transaction) -> None:
        """
        Add a proposal (in the form of a transaction) to the pending list.

        :param dialogue: the dialogue associated with the proposal
        :param proposal_id: the message id of the proposal
        :param transaction: the transaction
        :raise AssertionError: if the pending proposal is already present.

        :return: None
        """
        assert dialogue.dialogue_label not in self.pending_tx_proposals and proposal_id not in self.pending_tx_proposals[dialogue.dialogue_label]
        self.pending_tx_proposals[dialogue.dialogue_label][proposal_id] = transaction
        self._register_message_with_time(dialogue, proposal_id)

    def pop_pending_proposal(self, dialogue: Dialogue, proposal_id: int) -> Transaction:
        """
        Remove a proposal (in the form of a transaction) from the pending list.

        :param dialogue: the dialogue associated with the proposal
        :param proposal_id: the message id of the proposal
        :raise AssertionError: if the pending proposal is not present.

        :return: the transaction
        """
        assert dialogue.dialogue_label in self.pending_tx_proposals and proposal_id in self.pending_tx_proposals[dialogue.dialogue_label]
        transaction = self.pending_tx_proposals[dialogue.dialogue_label].pop(proposal_id)
        return transaction

    def add_pending_acceptances(self, dialogue: Dialogue, proposal_id: int, transaction: Transaction) -> None:
        """
        Add an acceptance (in the form of a transaction) to the pending list.

        :param dialogue: the dialogue associated with the proposal
        :param proposal_id: the message id of the proposal
        :param transaction: the transaction
        :raise AssertionError: if the pending acceptance is already present.

        :return: None
        """
        assert dialogue.dialogue_label not in self.pending_tx_acceptances and proposal_id not in self.pending_tx_acceptances[dialogue.dialogue_label]
        self.pending_tx_acceptances[dialogue.dialogue_label][proposal_id] = transaction
        self._register_message_with_time(dialogue, proposal_id)

    def pop_pending_acceptances(self, dialogue: Dialogue, proposal_id: int) -> Transaction:
        """
        Remove an acceptance (in the form of a transaction) from the pending list.

        :param dialogue: the dialogue associated with the proposal
        :param proposal_id: the message id of the proposal
        :raise AssertionError: if the pending acceptance is not present.

        :return: the transaction
        """
        assert dialogue.dialogue_label in self.pending_tx_acceptances and proposal_id in self.pending_tx_acceptances[dialogue.dialogue_label]
        transaction = self.pending_tx_acceptances[dialogue.dialogue_label].pop(proposal_id)
        return transaction

    def add_lock(self, transaction: Transaction, as_seller: bool) -> None:
        """
        Add a lock (in the form of a transaction).

        :param transaction: the transaction
        :param as_seller: whether the agent is a seller or not
        :raise AssertionError: if the transaction is already present.

        :return: None
        """
        transaction_id = transaction.transaction_id
        assert transaction_id not in self.locks
        self._register_transaction_with_time(transaction_id)
        self.locks[transaction_id] = transaction
        if as_seller:
            self.locks_as_seller[transaction_id] = transaction
        else:
            self.locks_as_buyer[transaction_id] = transaction

    def pop_lock(self, transaction_id: str) -> Transaction:
        """
        Remove a lock (in the form of a transaction).

        :param transaction_id: the transaction id
        :raise AssertionError: if the transaction with the given transaction id has not been found.

        :return: the transaction
        """
        assert transaction_id in self.locks
        transaction = self.locks.pop(transaction_id)
        self.locks_as_buyer.pop(transaction_id, None)
        self.locks_as_seller.pop(transaction_id, None)
        return transaction

    def start(self) -> None:
        """
        Start the lock manager.

        :return: None
        """
        if not self._cleanup_locks_task_is_running:
            self._cleanup_locks_task_is_running = True
            self._cleanup_locks_task = Thread(target=self.cleanup_locks_job)
            self._cleanup_locks_task.start()

    def stop(self) -> None:
        """
        Stop the lock manager.

        :return: None
        """
        if self._cleanup_locks_task_is_running:
            self._cleanup_locks_task_is_running = False
            self._cleanup_locks_task.join()

    def store_proposals(self, proposals: List[Description], new_msg_id: int, dialogue: Dialogue, origin: str, is_seller: bool, crypto: Crypto) -> None:
        """
        Store proposals as pending transactions.

        :param proposals: the list of proposals
        :param new_msg_id: the new message id
        :param dialogue: the dialogue
        :param origin: the public key of the message sender.
        :param is_seller: Boolean indicating the role of the agent
        :param crypto: the crypto object

        :return: None
        """
        for proposal in proposals:
            proposal_id = new_msg_id  # TODO fix if more than one proposal!
            transaction_id = generate_transaction_id(crypto.public_key, origin, dialogue.dialogue_label, is_seller)  # TODO fix if more than one proposal!
            transaction = Transaction.from_proposal(proposal=proposal,
                                                    transaction_id=transaction_id,
                                                    is_buyer=not is_seller,
                                                    counterparty=origin,
                                                    sender=crypto.public_key,
                                                    crypto=crypto)
            self.add_pending_proposal(dialogue, proposal_id, transaction)
