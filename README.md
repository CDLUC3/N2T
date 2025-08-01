# N2T Python Implementation

N2T is an identifier scheme resolver. 

Its role is to redirect clients to the registered handler for an identifier 
scheme. The handler is expected to continue interaction with the client for 
identifier resolution.

## Manual Deploy on Amazon Linux 2023

The steps to deployment are broadly:

1. Setup Nginx Unit as the web server
2. Install the n2t python application
3. Configure the n2t application with identifier schem information

### Setup Nginx Unit as the web server

On server instance:

Given the YUM repository description file `unit.repo`:
```
[unit]
name=unit repo
baseurl=https://packages.nginx.org/unit/amzn/2023/$basearch/
gpgcheck=0
enabled=1
```

Add the repository and install Nginx `unit`: 
```
sudo yum update
sudo yum install yum-utils
sudo /usr/bin/yum-config-manager --add-repo unit.repo
sudo yum update
sudo yum install unit
sudo yum install unit-devel unit-jsc17 unit-python311 unit-wasm
sudo cdlsysctl start unit
```

Note: The service is installed as disabled and needs to be enabled, but 
`cdlsysctl` doesn't allow that so needs to be done by an administrator, e.g.:
```
sudo systemctl enable unit
```

Is the service running?
```
sudo cdlsysctl status unit
● unit.service - NGINX Unit
     Loaded: loaded (/usr/lib/systemd/system/unit.service; disabled; preset: disabled)
     Active: active (running) since Wed 2024-02-28 04:32:23 PST; 4s ago
   Main PID: 1893665 (unitd)
      Tasks: 3 (limit: 1055)
     Memory: 5.7M
        CPU: 16ms
     CGroup: /system.slice/unit.service
             ├─1893665 "unit: main v1.32.0 [/usr/sbin/unitd --log /var/log/unit/unit.log --pid /var/run/unit/unit.pid --no-daemon]"
             ├─1893667 "unit: controller"
             └─1893668 "unit: router"
```

To enable access to `unit` by the `ezid` user, it is necessary to override the 
default systemd startup for unit. This is done with an `override.conf` file in
`/etc/systemd/system/unit.service.d`:
```
[Service]
Environment="UNITD_OPTIONS=--log /var/log/unit/unit.log --pid /var/run/unit/unit.pid --user ezid --group ezid"
Group=ezid
ExecStartPost=/usr/bin/sh -c 'sleep 3; chmod 660 /var/run/unit/control.sock; chmod 640 /var/log/unit/*.log'
```

Show the current `unit` configuration:
```
$ curl -X GET --unix-socket /var/run/unit/control.sock http://localhost/config/
{
	"listeners": {},
	"routes": [],
	"applications": {}
}
```

### Install the n2t python application

Setup python and application. Installing the application is done by cloning from 
the GitHub repository. From the application home (i.e. `/ezid` on UC3 systems):

```
git clone https://github.com/CDLUC3/n2t.git
cd n2t
python3.11 -m venv venv
source venv/bin/.activate
python --version
  Python 3.11.6
python -m pip install -U pip
python -m pip install -e .
```

Run the `n2t` cli to verify the application is installed:

```
$  n2t
Usage: n2t [OPTIONS] COMMAND [ARGS]...

  Management commands for N2T.

  This script is used for initializing the JSON representation of scheme
  records from the original YAML and creating or updating the sqlite store
  used by the resolver application.

Options:
  -c, --config FILE
  --help             Show this message and exit.

Commands:
  info       Print application version and basic status.
  loaddb     Load or update the scheme database.
  yaml2json  Generate or update JSON record from YAML source.
```

### Configure the n2t application with identifier scheme information

Before operation, the N2T application scheme database must be initialized. This 
process creates an sqlite database containing the scheme records to support 
resolution. The scheme records are loaded from the JSON sources, and the 
database will need to be updated when the JSON sources are modified.

The N2T application is configured using a `.env` file. The available properties
include:

