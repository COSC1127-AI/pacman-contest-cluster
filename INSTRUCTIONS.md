# Instructions

The system contains two main scripts:

1. ```pacman_contest_cluster.py``` is the main script to actually run a contest.
2. ```pacman_html_generator.py``` generates an HTML web page from existing data of already ran contests.

Some terminology first:

* A **_contest_** is a set of tournaments that are played sequentially.
* A **_tournament_** is a set of games that are played between a variety of teams on a variety of maps. Tournaments can be _round-robin_, in which every team plays every other team (complete graph), or _staff-only_ in which the staff teams play every other team (complete bipartite graph).
* A **_job_** is a single game played between two teams on a single map.

>[!IMPORTANT]
> For setting up the system, refer to [SETUP.md](SETUP.md).


- [Instructions](#instructions)
  - [Overview Of Marking Process](#overview-of-marking-process)
  - [Example runs](#example-runs)
    - [Run contest only vs staff teams](#run-contest-only-vs-staff-teams)
    - [Run a multi/split contest](#run-a-multisplit-contest)
  - [Resume/Extend/Modify Executed Contest](#resumeextendmodify-executed-contest)
    - [Re-run only some teams in a given contest](#re-run-only-some-teams-in-a-given-contest)
    - [Re-run only updated teams](#re-run-only-updated-teams)
    - [Remove agent from contest](#remove-agent-from-contest)
  - [Webpage](#webpage)
    - [Interactive Dashboard](#interactive-dashboard)
  - [Troubleshooting](#troubleshooting)
    - [Cannot connect all hosts with message: _"Exception: Error reading SSH protocol banner"_](#cannot-connect-all-hosts-with-message-exception-error-reading-ssh-protocol-banner)


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

### Run contest only vs staff teams

To make the teams play only the staff teams (but not between them), use the  `--staff-teams-vs-others-only` option.

To hide the staff teams from the final leaderboard table, use `--hide-staff-teams`.

Finally, one can higlight different levels of performance using option `--score-thresholds`.

### Run a multi/split contest

When having too many teams, you can use the `--split n` option to generate `n` balanced contests from the pool of teams. Each team will be assigned randomly to one contest. Sub-contests will have the timestamp but a letter as suffix, e.g., `A`, `B`, etc.

For example, to run a split multi-contest with 5 sub-contests use `--split 5`.

## Resume/Extend/Modify Executed Contest

It is possible to **resume** an existing failed/partial competition or **modify/extend** a specific competition by using the option `--resume-contest-folder`.

This could be useful, for example, when:

* a contest has failed half-way: we can resume from where it is left and run only the games that are missing;
* want to extend a previously ran contest with more layouts;
* want to delete a team from a previously executed contest;
* want to repair/change an agent (submitted or staff).

In all cases, the idea is to re-use the logs and replays stored in the existing temporal folder of the already executed contest, namely, `tmp/logs-run` and `tmp/replays-run`.

In all cases, the method is the same:

1. Move or copy the temporary folder of the contest to be resumed/modified: `mv tmp tmp.bak`.
   * This is extremely important, the folder `tmp/` will be re-created from scratch, so we have to move away and save the one corresponding to the contest to be modified/extended.
1. Perform whatever changes to the previous contest by modifying `tmp.bak/`; for example:
   * Delete all the logs of some teams if you wan to re-run that team.
   * Modify `tmp.bak/config.jason` to delete some team that should not be included.
1. Run the script and use `--resume-contest-folder tmp.bak/` to instruct resuming that saved contest:

    ```shell
    python pacman-contest-cluster.git/pacman_contest_cluster.py  --resume-contest-folder tmp.bak
    ```

This will run the exact configuration used in the contest being resumed by reading and using saved configuration `tmp.bak/config.json`. Importantly, all agents (submitted and staff) will be packed from scratch.

One can override the options in the configuration file by adding options. For example, to extend an existing contest with more layout games, use options `--no-fixed-layouts` and `--no-random-layouts` with greater numbers than the one in the contest done. For example, if the contest in `tmp.bak/` included 2 fixed and 3 random layouts, we can extend it with more one more of each type as follows:

```shell
python pacman-contest-cluster.git/pacman_contest_cluster.py --no-random-layouts 3 --no-fixed-layouts 4 --resume-contest-folder tmp.bak
```

This will add one more fixed and one more random layout, both chosen randomly.

If you want to control exactly which fixed or random layout to add, then use options `--fixed-layout-seeds` and `--random-layout-seeds`. This will force the script to use specific layouts (look in folder [layouts/](layouts/) for available fixed, non-random, layouts).

* When using these options, the information stored in the previous contest configuration file on which layouts were used will be disregarded.
* Thus, one has to specify ALL the layouts that the new contest must use, including the previous ones and the specific ones one wants to add.
* If the seeds given are less than the number of layouts asked for, the remaining are completed randomly.

For example, if the previous contest used `contest05Capture` and `contest16Capture` fixed layouts and `7669,1332,765`, one can extend it further with specific layouts `contest20Capture` and `1111` as follows:

```shell
python pacman-contest-cluster.git/pacman_contest_cluster.py --no-random-layouts 3 --no-fixed-layouts 4 --fixed-layout-seeds contest05Capture,contest16Capture,contest20Capture --random-layout-seeds 7669,1332,765,1111 --resume-contest-folder tmp.bak
```

Remember the seeds of the layouts used in the previous contests are always saved in file `config.json`. It can also be manually extracted from log file names as follows:

1. For the random seeds:

    ```bash
    ls -la tmp.bak/logs-run/ |  grep RANDOM | sed -e "s/.*RANDOM\(.*\)\.log/\1\,/g" | sort -u | xargs -n 100
    ```

2. For the fixed layouts:

    ```bash
    ls -la tmp.bak/logs-run/ |  grep -v RANDOM | grep log | sed -e "s/.*_\(.*\)\.log/\1\,/g" | sort -u | xargs -n 100
    ```

### Re-run only some teams in a given contest

If only one or a few teams failed, one can just re-run those ones by basically deleting their logs from the temporary folder and re-running/resuming a contest as above.

To delete the logs of a given team:

```bash
$ find tmp.bak -name \*<TEAM NAME>\*.log -delete
```

When resuming the contest in `tmp.bak/`, it will only run the games for the logs you just deleted.

### Re-run only updated teams

One quick and good strategy is to run a big contest but re-playing all games where one of the teams was updated.

To do so, we use the above method but we first delete all the logs of the teams that have been updated:

```bash
$ for d in `cat ai20-contest-timestamps.csv | grep updated | awk -F "\"*,\"*" '{print $1}'` ; do find tmp.bak/contest-a/logs-run/ -name \*$d*.log ; done
```

This takes advantage of the cloning script that leaves a column in the csv file stating whether the repo was updated or not from the last cloning.

### Remove agent from contest

To remove an agent `XYZ`, delete all the logs for that team in `tmp.bak/` and delete the team from  `tmp.bak/config.json`. Then resume the contest, it will skip ALL the games and produce the new contest without team  XYZ`.

## Webpage

A contest will leave JSON files with all stats, replays, and logs, from which a web page can be produced.

For example, to build web page in `www/` from stats, replays, and logs dirs:

```shell
$ python pacman_html_generator.py --organizer "Inter Uni RMIT-Mel Uni Contest" \
    --www-dir www/ \
    --stats-archive-dir stats-archive/  \
    --replays-archive-dir replays-archive/ \
    --logs-archive-dir logs-archive/
```

or if all stats, replays, and logs are within `www/` then just:

```shell
$ python pacman_html_generator.py --organizer "Inter Uni RMIT-Mel Uni Contest" --www-dir www/
```

> [!NOTE]
> If the stats file for a run has the `transfer.sh` URL for logs/replays, those will be used.

### Interactive Dashboard

As of 2020, the system includes a pretty visual dashboard that can display the results of the various contests carried out in an interactive manner. Students can select which teams to display, and compare selectively.

The dashboard will be served as a web-server, by default on port 8501.

See `/dashboard/` folder for more information how to set-it up and run the dashboard system.

## Troubleshooting

### Cannot connect all hosts with message: _"Exception: Error reading SSH protocol banner"_

Cannot connect all hosts with message: _"Exception: Error reading SSH protocol banner"_

* This happens when a single host has more than 10 CPUs.
* The problem is not the script, but the ssh server in the cluster. By default it does not accept more than 10 connections.
* Configure `/etc/ssh/sshd_config:` in the host with `MaxStartups 20:30:60`
* Check [this issue](https://github.com/ssardina-teaching/pacman-contest/issues/26)
