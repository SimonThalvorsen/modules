Promise type for editing values inside `yaml` files.

Edits are applied as small text splices on the original lines, so comments, key order, quoting style and formatting of everything not touched by the promise are preserved.

## Promiser

Path to the YAML file to edit. It must have a `.yaml` or `.yml` extension and must already contain YAML content.
Creating the file is a job for a `files:` promise.

## Attributes

| Name        | Type     | Required                     | Description                                        |
| ----------- | -------- | ---------------------------- | -------------------------------------------------- |
| `filter`    | `string` | yes                          | jq-like path to the node(s) to operate on          |
| `operation` | `string` | yes                          | One of `set`, `present` or `absent`                |
| `value`     | `string` | for `set` and `present`      | A scalar value                                     |

### Operations

All operations describe a desired state, so running a promise again once it is kept changes nothing.

- `set`: The key or item has `value`. Creates the key if it's missing (its parent must exist) or replaces the current value, including nested content.
  The quoting style of an existing value (plain, single or double quoted) is kept.
- `present`: The sequence at `filter` contains `value`. Appends it if it's missing.
- `absent`: Without `value`, the key(s) or item(s) at `filter` don't exist.
  With `value`, the sequence at `filter` doesn't contain `value`.

Sequence items are matched by content, not by position: use `value`, or `select()` for sequences of mappings.
`absent` on a plain index like `.hosts[1]` is rejected, since the next run would remove whatever moved into that position.

`true`, `false`, `null` and numbers are written as-is, so `value => "false"` writes a boolean.
Values that would be misread (e.g. `no`, `on`, `22:22`, or anything containing `: `) are quoted.

### Filter syntax

| Syntax                         | Meaning                                                   |
| ------------------------------ | --------------------------------------------------------- |
| `.a.b.c`                       | Key access                                                |
| `.a["b.c"]`                    | Quoted key access (keys with dots, spaces, etc.)          |
| `.a[1]`, `.a[-1]`              | Sequence index (negative counts from the end)             |
| `.a[]`                         | Every item of a sequence                                  |
| `.a[] \| select(.b == "x")`    | Items where `.b` equals a string, number, `true`, `false` or `null` |
| `... \| .c`                    | Continue from each selected item                          |

A filter can match several nodes (e.g. `.hosts[].port`); the operation is applied to all of them.
A `select()` that matches nothing is kept.

## Examples

Given `/etc/netplan/01-netcfg.yaml`:

```yaml
# This file is managed by the network team
network:
  ethernets:
    eth0:
      dhcp4: true
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4 # old secondary
```

the policy

```cfengine3
bundle agent main
{
  yaml:
    "/etc/netplan/01-netcfg.yaml"
      filter => ".network.ethernets.eth0.dhcp4",
      operation => "set",
      value => "false";

    "/etc/netplan/01-netcfg.yaml"
      filter => ".network.ethernets.eth0.nameservers.addresses",
      operation => "absent",
      value => "8.8.4.4";

    "/etc/netplan/01-netcfg.yaml"
      filter => ".network.ethernets.eth0.nameservers.addresses",
      operation => "present",
      value => "1.1.1.1";
}
```

results in:

```yaml
# This file is managed by the network team
network:
  ethernets:
    eth0:
      dhcp4: false
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
```

Items in a sequence of mappings are found with `select()`, e.g. to update a container image in a Kubernetes deployment:

```cfengine3
    "/srv/k8s/shop.yaml"
      filter => '.spec.template.spec.containers[] | select(.name == "app") | .image',
      operation => "set",
      value => "registry.example.com/shop:1.5.0";
```

## Limitations

This module ships its own minimal YAML parser (`yaml_lite.py`) and does not depend on PyYAML.
It only understands a subset of YAML:

- Block mappings, block sequences, plain/quoted scalars and comments are supported
- Block scalars (`|` / `>`), flow collections (`{...}` / `[...]`), anchors, aliases and tags are not supported
- Only scalar values can be written; nested structures can not be created with `value`
- `set` does not create missing parents, only the last key in the filter

## Tests

`tests/*.cf` are self-contained policies. With the module installed, run them as root with `cf-agent -KIf <file>.cf`; each prints `Pass` or `FAIL`.

## Authors

This software was created by the team at [Northern.tech](https://northern.tech), with many contributions from the community.
Thanks everyone!

## Contribute

Feel free to open pull requests to expand this documentation, add features, or fix problems.
You can also pick up an existing task or file an issue in [our bug tracker](https://northerntech.atlassian.net/).

## License

This software is licensed under the MIT License. See LICENSE in the root of the repository for the full license text.
