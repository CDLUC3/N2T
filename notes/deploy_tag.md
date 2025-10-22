# Deploying an N2T release

N2T is deployed using puppet. Puppet is setup to deploy only tagged references to the N2T source repository.

To create a tag, e.g. for release `0.11.0`:

```
git checkout main
git pull
git tag v0.11.0 -a -m "Make ark hyphens optional, CORS"
git push -u origin tag v0.11.0
```

## Stage deployment

The deployment procedure is to deploy the tag to the N2T stage environment and verify operation there.

If any changes are needed, the normal development cycle needs to be followed. This would ultimately result in a patch release which would be tagged as such (e.g. v0.11.1).

The N2T stage environment servers are:

```
uc3-ezidn2t-stg01.cdlib.org
uc3-ezidn2t-stg02.cdlib.org
```

To deploy to the stage environment, visit:

  https://github.com/CDLUC3/uc3-ops-puppet-hiera/blob/main/fqsn/uc3-ezid-n2t-stg.yaml

and edit the `project_revision` to match the desired tag name (e.g. `v0.11.0`).

Next, `ssh` to a stage server and deploy using puppet:

```
ssh n2t-stg1
sudo su - uc3puppet
uc3_pupapply.sh --exec
```

The `unit` service may show some latency in loading the new application. A restart of the python app can be forced without restarting the `unit` service by using the `unit` configuration endpoint:

```
curl -s -X GET --unix-socket /var/run/unit/control.sock http://localhost/control/applications/n2t/restart | jq '.'
{
  "success": "Ok"
}
```

Repeat the puppet and optional app restart for the other stage server.

## Production deployment

The process for deploying to production is the same except the `hiera` entry is located at:

  https://github.com/CDLUC3/uc3-ops-puppet-hiera/blob/main/fqsn/uc3-ezid-n2t-prd.yaml

and the N2T production environment servers are:

```
uc3-ezidn2t-prd01.cdlib.org
uc3-ezidn2t-prd02.cdlib.org
```
