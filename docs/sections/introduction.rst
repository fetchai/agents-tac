.. _introduction:

Introduction
============

This documentation describes the *Trading Agent Competition*,
a competition between developers in a trading game
where the goal is to implement the best trading strategy.

At the beginning of the game, each agent holds a given quantity
of every *good*. The agents can buy other goods from other agents
by submitting transactions to the game controller.

The aim of the game is to maximize an utility function,
depending on the goods the agent has been able to buy/hold
and on the utility values per good, assigned randomly to every agent
at the beginning of the game.

The competition will be run in a *distributed* fashion.
The programs of the participant can communicate through
an OEF Node, that will be operative for the duration of
the competition.

An instance of TAC is loosely split in three phases:

- *registration phase*, during which trading agents can register
  to the competition
- *trading phase*, during which the actual competition take place.
  the
- *evaluation phase*, where the activity of the trading agents
  is scored and the winner is announced.

The competition will be controlled by a special agent,
that we call *controller agent*. Further details will be
provided later in the documentation.

In the following sections, we will outline an example
of TAC, describing more in detail the three phases,
and how the different components
work together.
