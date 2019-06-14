### v2

The second iteration of our agents have a more advanced architecture whereby the agent main loop is separated from the event loop.


### Demo

- Run the OEF Docker image on `localhost`, using this command:

```
docker run -it -p 20000:20000 -p 3333:3333 -p 40000:40000 fetchai/oef-search:v4 node no_sh \
    --node_key Search1 \
    --core_key Core1 \
    --search_port 20000 \
    --core_port 3333 \
    --dap_port 30000 \
    --director_api_port 40000
```

- and run controller like so

      python3 tac/platform/controller.py --verbose --nb-agents 2 --inactivity-timeout 60

- and two agents

      python3 tac/agents/v2/examples/baseline.py --name agent_1

      python3 tac/agents/v2/examples/baseline.py --name agent_2
