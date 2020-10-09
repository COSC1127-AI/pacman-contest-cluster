```
pip3 install streamlit
```

Change this information in `app.py`

```
DATA_URL = ('/data/www/stats-archive')
DEPLOYED_URL = 'http://115.146.95.253'
ORGANIZER = 'UNIMELB - COMP90054/2020'
```

open a `screen` window and run the server.


```
streamlit run app.py
```

In order to fix the old `www` that didn't unpack the replays and logs, Change file in `extras\process_www_dashboard.py`:

```

DATA_URL = '/home/nirlipo/contest-2020/www'
```

MAKE A BACKUP OF YOUR WWW folder using tar!!


and then go to the extras folder and run

```
python3 process_www_dashboard.py
```