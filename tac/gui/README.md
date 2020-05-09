## GUIs		

This package contains GUI tools to interact with the TAC project (e.g. data visualization & agent launcher).		

## Recommended Visualization:

This displays dynamic information.

### To run a Visdom server via script to visualise historic data

Set explicit version id `version_id` and then run

    python3 tac/gui/dashboard.py --datadir #{data_output_dir}/#{version_id}

Here `#{data_output_dir}/#{version_id}` is the path to the folder containing the `game.json` file.


### To visualize the leaderboard after a full TAC 

Assuming the output of `sandbox/run_iterated_games.py` is in `sandbox/data`, do:

    python tac/gui/dashboards/leaderboard.py --datadir sandbox/data --dump_stats

## Alternative Visualization

This displays static information.

### Run a basic flask app

    python3 tac/gui/app.py