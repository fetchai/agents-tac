This tutorial shows how to set up a simple TAC.

## Demo

- Be sure you're running an OEF Node on `localhost`. 

- Run the example:

      python examples/baseline_demo/tac_agent_spawner.py N

  Where `N` is the number of participants.
    
Follows the sequence diagram of the communications between agents:

![](./registration .png)


### Other parameters

- `--oef-addr` and `--oef-port` allow you to specify a different OEF Node tu use for the simulation.
- `--uml-out` is the filepath where to to store the activity of the simulation in PlantUML syntax.
- `--data-output-dir` is the output directory to use for storing simulation data.
- `--experiment-id` is the name to give to the experiment. The data will be stored in `${data_output_dir}/${experiment_id}`.

Example:

      python examples/baseline_demo/tac_agent_spawner.py 
          3 
          --oef-addr oef.economicagents.com 
          --oef-port 3333
          --uml-out out.uml
          --data-output-dir my_data
          --experiment-id my_experiment
      
It generates a `game.json` file in `my_data/my_experiment/` folder that looks like:

```
{'fee': 1,
 'initial_endowments': [[1, 0, 2, 2, 2], [1, 2, 0, 0, 0]],
 'initial_money_amount': 20,
 'instances_per_good': 2,
 'nb_agents': 2,
 'nb_goods': 5,
 'preferences': [[4, 0, 1, 3, 2], [3, 4, 2, 0, 1]],
 'scores': [4, 3, 2, 1, 0],
 'transactions': [{'amount': 3,
                   'buyer_id': 1,
                   'good_ids': [0, 1, 2, 3, 4],
                   'quantities': [0, 0, 1, 1, 1],
                   'seller_id': 0,
                   'timestamp': '2019-04-03 15:25:25.240885'},
                  {'amount': 3,
                   'buyer_id': 0,
                   'good_ids': [0, 1, 2, 3, 4],
                   'quantities': [0, 1, 0, 0, 0],
                   'seller_id': 1,
                   'timestamp': '2019-04-03 15:25:25.242052'}]}
```
