#!/bin/sh
# Wrapper choosing the Python interpreter that runs ansible_promise.py.
#
# The [install-ansible](https://build.cfengine.com/modules/install-ansible/)
# build module installs Ansible with `pipx install --global`, which places it in
# an isolated virtualenv under /opt/pipx/venvs. The system interpreter cannot
# import Ansible from there, so prefer the virtualenv's interpreter and fall
# back to /usr/bin/python3 for hosts where Ansible was installed some other way.

module="$(dirname "$0")/ansible_promise.py"

can_import_ansible() {
  if [ ! -x "$1" ]; then
    return 1
  fi
  "$1" -c "import ansible" >/dev/null 2>&1
}

# The ansible command is a Python console script, so its shebang names the
# interpreter it was installed for. Reading it finds the right virtualenv no
# matter where pipx put it, and whether ansible or ansible-core was installed.
ansible_bin="$(command -v ansible)"
if [ -n "$ansible_bin" ]; then
  python="$(sed -n '1s|^#! *\([^ ]*\).*|\1|p' "$ansible_bin")"
  if can_import_ansible "$python"; then
    exec "$python" "$module" "$@"
  fi
fi

# Default locations, in case the command above is missing from the PATH that
# cf-agent inherited.
for python in /opt/pipx/venvs/ansible/bin/python /opt/pipx/venvs/ansible-core/bin/python; do
  if can_import_ansible "$python"; then
    exec "$python" "$module" "$@"
  fi
done

exec /usr/bin/python3 "$module" "$@"
