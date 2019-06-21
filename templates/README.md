# Templates
Templates for agent development.

Check out the [package documentation](../../master/docs) to learn more about the agent and competition framework.

## Available templates

- `basic.py` this lets you run a preconfigured baseline agent without further development
- `advanced.py` this lets you configure the strategy of the baseline agent without the need to implement the whole agent.
- `expert.py` this lets you start from scratch, only borrowing our agent architecture which separates the agent loop from the event loop.

## Testing with Sandbox (recommended)

To test your agent run it against baseline agents in the sandbox.

## Testing manually (not recommended)

- Start the oef:
```
python3 oef_search_pluto_scripts/launch.py -c ./oef_search_pluto_scripts/launch_config.json
```

- Start the visdom server in shell:
```
python3 -m visdom.server
```

- Start the controller, followed by two agents in separate terminals.
```
python3 tac/platform/controller.py --verbose --registration-timeout 20 --nb-agents 2 --tx-fee 0.0 --gui
```
```
python3 templates/v2/basic.py --name basic0 --gui
```
```
python3 templates/v2/basic.py --name basic1 --gui
```

## GUI

To visualize the statistics of your agent:

- in another terminal, after executing `pipenv shell`, run a [Visdom](https://github.com/facebookresearch/visdom) server:

      python3 -m visdom.server
      
- Use the flag `--gui` when launching the template scripts.

- Navigate to `http://localhost:8097/` and select the appropriate environment.