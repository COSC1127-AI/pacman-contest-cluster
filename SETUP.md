# SETUP

We need to configure the machine running the central script, and the workers machines running pacman single games.

## Worker machines

* Python 3.x with standard libraries.
* zip/unzip (to pack and unpack submissions and files for transfer): `sudo apt-get install -y unzip zip vim`
* Set the SSH server to accept as many connections as you want to run concurrently. This is done by changing option `MaxStartups` in file `/etc/ssh/sshd_config`. By default `sshd` has up to 10 connections.
  * For example, set `MaxStartups 100:30:100` to accept up to 100 simultaneous connections. Remember to restart the ssh server: `sudo service sshd restart`
  * For more info on this, see issue [#26](https://github.com/COSC1127-AI/pacman-contest-cluster/issues/26).
* Cluster should have all the Python and Unix packages to run the contest. For example, in the [NeCTAR cluster](https://ardc.edu.au/services/nectar-research-cloud/):

    ```shell
    $ sudo apt-get update
    $ sudo apt-get install python-pip zip unzip vim
    $ pip install --upgrade pip

    $ pip install -r https://raw.githubusercontent.com/COSC1127-AI/pacman-contest-cluster/main/requirements-workers.txt
    ```

Finally, you need to locally install the **cluster manager module** located [here](https://github.com/ssardina-teaching/cluster-manager). Follow instructions on that repository. This is a generic framework to delegate jobs to workers and collect their outputs.

### Extras

Many students benefit from the availability other tools, like [TensorFlow](https://www.tensorflow.org/), [scikit-learn](http://scikit-learn.org/), [neat-python](https://github.com/CodeReclaimers/neat-python).

A file `requirements-workers-extras.txt` is provided for those extras:

```shell
$ pip install -r https://raw.githubusercontent.com/COSC1127-AI/pacman-contest-cluster/main/requirements-workers-extras.txt
```

Also, if students want to use planners to solve pacman PDDL models for their solutions, copy any planner to `/usr/local/bin` in each host. For example, in the NeCTAR cluster:

```shell
sudo cp planners/ff /usr/local/bin/.
```

You can get some of the FF planners [here](https://github.com/ssardina-planning/planners).

## Central Script Host

In the **local machine** (e.g., your laptop) that will dispatch game jobs to the cluster via the `pacman_contest_cluster.py` script:

* unzip & zip (to pack and unpack submissions and files for transfer): `sudo apt-get install -y unzip zip`
* Python >= 3.6 with:
  * `setuptools`
  * `iso8601`
  * `pytz`
  * `paramiko`

  Simply run: `pip install -r requirements.txt --user`

In addition to that:

* Each submission is a `.zip` file or a directory; all within some folder (e.g., `teams/`)
  * The player agent should be in the _root_ of the team zip file or team directory.
  * Submission file/dir name will be used as the team name.
* The cluster to be used is specified with option `--workers-file-path`, to point to a `.json` file containing the workers available (including no of cores, IP, username, password, and private key file if needed)

Hence, the user of this system must provide:

* _private keys_ for cluster (if needed; specified in `workers.json`).
* Directory with set of zip submission files; see above (for option `--teams`)
* `workers.json`: listing the cluster setting to be used (for option `--workers-file-path`)

## Web-server configuration

To host the contest ladders, install Apache web-server first:

```shell
$ sudo apt-get install apache2
```

The default Ubuntu document root is `/var/www/html`, so it first serve  `/var/www/html/index.html` when accessing the server.

A very easy way to serve multiple folders elswhere is to create symbolic links from there to the root of your site. For example:

```shell
$ sudo ln -s /home/ssardina/ssardina-volume/cosc1125-1127-AI/AI21/p-contest/www/ /var/www/html/prelim
```

To set-up the web-page for preliminary contests at `http://<ip server>/prelim`

To allow directory listing and configure per directory, first disable listig by default by changing `/etc/apache/apache2.conf` as follows:

```xml
<Directory /var/www/>
        #Options Indexes FollowSymLinks
        Options FollowSymLinks
        AllowOverride all
        Require all granted
</Directory>
```

The key here is to disable out `Indexes` and `FollowSymLinks` by default, and allow overriding via `.htaacess` files with `AllowOverride all`.

Then, to allow listing in a folder, add `.htaccess` file (permission `0755`) there with:

```plaintext
Options Indexes FollowSymLinks
IndexOptions FancyIndexing FoldersFirst NameWidth=* DescriptionWidth=*
```

> [!NOTE]
> One could install the lighter Lighttpd web-server, but it happens that it does not use `.htaccess` so it is more difficult to set-up per directory listing.
