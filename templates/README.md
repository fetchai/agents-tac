# Templates
Templates for agent development.

## Available templates

- `basic.py` this lets you run a preconfigured baseline agent without further development
- `advanced.py` this lets you configure the strategy of the baseline agent without the need to implement the whole agent.
- `expert.py` this lets you start from scratch, only borrowing our agent architecture which separates the agent loop from the event loop.

## GUI

To visualize the statistics of your agent:

- in another terminal, after executing `pipenv shell`, run a [Visdom](https://github.com/facebookresearch/visdom) server:

      python3 -m visdom.server
      
- Use the flag `--gui` when launching the template scripts.