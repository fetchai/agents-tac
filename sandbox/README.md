# Sandbox

This folders contains the `docker-compose` scripts to run an ensemble of 
Docker image to support TAC.

Please install [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/).

## Build

    docker-compose build

## Run TAC

    docker-compose up


## Configuration

To configure the execution of TAC, you can tune the following parameters:
- `NB_AGENTS` is the minimum number of agents to start the competition.
- `NB_GOODS` is the number of types of goods to trade in the competition.
- `NB_BASELINE_AGENTS` is the number of baseline agents in the TAC instance. 
- `REGISTRATION_TIME` is the time (in seconds) that the controller waits for registrations for TAC. 

To change the parameters:

- export the variable before the command:

      export NB_BASELINE_AGENTS=2
      docker-compose up

- set the variable in one command:

      NB_BASELINE_AGENTS=2 docker-compose up

- Specify the values in the [`.env`](.env) file.


To double-check whether the variable has been set successfully, use:

    docker-compose config

### Run TAC with baseline agents only

To run a TAC instance with only baseline agents, you can set `NB_AGENTS` equal to `NB_BASELINE_AGENTS`.
`REGISTRATION_TIME` should be high enough (e.g. 5-10 seconds) to allow all the baseline agents to register to TAC.
    
Notice: if `NB_AGENTS` > `NB_BASELINE_AGENTS`, there are no enough agents to start the TAC.
    
### Run TAC with baseline agents and your own agent implementation(s)

If you want to include your agents:  

- Set up an OEF-Node, a Controller agent and a list of baseline agents:

      docker-compose up
      
- Connect your agent to `localhost:3333`, e.g.:

      python3 ../scripts/template_agent.py
      
In this case, be careful of the values of `NB_AGENTS` and `NB_BASELINE_AGENTS`:
- if `NB_AGENTS` <= `NB_BASELINE_AGENTS`, the competition might start even though you didn't register your agent;
- if  `NB_AGENTS` > `NB_BASELINE_AGENTS`, the competition waits until `NB_AGENTS` - `NB_BASELINE_AGENTS` agents to start.
  But if you're planning to run only one agents, the difference should be just `1`, e.g. when `NB_AGENTS=10` and `NB_BASELINE_AGENTS=11`. 
  