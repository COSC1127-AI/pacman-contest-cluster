# PACMAN CAPTURE THE FLAG - CONTEST SCRIPT

This system runs complex contests for the [UC Berkley Pacman Conquer the Flag](http://ai.berkeley.edu/contest.html) game.

Designed & developed for RMIT COSC1125/1127 AI course in 2017 by lecturer A/Prof. Sebastian Sardina (with programming support by Marco Tamassia), based on an original script from Dr. Nir Lipovetzky. Since then, the tool has been continuously improved and extended to fit RMIT COSC1125/1127 and UNIMELB COMP90054 AI course.

The system runs on Python 3.x. Currently used on Python 3.6.

**CONTACT:** Prof. Sebastian Sardina (ssardina@gmail.com) and Dr. Nir Lipovetzky (nirlipo@gmail.com)

## Overview

This system runs a full Pacman Capture the Flag tournament among many teams using a _cluster of machines/CPUs_ (e.g., [Australia's NeCTAR](https://nectar.org.au/).

The contest script takes a set of teams, a set of machine workers in a cluster, and a tournament configuration (which layouts and how many steps per game), and runs games concurrently (one per worker) for every pair of teams and layouts (round-robin type of tournament), and produces files and html web page with the results. With `n` teams playing on `k` layouts there will be `(n(n-1) / 2)k` games. To deal with too many teams, the script can play teams against staff team systems only and also split teams into random sub-contests and run them in sequence.

The full contest is **all-against-all tournament** (round-robin) with the following rank generation:

- 3 points per win; 1 point per tie; 0 points per lose. Failed games are loses.
- Ordered by: points first, no. of wins second, score points third.

The main script is `pacman_contest_cluster.py`.

To see options available run:

```bash
python3  pacman_contest_cluster.py -h
```

## Features

- Build `n` subcontests where teams are assigned randomly to one of them (`--split` option).
- Play teams only against staff teams.
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

## LICENSE

This project is using the GPLv3 for open source licensing for information and the license visit GNU website (<https://www.gnu.org/licenses/gpl-3.0.en.html>).

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.
