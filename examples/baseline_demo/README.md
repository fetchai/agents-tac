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
      