| Key                          | Default                          | Description                                                               |
|------------------------------|----------------------------------|---------------------------------------------------------------------------|
| `N2T_HOST`                   | `localhost`                      | Address to listen when running in dev mode.                               |
| `N2T_PORT`                   | `8000`                           | Port to listen on when running in dev mode.                               |
| `N2T_PROTOCOL`               | `http`                           | Protocol to listen on (`http` or `https`).                                |
| `N2T_DB_CONNECTION_STRING`* | `sqlite:///BASE/data/n2t/sqlite` | SQLAlchemy connection string (sqlite preferred).                          | 
| `N2T_JSON_DIR`*             | `BASE/schemes`                   | Folder where the scheme definitions are located.                          |
| `N2T_STATIC_DIR`*           | `BASE/static`                    | Folder from where static content is served (styles, images, scripts).     | 
| `N2T_TEMPLATE_DIR`*         | `BASE/templates`                 | Folder from which templated content is served.                            |
| `N2T_ENVIRONMENT`            | `development`                     | A human readable label for the service (development, staging, production) | 

*: Default folder locations are relative to the `n2t` folder in the cloned repository. 

A typical configuration file for a staging environment will be:
```
N2T_DB_CONNECTION_STRING="sqlite:///data/n2t.sqlite"
N2T_JSON_DIR="schemes"
N2T_ENVIRONMENT="staging"
```

Those settings indicate the name of the environment "staging", that the JSON
scheme definitions are in the folder `schemes` and the application
database is `data/n2t.sqlite`. The folders are relative to the location where
the `n2t` command is run. These properties may also use absolute paths, for
example:

```
N2T_DB_CONNECTION_STRING="sqlite:////ezid/var/n2t.sqlite"
N2T_JSON_DIR="/ezid/n2t/schemes"
```

Any of the settings are overridden by an equivalent named environment variable
if set.

If the `schemes` folder is not present it needs to be created from the 
legacy N2T prefixes file:

```
wget "https://legacy-n2t.n2t.net/e/n2t_full_prefixes.yaml"
n2t yaml2json
```

The application database may be created and populated when the JSON scheme
records are available:

```
cd /ezid/n2t
mkdir -p data
n2t loaddb
```

To verify setup, use the `info` command. The output should be something like:

```
$ n2t info
{
  "version": "0.5.0",
  "environment": "development",
  "status": "initialized",
  "description": "n2t_full_prefixes",
  "created": "2024-03-06T16:01:43.245204",
  "schemes": {
    "total": 2774,
    "valid": 1596
  }
}
```

## Managing Scheme Records

## Local Development

Clone the repository:

```
git clone https://github.com/CDLUC3/N2T.git
cd N2T
```

Initialize a virtual environment:

```
uv venv .venv
```

Install the dependencies (includes the dev group dependencies):

```
uv sync
```

Create a data folder and generate the resolver database:

```
mkdir data
uv run n2t -c dev-config.env loaddb
```

Run the local server:

```
uv run n2t -c dev-config.env serve
```

**Hint:** Running `source .venv/bin/activate` will load the virtual environment to the current shell, so you can run the `n2t` commands without `uv run`, e.g.:

```
source .venv/bin/activate
n2t --help
Usage: n2t [OPTIONS] COMMAND [ARGS]...

  Management commands for N2T.

  This script is used for initializing the JSON representation of scheme
  records from the original YAML and creating or updating the sqlite store
  used by the resolver application.

Options:
  -c, --config FILE
  --help             Show this message and exit.

Commands:
  info       Print application version and basic status.
  loaddb     Load or update the scheme database.
  serve
  yaml2json  Generate or update JSON record from YAML source.
```

The virtual environment can be unloaded with `deactivate`


### Nginx Unit on OS X (silicon)

```
brew install nginx/unit/unit
brew install unit-python3

/opt/homebrew/opt/unit/bin/unitd --no-daemon
```

Control socket: `/opt/homebrew/var/run/unit/control.sock`
Log file: `/opt/homebrew/var/log/unit/unit.log `

```
export UNIT_CONTROL="/opt/homebrew/var/run/unit/control.sock"
```

Set configuration:
```
curl -X PUT --data-binary @unit.conf --unix-socket ${UNIT_CONTROL} http://localhost/config/applications/n2t"
```