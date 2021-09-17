# SCHEDULE COMPETITION via `driver.py`

If you want to automate the tournament, use the `driver.py` provided. It has the following options:

```bash
  --username [USERNAME]
                        username for --teams-server-url or for https git connection
  --password [PASSWORD]
                        password for --teams-server-url or for https git connection
  --dest-www [DEST_WWW]
                        Destination folder to publish www data in a web
                        server. (it is recommended to map a web-server folder
                        using smb)
  --teams-server-folder [TEAMS_SERVER_FOLDER]
                        folder containing all the teams submitted at the
                        server specified at --teams-server-name
  --teams-server-url [TEAMS_SERVER_URL]
                        server address containing the teams submitted
  --teams-git-csv [TEAMS_GIT_CSV] 
                        CSV containining columns TEAM, 'GitLab SSH repository link' and 'GitLab https repository link' 
  --tournament-cmd [TOURNAMENT_CMD]
                        specify all the options to run pacman-ssh-contesy.py
  --cron-script-folder [CRON_SCRIPT_FOLDER]
                        specify the folder to the scripts in order to run cron
```

You can run a competition using the following command:

```bash
$ driver.py --dest-www '' --teams-git-csv xxx --tournament-cmd '--compress-log --organizer "UoM COMP90054/2018 - AI Planning" ...'
```

It uses a csv file with the links to github/bitbucket/gitlab or any git server containing the code of each team, and downloads the submissions that have the *tag submission-contest* (see [driver.py](driver.py#lines-37)).

### Schedule in cron

We can then schedule it via **cron**. To do that, run the following command:

```shell
crontab -e
```

and introduce the following line into **cronfile** (change *username* appropriately)

```shell
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command

* * * * *  /usr/bin/env > /home/username/cron-env
```

Now you can test the command you want to schedule by running

```shell
./run-as-cron /home/username/cron-env "<command>"
```

This will run you command with the same environment settings as cron jobs do. If the command succeeds, then you can set up your command now.

### Setting up cron

Run the following command:

```bash
crontab -e
```

Remove the line you introduced before and introduce the following line:

```bash
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command

01 00 * * * python driver.py --username xxx --password xxx --cron-script-folder ''  --dest-www '' --teams-server-folder '' --teams-server-url xxx --tournament-cmd ''
```

Now your script will run every midnight at 00:01