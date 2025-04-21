# Development Information

The main script `pacman_contest_cluster.py` runs a full contest and uses:

- `cluster_manager.py`: the support script to manage clusters (used by `pacman_contest_cluster.py`).
- `assets/contest.zip`: the actual main contest infrastructure, based on that one from UC (with minor fixes, e.g., delay in replays, upgraded to Python 3.x)
- `assets/layouts.zip`: some interesting layouts that can be used (beyond the randomly generated ones)
- `staff_team_{basic,medium,top}.zip`: the teams from staff, used for `--include-staff-team` option.
  - You can point to the directory containing all three staff agents using `--staff-teams-roots` (default is current dir)
  - You can use your own basic, medium, top agents, as long as they are named accordingly.
  - If you want to use our agents, co ntact us. These teams are not shared as they are used for marking purposes. So, if
     you get access to them, please do not distribute.
- `contest/` folder: developing place for `assets/contest.zip`.
- `extras/` folder: additional scripts and resources; some of them may be out-dated.

## Contests

Current arguments to `ContestRunner` only:

- organizer - the name of the person running the tournament. Used in generating the results html.
- staff_teams_vs_others_only - Binary flag to determine if round robin or bipartite tournament is run.
- include_staff_team - Binary flag to determine if staff teams are included in the tournament. Validation issue if this is false and previous is true.
- staff_teams_dir - the directory that contains all of the staff team submissions. Rename for consistency with teams_root
- compress_logs - Binary flag to determine if logs should be compressed or not.
- max_steps - The length in steps of each job (game). Used for running the games and display in html
- www_dir - Directory for html output to be placed.
- stats_archive_dir=None - Location of archive directory for tournament statistic files
- logs_archive_dir=None - Location of archive directory for tournament log files
- replays_archive_dir=None - Location of archive directory for tournament replay files
- upload_replays=False - Binary flag indicating that replays are uploaded to archive directory, not just copied
- upload_logs=False - Binary flag indicating that logs are uploaded to archive directory, not just copied

Current arguments to Contest only:

- no_fixed_layouts - Number of fixed layouts to be run in contest
- fixed_layouts_file - Location of zip file containing the fixed layouts
- no_random_layouts - Number of random layouts to be run in contest
- team_names_file - File that contains a list of team names (optional, otherwise zip/folder names are used)
- allow_non_registered_students - Binary flag that allows students in tournament that aren't in team_names_file. Potential validation issue if team_names_file missing
- ignore_file_name_format - Binary flag that allows student submissions that don't match the submission file name pattern
- fixed_layout_seeds=[] - List of specific fixed layouts to be used
- random_seeds=[] - List of specific random seeds to be used
- split=1 - Number of tournaments to run in this contest

Current arguments to Both:

- teams_root - the directory that contains all of the student team submissions. Used to identify which teams exist and get their code.

### Jobs

A job represents a single game played between two opponents on one map. It is a named tuple with the following fields:

- command - The command to run the game. This does a number of things including unzipping code, making directories and running the actual python script.
- required_files - Files needed to run the command. This is currently empty as the code is transferred at the start separately, not individually per job.
- return_files - Files to be copied back to the tmp folder. This is generally the replay and log files.
- id - a string which contains the matchup information ($red vs $blue in $map)
- data - information about the red-team, blue-team and layout. Not clear entirely how this is used, given the information is already captured in the command and the id. Seems to largely be returned by the ClusterManager and used as an ID, perhaps worth changing.

Jobs are created by the pacman_contest_cluster script and passed to the ClusterManager for execution.

### Tmp folder

A key component of the cluster runner is the tmp folder. This is where the logs, replays, and teams go for any given tournament.

We would like to expand this tmp folder to be a better history of what occurred, in particular by adding the contest metadata into that folder.
This should be a json file which captures:

- Layouts used in the tournament
- Teams participating in the tournament
- Matchups of teams in the tournament? (To help with team ordering and also staff vs round-robin)
- Hosts? Probably not - we don't care if we re-run in a different place.

tmp folders are crucial for rerunning tournaments; matches without log files are rerun, others are left as is.

## Modifying The Contest Game

The code implementing a game simulator between two players is located in `contest/` as a _git submodule_ from [pacman-contest-agent](https://github.com/AI4EDUC/pacman-contest-agent) repository, which also serves as an empty agent template. Remember that to get the source from its repo, one needs to do this before:

```bash
$ git submodule init
$ git submodule update --remote
```

As of 2019, that code runs under Python 3.6+.

Note that the submodule source under `contest/` is NOT used for the actual cluster tournament, which only uses the source packed in `contest.zip` file.

It is however left there under `contest/` just in case one wants to run and test specific single games, if needed. For example, if we assume that `contest/teams` points to a set of teams, we can run one game as follows:

```bash
$ cd contest/
$ python capture.py -r teams/staff_team_super/myTeam.py -b teams/staff_team_medium/myTeam.py
```

Since the actual simulator code used by the cluster contest script is the one packed in `contest.zip`, any changes, fixes, upgrades, extensions to the simulator have to be done outside and zipped it into `contest.zip` file again.

For example, if one modifies the code in `contest/`, a new `contest.zip` can be generated as follows:

```bash
$ rm -f contest.zip ; cd contest/ ; zip -r  ../contest.zip * ; cd ..
```

## Modifying fixed layouts

The set of fixed layouts used in the script is in zip file `layouts.zip`, which includes the layouts in folder [`layouts/layouts/`](layouts/layouts/).

If a layout is added to the folder or an existing layout is modified, we can re-generate the layout zip file as follows:

```shell
$ zip -j layouts.zip layouts/layouts/*.lay
```

Now the script will use the new `layouts.zip` file for the fixed layouts.
