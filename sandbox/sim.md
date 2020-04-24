python tac/gui/dashboards/leaderboard.py --datadir data/shared/EX_2

to inspect summary stats


python run_iterated_games.py --config config.json --skip


Null hypothesis:
World modelling and baseline agents achieve same aggregate score

better
World modelling and baseline agents achieve same average score

Alternate hypothesis:
World modelling agents achieve higher average score (one-sided t-test)


Sample: 60 games
Population: all games with that config

> sample is random due to seeds (and inherent randomness


use t-test: we do not know population params
independent samples t-test for means comparison


Compare same group runs
> run with same seed 20 times
> compare results

Paired sample t-test


python tac/gui/dashboards/leaderboard.py --datadir data/shared/EX_2