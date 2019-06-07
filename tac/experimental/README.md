### Registration agent demo

- run the OEF Docker image on `localhost`, using this command:

```
docker run -it -p 20000:20000 -p 3333:3333 -p 40000:40000 fetchai/oef-search:v1 node no_sh \
    --node_key Search1 \
    --core_key Core1 \
    --search_port 20000 \
    --core_port 3333 \
    --dap_port 30000 \
    --director_api_port 40000
```
or
```
python3 oef_search_pluto_scripts/launch.py -c ./oef_search_pluto_scripts/launch_config.json
``` 

- in one terminal run the controller:

      python3 tac/agents/controller.py
      
- in another terminal run the agent:

      python3 tac/experimental/registration_agent1.py

- or
      python3 tac/experimental/registration_agent2.py
     
- or
      python3 tac/experimental/registration_agent3.py
