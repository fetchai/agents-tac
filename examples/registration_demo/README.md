# registration_demo

This tutorial shows how the registration to the Trading Agent Competition works.

## Demo

- Ensure you are running an OEF Node on `localhost`. 

- Run the controller:

      python tac/agents/controller.py
    
- Run the baseline agent:

      python examples/registration_demo/app.py
      
  The client agent will send a `register` request to the controller.
  
  
The logging messages from the first command are:

```
[2019-03-26 19:43:44,109][tac][__init__][DEBUG] Initialized Controller Agent :
{'money_endowment': 20,
 'nb_goods': 5,
 'oef_addr': '127.0.0.1',
 'oef_port': 3333,
 'public_key': 'controller'}
[2019-03-26 19:43:44,110][tac][register][DEBUG] Registering with tac data model
[2019-03-26 19:43:44,111][tac][main][DEBUG] Running agent...
[2019-03-26 19:43:46,076][tac][on_message][DEBUG] [ControllerAgent] on_message: msg_id=0, dialogue_id=0, origin=simple_agent
[2019-03-26 19:43:46,076][tac][handle_register][DEBUG] Agent registered: 'simple_agent'
[2019-03-26 19:43:46,076][tac][handle][DEBUG] Returning response: Registered({})
```

The logging messages from the second command are:
```
[2019-03-26 19:43:46,076][tac][on_search_result][DEBUG] Agents found: ['controller']
[2019-03-26 19:43:46,076][tac][on_search_result][DEBUG] Sending 'Register({})' message to the TAC Controller controller
[2019-03-26 19:43:46,077][tac][on_message][DEBUG] Response from the TAC Controller 'controller': Registered({})
```