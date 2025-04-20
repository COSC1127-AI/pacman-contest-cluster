# Instructions

The system contains two main scripts:

1. ```pacman_contest_cluster.py``` is the main script to actually run a contest.
2. ```pacman_html_generator.py``` generates an HTML web page from existing data of already ran contests.

Some terminology first:

* A **_contest_** is a set of tournaments that are played sequentially.
* A **_tournament_** is a set of games that are played between a variety of teams on a variety of maps. Tournaments can be _round-robin_, in which every team plays every other team (complete graph), or _staff-only_ in which the staff teams play every other team (complete bipartite graph).
* A **_job_** is a single game played between two teams on a single map.

For setting up the system, refer to [SETUP.md](SETUP.md).

