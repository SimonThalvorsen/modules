#!/usr/bin/env bash
# assumes deploy.sh has already run adjacent to this file

set -ex
thisdir="$(cd "$(dirname "$0")" && pwd)"
cd "$thisdir"

sudo cf-agent -Kd -Ddata:install_ansible --bundle install_ansible
ansible --version

markerdir=$(mktemp -d)
marker="$markerdir/marker"
playbookdir=$(mktemp -d)

# The tests share one project, so put it back the way we found it.
cleanup() {
  sudo rm -rf "$markerdir" "$playbookdir"
  cfbs --non-interactive remove ansible-playbook-dispatcher || true
  rm -rf ansible-playbook-dispatcher
}
trap cleanup EXIT

# The playbook touches a marker file so we can tell that it actually ran.
# It is written outside the project on purpose, so 'cfbs input' has to copy it in.
cat >"$playbookdir/playbook.yaml" <<EOF
- hosts: all
  gather_facts: false
  tasks:
    - name: Create marker file
      ansible.builtin.file:
        path: $marker
        state: touch
EOF

# Answers are path, condition, ifelapsed and whether to add more playbooks.
# The delimiter is unquoted so that bash expands the temporary playbook path.
rm -rf ansible-playbook-dispatcher
cfbs input ansible-playbook-dispatcher <<EOF
$playbookdir/playbook.yaml
any
5
no
EOF

# The playbook should have been copied in next to input.json
if [ ! -f ansible-playbook-dispatcher/playbook.yaml ]; then
  echo "expected 'cfbs input' to copy the playbook into the project"
  exit 1
fi

cfbs build

# ... and shipped with the policy set, under the module's own directory
built=out/masterfiles/services/cfbs/modules/ansible-playbook-dispatcher/playbook.yaml
if [ ! -f "$built" ]; then
  echo "expected 'cfbs build' to ship the playbook as '$built'"
  exit 1
fi

sudo cfbs install
sudo cf-agent -Kf update.cf
sudo cf-agent -KI | tee log
if grep 'error:' log; then
  grep 'error:' log
  exit 1
fi

if [ ! -f "$marker" ]; then
  echo "expected the playbook to create '$marker'"
  exit 1
fi
