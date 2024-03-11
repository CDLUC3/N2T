How to update n2t with ansible
==============================

These instructions are independant of puppet.  But if you do update n2t directly, please be
sure to post the new semantic version rev into puppet hiera files.


Quick Guide
-----------
```
cd install/n2t/
git --no-pager log --oneline -n 1
git fetch  origin --tags
git checkout 0.7.0rc2
cd ansible/
ansible-playbook -i hosts deploy_n2t.yaml -e n2t_version=0.7.0rc2 -CD
ansible-playbook -i hosts deploy_n2t.yaml -e n2t_version=0.7.0rc2
curl -v http://localhost:18880/
```


Full Example
============

Login as ezid user and update the deployment working tree:
```
agould@uc3-ezidn2t-prd02:~> sudo su - ezid
Last login: Mon Mar 11 15:21:25 PDT 2024 on pts/1
ezid@uc3-ezidn2t-prd02:15:27:16:~$ cd install/n2t/
ezid@uc3-ezidn2t-prd02:15:27:21:~/install/n2t$ git --no-pager log --oneline -n 1
8abdc90 (HEAD, tag: 0.0.0rc0) ansible: debugging playbook
ezid@uc3-ezidn2t-prd02:15:27:26:~/install/n2t$ git fetch  origin --tags
ezid@uc3-ezidn2t-prd02:15:27:57:~/install/n2t$ git tag
ezid@uc3-ezidn2t-prd02:15:28:40:~/install/n2t$ git checkout 0.7.0rc1
Previous HEAD position was 8abdc90 ansible: debugging playbook
HEAD is now at 951ddc2 Adjust sqlite db to use var folder
```



#### Review ansible usage in `ansible/README.md`:

```
ezid@uc3-ezidn2t-prd02:15:29:23:~/install/n2t$ cd ansible/
ezid@uc3-ezidn2t-prd02:15:32:49:~/install/n2t/ansible$ grep -A 20 Usage README.md 
### Usage

Execute this playbook on the localhost as user `ezid`:

   cd ~/install/n2t
   export ANSIBLE_STDOUT_CALLBACK=debug
   
   ansible-playbook -i hosts deploy_n2t.yaml -CD
   ansible-playbook -i hosts deploy_n2t.yaml


By default the playbook clones the `main` branch of the `n2t`
repository into the deployment directory.  To Deploy a specific version of the
n2t application, supply the version number (git tag) on the command line as
variable `n2t_version`:

   ansible-playbook -i hosts deploy_n2t_site.yaml -e n2t_version=0.0.2
```



#### Dryrun with appropreate **n2t_version**:
```
ezid@uc3-ezidn2t-prd02:15:46:48:~/install/n2t/ansible$ ansible-playbook -i hosts deploy_n2t.yaml -e n2t_version=0.7.0rc2 -CD

PLAY [all] *********************************************************************************************

TASK [Gathering Facts] *********************************************************************************
[WARNING]: Platform linux on host localhost is using the discovered Python interpreter at
/usr/bin/python3.11, but future installation of another Python interpreter could change the meaning of
that path. See https://docs.ansible.com/ansible-
core/2.16/reference_appendices/interpreter_discovery.html for more information.
ok: [localhost]

TASK [Clone n2t repo] **********************************************************************************
ok: [localhost]

TASK [Install n2t application] *************************************************************************
changed: [localhost]

TASK [Print unit.json contents] ************************************************************************
ok: [localhost] => {}

MSG:

{
    "access_log": {
        "path": "/var/log/unit/access.log"
    },
    "applications": {
        "n2t": {
            "callable": "app",
            "environment": {
                "N2T_SETTINGS": "/ezid/n2t/n2t/n2t-config.env"
            },
            "home": "/ezid/n2t/venv/",
            "module": "n2t.app",
            "path": [
                "/ezid/n2t/n2t"
            ],
            "type": "python 3.11",
            "working_directory": "/ezid/n2t/n2t"
        }
    },
    "listeners": {
        "*:18880": {
            "pass": "routes/n2t"
        }
    },
    "routes": {
        "n2t": [
            {
                "action": {
                    "pass": "applications/n2t"
                },
                "match": {
                    "uri": [
                        "/*"
                    ]
                }
            }
        ]
    }
}

TASK [Configure nginx unit] ****************************************************************************
skipping: [localhost]

PLAY RECAP *********************************************************************************************
localhost                  : ok=4    changed=1    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0   
```



