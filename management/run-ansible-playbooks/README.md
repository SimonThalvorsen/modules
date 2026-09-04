This module enables the running of Ansible playbooks in masterfiles.
Playbook paths are specified based on input from Build in Mission Portal or `cfbs input`.

**Note:** Each playbook must be stored in masterfiles.
You can achieve this by copying them into a subdirectory in your cfbs project (e.g. `playbooks/`), followed by:

```
$ cfbs add ./playbooks/
WARNING: Did not find any bundles to add to bundlesequence
Added module: ./playbooks/
```

Don't mind the warning.
After building and deploying your project the playbooks will end up in `$(sys.inputdir)/services/cfbs/playbooks/`.

**Note:** The playbooks will be distributed and run locally with root-privilege (uid=0).

**Note:** Ansible must be installed on the hosts.
You can use a module to install Ansible *_(See [install-ansible](https://build.cfengine.com/modules/install-ansible/) build module)_*:
```
cfbs add install-ansible
```

**Usage:**
- `path` - The playbook path.
  Must be absolute, e.g. `$(sys.inputdir)/services/cfbs/playbooks/playbook.yaml`.
- `condition` - Condition for running the playbook.
  Use a class expression (e.g., `linux|bsd`).
  Defaults to `any`.
- `ifelapsed` - Minimum number of minutes between each run.
  Defaults to 5 minutes.

## Contribute

Feel free to open pull requests to expand this documentation, add features or fix problems.
You can also pick up an existing task or file an issue in [our bug tracker](https://northerntech.atlassian.net/projects/CFE).

## License

This software is licensed under the MIT License. See LICENSE in the root of the repository for the full license text.
