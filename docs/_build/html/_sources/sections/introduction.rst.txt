.. _introduction:

Introduction
============

This documentation describes the *Trading Agent Competition*,
a competition between autonomous *trading agents* in a trading game
where the goal of developers is to implement the best trading strategy
in their agent.

The competition is run in a *distributed* fashion. The agents can communicate through
an OEF Node (the open economic framework), that is operative for the duration of the competition.

The competition consists of a number of game instances. Each game instance
is managed by an agent with a special role, the *controller agent*.
An instance of TAC is loosely split in two phases:

- *registration phase*, during which trading agents can register
  to the competition.
- *trading phase*, during which the actual competition take place.

At the beginning of the trading phase, the controller agent assigns each trading agent
the *game data*. The game data consists of a specific quantity for each one of a number
of *goods* to be traded as well as a *money amount* and *utility parameters* for each good.
The utility parameters specify how the agent values a good. The goods and utility parameters
are assigned to agents in such a way that the competition setup is fair and interesting.

Once the agents have received their game data, the agents can buy goods from and sell goods
to other agents. The agents can advertise the goods they supply and the goods they demand on the
OEF. They can also search the OEF for goods supplied or demanded by other agents.
Finally, the agents use the OEF to communicate with each other.

When two agents arrive at an agreement to trade a bundle of goods they settle
their transaction by submitting it to the controller agent. A
transaction specifies which goods are exchanged as part of the transaction at at which
price.

The aim of the agent during a game is to maximize their *utility function*. At any
point they can compute their utility by using the goods they currently hold, the
money amount they currently hold as well as their utility function parameters.

The competition is terminated by the controller agent after a predetermined amount 
of time and the agent with the highest score wins.

In the following sections, we will describe in more detail the two phases of a game,
and how the different agent components work together.
