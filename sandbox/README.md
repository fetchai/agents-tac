# Sandbox

This folders contains the `docker-compose` scripts to run an ensemble of 
Docker image to support TAC.

Please install [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/).

## Build

    docker-compose build
    
## Run

To run the Docker ensemble, you need to set up the environment variable `NB_BASELINE_AGENTS`. 
The default one, provided in the `.env` file, is `2`. If it's OK for you, 
you can just run:

    docker-compose up
    
To change the parameter:

- export the variable before the command:

      export NB_BASELINE_AGENTS=2
      docker-compose up

- set the variable in one command:

      NB_BASELINE_AGENTS=2 docker-compose up