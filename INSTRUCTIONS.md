# Instructions

The system contains two main scripts:

1. ```pacman_contest_cluster.py``` is the main script to actually run a contest.
2. ```pacman_html_generator.py``` generates an HTML web page from existing data of already ran contests.

Some terminology first:

* A **_contest_** is a set of tournaments that are played sequentially.
* A **_tournament_** is a set of games that are played between a variety of teams on a variety of maps. Tournaments can be _round-robin_, in which every team plays every other team (complete graph), or _staff-only_ in which the staff teams play every other team (complete bipartite graph).
* A **_job_** is a single game played between two teams on a single map.

For setting up the system, refer to [SETUP.md](SETUP.md).

## Overview Of Marking Process

First, the script will do the following setup steps:

1. Authenticates to all workers specified.
2. Collect all the teams.
    * Collect the team names from the `<team-name>.zip` files.
3. Take `contest.zip`, `layouts.zip` (where some fixed layouts are stored), and the set of collected set of teams and:
    1. create a temporary full contest dir `contest-tmp`;
    2. zip it into `contest_and_teams.zip` file;
    3. transfer  `contest_and_teams.zip` to each available worker.

Then, for each game:

 1. expand in `contest_and_teams.zip` to `/tmp/cluster_xxxxxxx`;
 2. run game;
 3. copy back log and replay to marking machine.

Finally, it will produce stat files as JSON files (can be used to generate HTML pages).

## Example runs

To have a test run in `localhost` with the teams available in `test/`:

````shell
$ python  pacman_contest_cluster.py --organizer "RMIT COSC1125/1127 - Intro to AI" \
        --teams-roots ./test/reference-teams/ ./test/students/  \
        --www-dir www/ \
        --max-steps 1200 \
        --no-fixed-layouts 5 --no-random-layouts 5 \
        --workers-file ./test/workers_localhost.json
        --staff-teams-roots ./test/reference-teams/staff-teams/
````

The command used in AI17 was as follows:

````shell
$ python  pacman_contest_cluster.py --organizer "RMIT COSC1125/1127 - Intro to AI" \
        --teams-roots AI17-contest/teams1/ AI17-contest/teams2/  \
        --www-dir www/ \
        --max-steps 1200 \
        --no-fixed-layouts 5 --no-random-layouts 10 \
        --workers-file AI1-contest/workers/nectar-workers.jason  
        --staff-teams-roots AI17-contest/staff-teams/
        --upload-www-replays
````

The `--upload-www-replays` option tells the script to upload the replays file only into a sharing file service instead of your local directory (to save storage).
