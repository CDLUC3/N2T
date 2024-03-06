Ansible Playbook `deploy_arksorg_site`
=====================================

The `deploy_arksorg_site.yaml` ansible playbook works in consort with the UC3 puppet module
[`uc3_ezid_arks`](https://github.com/CDLUC3/uc3-ops-puppet-modules/tree/main/modules/uc3_ezid_arks)
to perform end-to-end deployment of the arksorg-site service on AWS EC2 hosts.


### What it Does

- Clone arksorg-site repository into deployment directory `/ezid/arksorg`
- Install ruby gems from arks.github.io Gemfile
- Run `bundle exec jekyll` to build arks.github.io site
- Install python dependencies for `resolver` app into virtual environment at `/ezid/arksorg/venv`.
- Post site configuration data (`unit.josn`) into nginx-unit config api.


### Usage

Execute this playbook on the localhost as user `ezid`:
```
cd ~/install/arksorg-site
export ANSIBLE_STDOUT_CALLBACK=debug

ansible-playbook -i hosts deploy_arksorg_site.yaml -CD
ansible-playbook -i hosts deploy_arksorg_site.yaml
```

By default the playbook clones the `main` branch of the `arksorg-site`
repository into the deployment directory.  To Deploy a specific version of the
arksorg application, supply the version number (git tag) on the command line as
variable `arksorg_version`:
```
ansible-playbook -i hosts deploy_arksorg_site.yaml -e arksorg_version=0.0.2
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

- ruby and bundler installed local to ezid user.  These are for building `arks.github.io` content.


### Debugging

To retrieve the current unit config object, run this curl as user `ezid`:
```
curl --unix-socket /var/run/unit/control.sock http://localhost/config
```

To check the status of the Nginx Unit service:
```
sudo cdlsysctl status unit
```
