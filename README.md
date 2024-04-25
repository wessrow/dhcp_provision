## NetBox

Defaults to use netbox reachable of docker-network via DNS (netbox:8080)

This can be overwritten with the env-var NETBOX_HOST

When provisioning a device, NetBox will be queried for the discovered serial (from 'show version')

## Required env-vars:

- TFTP_SERVER
- NB_API_TOKEN

## Optional env-vars:

- SFTP_SERVER
- SFTP_USER
- SFTP_PASSWORD
