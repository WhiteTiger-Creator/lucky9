# Vaultwatch Database Node Restoration Runbook

Required known-good configuration for any database node left misconfigured by the Vaultwatch
sync automation. The automation provisioned itself with stray access and sudo paths that must be
cleared while the dbnode is reconfigured; the query-triage rollup is not restored until the host
matches this runbook.

## SSH access

The automation appended its own deploy key to root's `authorized_keys`, identified by the key
comment `dbnode-sync-automation`. Remove it: no entry carrying that comment may remain in
`/root/.ssh/authorized_keys`. The file also carries the ops on-call bastion key (comment
`ops-oncall@bastion`). That entry is legitimate and MUST survive this cleanup — remove the
offending line rather than truncating or rewriting the file, and leave the file at mode 0600.
Locking responders out of the dbnode is a misconfiguration, not a fix.

## Sudo configuration

The automation installed a temporary sudoers drop-in at `/etc/sudoers.d/dbnode-sync` granting
`svc-dbnode` passwordless root. Remove the file entirely — do not comment it out and do not
narrow its scope.

## Query-signing key permissions

The datastore query-signing key at `/app/secrets/db_signing.key` was left world-readable. The key
is still valid and the dbnode still needs it in place: keep the file, owned `root:root`, mode
`0600`.
