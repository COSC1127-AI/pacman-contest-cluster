# Pacman Contest Dashboard

This package will allow to display an interactive dashboard against the results of contests.

## Set up

The dashboard uses [streamlist](https://streamlit.io/), so this must be installed:

```shell
$ pip install streamlit plotly seaborn
```

Then, update the information in `config.py` with the correct data for your system. For example:

```shell
STATS_FOLDER = ('/data/www/stats-archive')
DEPLOYED_URL = 'http://115.146.95.253/preliminary-contest'
ORGANIZER = 'UNIMELB - COMP90054/2020'
```

The `STATS_FOLDER` variable should point to the stats folder containing the JSON files produced by the pacman contest cluster script.

The `DEPLOYED_URL` variable should point to the exact URL where the www information produced by the pacman contest cluster script is hosted.

## Run

To run the web-server serving the dashboard,  open a `screen` or `tmux` virtual terminal and run the server as follows:

```shell
$ streamlit run dashboard.py
```

The server will be listening on port 8501 by default. To change the port (e.g., when running more than one server):

``shell
$ streamlit run dashboard.py --server.port 8502
```

The reason to use `screen` or `tmux` is that this server will often be run in the remote cluster, so you want to keep running even when you disconnect.

## Unpacking logs and replays

The old version of the contest cluster script did not unpack the replays and logs that are needed for the dashboard server (they were just inside compressed `tar.gz` files).

To unpack them manually you can use the script `extras\process_www_dashboard.py` as follows:

1. Set the `DATA_URL` variable in the script to point to the root location where the web results for contests are stored; e.g.:

    ```shell
    DATA_URL = '/mnt/ssardina-pacman/cosc1125-1127-AI/www'
    ```

2. Make a backup of your www folder just tin case.
3. Run the script:

    ```shell
    python3 process_www_dashboard.py
    ```