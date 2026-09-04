#!/usr/bin/env bash
# assumes deploy.sh has already run adjacent to this file

set -ex
thisdir="$(cd "$(dirname "$0")" && pwd)"
cd "$thisdir"

sudo cf-agent -Kd -Ddata:install_ansible --bundle install_ansible
ansible --version

markerdir=$(mktemp -d)
trap 'sudo rm -rf "$markerdir"' EXIT
marker="$markerdir/marker"

# The playbook touches a marker file so we can tell that it actually ran
mkdir -p playbooks
cat >playbooks/playbook.yaml <<EOF
- hosts: all
  gather_facts: false
  tasks:
    - name: Create marker file
      ansible.builtin.file:
        path: $marker
        state: touch
EOF
cfbs --non-interactive add ./playbooks/

# Answers are path, condition, ifelapsed and whether to add more playbooks.
# The delimiter is quoted so that $(sys.inputdir) is left for cf-agent to expand.
rm -rf run-ansible-playbooks
cfbs input run-ansible-playbooks <<'EOF'
$(sys.inputdir)/services/cfbs/playbooks/playbook.yaml
any
5
no
EOF

cfbs build
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
