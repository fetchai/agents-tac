# Templates
Templates for agent development.

Check out the [package documentation](../../master/docs) to learn more about the agent and competition framework.

## Available templates

- `basic.py` this lets you run a preconfigured baseline agent without further development
- `advanced.py` this lets you configure the strategy of the baseline agent without the need to implement the whole agent.
- `expert.py` this lets you start from scratch, only borrowing our agent architecture which separates the agent loop from the event loop.

## Testing with Sandbox (recommended)

To test your agent run it against baseline agents in the sandbox. Follow the steps 1.-3. in sandbox readme, then start your own agent:

```
python3 templates/v1/basic.py --name basic1 --gui
```

The following additional parameters can be used to tune the agent:

- `--register-as`: `choices=['seller', 'buyer', 'both']`, The string indicates whether the baseline agent registers as seller, buyer or both on the oef.
- `--search-for`, `choices=['sellers', 'buyers', 'both']`, The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.
- `--is-world-modeling`, `type=bool`, Whether the agent uses a workd model or not.   
- `--services-interval`, `type=int`, The number of seconds to wait before doing another search.


### Generate private key (optional)

A private key for your agent is generated every time by the library. 
If you want to use the same cryptographic key, you can follow these steps:

- Generate a private key:
      
      python3 scripts/generate_private_key.py private_key.pem
      
- Every time you run your agent, add the parameter `--private-key <pem-file>` to your command:

      python3 templates/v1/basic.py --name basic1 --gui --private-key private_key.pem

## Testing manually (not recommended)

- First, start the oef:
```
python3 oef_search_pluto_scripts/launch.py -c ./oef_search_pluto_scripts/launch_config.json
```

- Second, start the visdom server in shell:
```
python3 -m visdom.server
```

- Third, tart the controller, followed by two agents in separate terminals.
```
python3 tac/platform/controller.py --verbose --registration-timeout 20 --nb-agents 2 --tx-fee 0.0 --gui
```
```
python3 templates/v1/basic.py --name basic0 --gui
```
```
python3 templates/v1/basic.py --name basic1 --gui
```

The following parameters can be used to tune the agent:

- `--register-as`: `choices=['seller', 'buyer', 'both']`, The string indicates whether the baseline agent registers as seller, buyer or both on the oef.
- `--search-for`, `choices=['sellers', 'buyers', 'both']`, The string indicates whether the baseline agent searches for sellers, buyers or both on the oef.
- `--is-world-modeling`, `type=bool`, Whether the agent uses a workd model or not.   
- `--services-interval`, `type=int`, The number of seconds to wait before doing another search.

- Fourth, navigate to `http://localhost:8097/` and select the appropriate environment.
