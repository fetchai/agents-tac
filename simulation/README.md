# Simulation

This tutorial shows how to simulate a TAC.

## Tutorial

- Before getting started, check that:

  - [x] You have followed the steps under 'Dependencies' and 'Preliminaries' on root readme.
  - [x] You are connected to the internet (to pull the latest docker images).


## Quickstart

Simply run:

      python scripts/launch_alt.py

## Manual

- First, ensure that you are running an OEF Node on `localhost`, using this command (make sure all docker containers are stopped `docker stop $(docker ps -q)`):

      python scripts/oef/launch.py -c ./scripts/oef/launch_config.json


- Second, (in a new terminal window, from root and in shell) start a `visdom` server:

      python -m visdom.server
  
- Third, (in a new terminal window, from root and in shell) run the simulation example with the dashboard flag to visualize data in realtime:

      python simulation/v1/tac_agent_spawner.py --dashboard

- Finally, lean back and watch the competition on `http://localhost:8097` in your browser (you might have to select the right environment `tac && tac_controller` and deselect `main` in the visdom browser tab).

![Screenshot of visdom env selection](../../docs/visdom_env.png)

### Optional parameters/flags

For a full list, do `python simulation/tac_agent_spawner.py -h`

- `--nb-agents` is the number of agents to participate in the competition.
- `--nb-goods` is the number of goods in the competition.
- `--nb-baseline-agents` is the number of number of baseline agents to participate in the competition.
- `--oef-addr` and `--oef-port` allow you to specify a different OEF Node to use for the simulation.
- `--register-as` the string indicates whether the baseline agent registers as seller, buyer or both on the oef.
- `--search-for` the string indicates whether the baseline agent searches for sellers, buyers or both on the oef.
- `--uml` specifies whether or not to store the activity of the simulation in PlantUML syntax.
- `--data-output-dir` is the output directory to use for storing simulation data in `${data_output_dir}/${experiment_id}`.
- `--version-id` is the name to give to the simulation.
- `--plot` specifies whether to plot a summary of the game.
- `--money-endowment` is the money amount every agent receives.
- `--base-good-endowment` is the base amount of per good instances every agent receives.
- `--lower-bound-factor` is the lower bound factor of a uniform distribution used for generating good instances.
- `--upper-bound-factor` is the upper bound factor of a uniform distribution used for generating good instances.
- `--tx-fee` is the transaction fee.
- `--registration-timeout` is the amount of time (in seconds) to wait for agents to register before attempting to start the competition.
- `--inactivity-timeout` is the amount of time (in seconds) to wait during inactivity until the termination of the competition.
- `--competition-timeout` is the amount of time (in seconds) to wait from the start of the competition until the termination of the competition.
- `--visdom-addr` is the TCP/IP address of the Visdom server
- `--visdom-port` is the TCP/IP port of the Visdom server
- `--dashboard` is a flag to specify that the dashboard is live and expecting an event stream.
- `--seed` is the seed for the random module.
- `--fraction-world-modeling` the fraction of world modelling baseline agents.

Example:

      python simulation/v1/tac_agent_spawner.py 
          --nb-agents 10
          --nb-goods 10
          --nb-baseline-agents 10
          --oef-addr oef.economicagents.com 
          --oef-port 10000
          --service-registration-strategy both
          --uml True
          --data-output-dir data
          --experiment-id my_experiment
          --plot True
          --money-endowment 200
          --base-good-endowment 2
          --lower-bound-factor 1
          --upper-bound-factor 1
          --tx-fee 1
          --registration-timeout 10
          --inactivity-timeout 60
          --competition-timeout 240
          --dashboard
          --seed 42
      
It generates a `game.json` file in the `${data_output_dir}/${version_id}` that can be inspected with a dashboard (see `tac/gui`).

### Scalability

We can confirm that the simulation runs successfully on a MacBook Pro (13-inch, 2017, 3.1 GHz Intel Core i5, 16 GB 2133 MHz LPDDR3) with 60 agents and 10 goods. Higher number of agents cause issues with threading.
