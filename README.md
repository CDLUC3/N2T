# N2T Python Implementation

This is a reimplementation of N2T using python.

N2T is an identifier scheme resolver. Its role is to redirect clients to the 
registered handler for an identifier scheme. The handler is expected to 
continue interaction with the client for identifier resolution.


## Manual Deploy on Amazon Linux 2023

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

Note: The service is installed as disabled and it needs to be enabled unit, but 
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




Setup python and application:

```
mkdir n2t
cd n2t
python3.11 -m venv venv
source venv/bin/.activate
python --version
  Python 3.11.6
python -m pip install -U pip
```



## Developer Setup

```
git clone https://github.com/CDLUC3/N2T.git
cd N2T
mkvirtualenv n2t
poetry install
```

Running micron2t:

First gather the prefixes and generate the JSON master file:
```
wget -O data/prefixes.yaml https://n2t.net/e/n2t_full_prefixes.yaml 
n2t data/prefixes.yaml tojson -d micron2t/data/prefixes.json
```

Then fire up the N2T web service:
```
cd micron2t
uvicorn --reload main:app
```

Deployment to Deta is through a GH Action. Available as a Deta micro at https://rslv.deta.dev

## `micron2t`

Provides API documentation at `/docs`

`/` Returns a list of supported prefixes

`/{identifier}` Returns information about the identifier and other behavior.

If the `identifier` has no colon, then it is treated as a prefix and prefix metadata is returned in JSON.

If the `identifier` has a colon and the pattern matches, then a redirect response is returned unless a request is made
with `Accept: application/json;profile=https://rslv.xyz/info`, in which case information about the intended action 
is returned.


[^1]: As of 2021-12-07


## Resolution

The process of resolution returns either a resource or a location from which the resource can be retrieved. N2T does not hold identified resources, and so will only provide the registered location of the resource.



