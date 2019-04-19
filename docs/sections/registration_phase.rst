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
* how to handle potential disconnection to the network.

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

The only purpose of the controller to register is to
be easily discoverable by hte


How to register/unregister
--------------------------



Wait for the competition
------------------------


Handle unexpected disconnection
-------------------------------


.. uml:: ../_static/diagrams/registration.uml
   :align: center
   :caption: The transition diagram for the registration phase.