#### Now deploy for reals:
```
ezid@uc3-ezidn2t-prd02:15:47:08:~/install/n2t/ansible$ ansible-playbook -i hosts deploy_n2t.yaml -e n2t_version=0.7.0rc2

PLAY [all] *********************************************************************************************

TASK [Gathering Facts] *********************************************************************************
[WARNING]: Platform linux on host localhost is using the discovered Python interpreter at
/usr/bin/python3.11, but future installation of another Python interpreter could change the meaning of
that path. See https://docs.ansible.com/ansible-
core/2.16/reference_appendices/interpreter_discovery.html for more information.
ok: [localhost]

TASK [Clone n2t repo] **********************************************************************************
ok: [localhost]

TASK [Install n2t application] *************************************************************************
changed: [localhost]

TASK [Print unit.json contents] ************************************************************************
ok: [localhost] => {}

MSG:

{
    "access_log": {
        "path": "/var/log/unit/access.log"
    },
    "applications": {
        "n2t": {
            "callable": "app",
            "environment": {
                "N2T_SETTINGS": "/ezid/n2t/n2t/n2t-config.env"
            },
            "home": "/ezid/n2t/venv/",
            "module": "n2t.app",
            "path": [
                "/ezid/n2t/n2t"
            ],
            "type": "python 3.11",
            "working_directory": "/ezid/n2t/n2t"
        }
    },
    "listeners": {
        "*:18880": {
            "pass": "routes/n2t"
        }
    },
    "routes": {
        "n2t": [
            {
                "action": {
                    "pass": "applications/n2t"
                },
                "match": {
                    "uri": [
                        "/*"
                    ]
                }
            }
        ]
    }
}

TASK [Configure nginx unit] ****************************************************************************
ok: [localhost]

PLAY RECAP *********************************************************************************************
localhost                  : ok=5    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
```


#### Validate the deployment:
```
ezid@uc3-ezidn2t-prd02:15:48:38:~/install/n2t/ansible$ curl -v http://localhost:18880/
* Host localhost:18880 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
*   Trying [::1]:18880...
* connect to ::1 port 18880 from ::1 port 38034 failed: Connection refused
*   Trying 127.0.0.1:18880...
* Connected to localhost (127.0.0.1) port 18880
> GET / HTTP/1.1
> Host: localhost:18880
> User-Agent: curl/8.5.0
> Accept: */*
> 
< HTTP/1.1 200 OK
< content-length: 1286
< content-type: text/html; charset=utf-8
< Server: Unit/1.32.0
< Date: Mon, 11 Mar 2024 22:50:02 GMT
< 
<!DOCTYPE html>
<html lang="en">
<head>
    
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0,user-scalable=0"/>
    <title>N2T Home</title>
    <link href="/static/style.css" rel="stylesheet">
    
    
    <script type="module" src="https://unpkg.com/gh-corner-wc/gh-corner.js?module">
    </script>
    
</head>
<body>

<gh-corner user="CDLUC3" repo="N2T" position="right"></gh-corner>
<header>
    
        <p><a href="/">N2T</a> service </p>
    
</header>
<main>
    
    <h1>N2T - Identifier Resolution Service</h1>
    <div>
    <p><code>N2T</code> is an identifier scheme resolver that given a provided identifier,
        matches it to an identifier scheme definition. Depending on the form of the request,
        a successful match will either redirect to the registered target or present
        information about the matched definition.</p>
    <p>Identifiers take the form:</p>
    <pre>
scheme:prefix/value
    </pre>
        <p>The service API description is available at <a href="/api">/api</a>.</p>
        <p>The registered schemes are listed on the <a href="/_schemes.html">schemes page</a>.</p>
    </div>

</main>
<footer>N2T, development environment, version 0.7.0</footer>



</body>
* Connection #0 to host localhost left intact
</html>
```



