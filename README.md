# PACMAN CAPTURE THE FLAG - CONTEST SCRIPT

This system runs complex contests for the [UC Berkley Pacman Conquer the Flag](http://ai.berkeley.edu/contest.html) game.

Designed & developed for RMIT COSC1125/1127 AI course in 2017 by lecturer Prof. Sebastian Sardina (with programming support by Marco Tamassia), based on an original script from Dr. Nir Lipovetzky (Melbourne University). Since then, the tool has been continuously improved and extended to fit RMIT COSC1125/1127 and UNIMELB COMP90054 AI course.

The system runs on Python 3.9+.

**CONTACT:** Prof. Sebastian Sardina (ssardina@gmail.com)

> [!IMPORTANT]
> Refer to [SETUP.md](SETUP.md) on how to setup the framework (in the coordination machine and all worker hosts) and [INSTRUCTIONS.md](INSTRUCTIONS.md) on how to use the framework. 👌

## Overview

This system runs a full Pacman Capture the Flag tournament among many teams using a _cluster of machines/CPUs_ (e.g., [Australia's NeCTAR](https://nectar.org.au/).

The contest script takes a set of teams, a set of machine workers in a cluster, and a tournament configuration (which layouts and how many steps per game), and runs games concurrently (one per worker) for every pair of teams and layouts (round-robin type of tournament), and produces files and html web page with the results. With `n` teams playing on `k` layouts there will be `(n(n-1) / 2)k` games. To deal with too many teams, the script can play teams against staff team systems only and also split teams into random sub-contests and run them in sequence.

The full contest is **all-against-all tournament** (round-robin) with the following rank generation:

- 3 points per win; 1 point per tie; 0 points per lose. Failed games are loses.
- Ordered by: points first, no. of wins second, score points third.

The main script is `pacman_contest_cluster.py`.

To see options available run:

```bash
$ python pacman_contest_cluster.py -h
```

Script `pacman_html_generator.py` generates an HTML web page from existing data of already ran contests.

## Features

- Build `n` sub-contests where teams are assigned randomly to one of them (`--split` option).
- Play teams only against staff/reference teams.
- Runs multiple games at the same time by using a cluster of worker machines/CPUs.
  - option `--workers-file <json file>`
  - connection via ssh with tunneling support if needed.
- Able to use variable number of fixed layouts and randomly generated layouts.
  - options `--no-fixed-layouts` and `--no-random-layouts`
- Generate an HTML page with the contest result and full details, including links to replay files.
  - Ability to store replays and logs into [`https://transfer.sh`](https://transfer.sh) service to avoid filling local www space.
  - Ranking generation: 3 points per win; 1 point per tie. Failed games are loses. Ordered by: points first, no. of wins second, score points third.
- Handle latest submission per team, by sorting via timestamp recorded in file name.
- Can resume a partial ran contest or extend an existing contest.
- Save options into a JSON file `config.json` for future runs using `--build-config-file` option.

## Screenshot

![Contest Result](extras/screenshot01.png)

## CONTRIBUTORS

- Prof. Sebastian Sardina (ssardina@gmail.com)
- Dr. Andrew Chester (while tutor at RMIT 2020-2024)
- A/Prof. Nir Lipovetzky (Melbourne University)
- Dr. Marco Tamassia (2017)

