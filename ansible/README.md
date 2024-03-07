Ansible Playbook `deploy_n2t_site`
==================================

The `deploy_n2t.yaml` ansible playbook works in consort with the UC3 puppet module
[`uc3_ezid_n2t`](https://github.com/CDLUC3/uc3-ops-puppet-modules/tree/main/modules/uc3_ezid_n2t)
to perform end-to-end deployment of the n2t service on AWS EC2 hosts.


### What it Does

- Clone n2t repository into deployment directory `/ezid/n2t`
- Install `n2t` app into virtual environment at `/ezid/n2t/venv`.
- Post site configuration data (`unit.json`) into nginx-unit config api.


### Usage

Execute this playbook on the localhost as user `ezid`:
```
cd ~/install/n2t
export ANSIBLE_STDOUT_CALLBACK=debug

ansible-playbook -i hosts deploy_n2t.yaml -CD
ansible-playbook -i hosts deploy_n2t.yaml
```

By default the playbook clones the `main` branch of the `n2t`
repository into the deployment directory.  To Deploy a specific version of the
n2t application, supply the version number (git tag) on the command line as
variable `n2t_version`:
```
ansible-playbook -i hosts deploy_n2t_site.yaml -e n2t_version=0.0.2
```


### Prereqs (deployed by puppet)

- nginx unit rpms:
  - unit
  - unit-devel
  - unit-python311

- python3.11 rpms from Amzn repo:
  - python3.11
  - python3.11-libs
  - python3.11-setuptools
  - python3.11-pip
  - python3.11-tkinter

- systemd dropin file for `unit.service`.  This provides:
  - service runs as group `ezid`
  - pid file group ownership as `ezid`
  - log file group ownership as `ezid`
  - unit service unix socket writable by `ezid`

- ansible binaries installed local to ezid user using `pip3.11`.



### Debugging

To retrieve the current unit config object, run this curl as user `ezid`:
```
curl --unix-socket /var/run/unit/control.sock http://localhost/config
```

To check the status of the Nginx Unit service:
```
sudo cdlsysctl status unit
```
