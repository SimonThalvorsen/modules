Promise type for editing values inside `yaml` files.

Edits are applied as small text splices on the original lines, so comments, key order, quoting style and formatting of everything not touched by the promise are preserved.

## Promiser

Path to the YAML file to edit.

A missing file is treated as an empty document: `set` and `present` create it, `absent` leaves it missing.
Like with `files:` promises, missing parent directories are created.
New files get mode 0600 and new directories 0700, the same as `files:` promises create them with. To use other permissions, create the file with a `files:` promise and `perms` first.

## Attributes

| Name        | Type     | Required                     | Description                                        |
| ----------- | -------- | ---------------------------- | -------------------------------------------------- |
| `filter`    | `string` | yes                          | jq-like path to the node(s) to operate on          |
| `operation` | `string` | yes                          | One of `set`, `present` or `absent`                |
| `value`     | `string` | depends on `operation`       | A scalar value, see [Operations](#operations)      |

### Operations

All operations describe a desired state, so running a promise again once it is kept changes nothing.

- `set`: The key or item has `value`. Creates the key if it's missing, along with any missing parent keys, or replaces the current value, including nested content.
  The quoting style of an existing value (plain, single or double quoted) is kept.
- `present`: The sequence at `filter` contains `value`. Appends it if it's missing, creating the sequence (and parent keys) if needed.
  Without `value`, on a filter ending in `[] | select(.key == value)`, a sequence of mappings contains an item matching the select.
  If none does, `- key: value` is appended, and other fields can then be set through the same `select()`:

  ```cfengine3
  "/etc/app/users.yaml"
    filter => '.users[] | select(.name == "carol")',
    operation => "present";

  "/etc/app/users.yaml"
    filter => '.users[] | select(.name == "carol") | .shell',
    operation => "set",
    value => "/bin/zsh";
  ```
- `absent`: Without `value`, the key(s) or item(s) at `filter` are removed, including anything nested under them.
  With `value`, every item equal to `value` is removed from the sequence at `filter`; the rest of the sequence is kept.
  Parents are never removed, even if they end up empty.

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
Missing parents are only created for plain key paths like `.a.b.c`, not through `[]`, indexes or `select()`.

## Example

Given `/etc/netplan/01-netcfg.yaml`:

```yaml
# Managed by cfengine
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      addresses:
        - 192.168.1.10/24
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

the policy

```cfengine3
bundle agent main
{
  vars:
    "netplan" string => "/etc/netplan/01-netcfg.yaml";
    "eth0" string => ".network.ethernets.eth0";

  yaml:
    "$(netplan)"
      filter => "$(eth0).dhcp4",
      operation => "set",
      value => "false";

    "$(netplan)"
      filter => "$(eth0).addresses",
      operation => "absent",
      value => "192.168.1.10/24";

    "$(netplan)"
      filter => "$(eth0).addresses",
      operation => "present",
      value => "10.0.0.5/24";

    "$(netplan)"
      filter => "$(eth0).nameservers.addresses",
      operation => "absent",
      value => "8.8.4.4";

    "$(netplan)"
      filter => "$(eth0).nameservers.addresses",
      operation => "present",
      value => "1.1.1.1";
}
```

results in:

```yaml
# Managed by cfengine
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: false
      addresses:
        - 10.0.0.5/24
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
```

## Limitations

This module ships its own minimal YAML parser (`yaml_lite.py`) and it only understands a subset of YAML:

- Block mappings, block sequences, plain/quoted scalars and comments are supported
- Block scalars (`|` / `>`), anchors, aliases and tags are not supported
- Flow collections are not supported. These are the compact, JSON-like way of writing sequences and mappings on one line:

  ```yaml
  addresses: [10.0.0.5/24, 10.0.0.6/24] # flow sequence
  tls: { enabled: true, port: 443 }     # flow mapping
  ```

  instead of the block style this module understands:

  ```yaml
  addresses:
    - 10.0.0.5/24
    - 10.0.0.6/24
  tls:
    enabled: true
    port: 443
  ```

  A flow collection is read as a single string: `set` can replace it, but `present`/`absent` with `value` fail since it isn't a sequence, and keys inside it can not be reached by `filter`.
- Only scalar values can be written; nested structures can not be created with `value`

## Authors

This software was created by the team at [Northern.tech](https://northern.tech), with many contributions from the community.
Thanks everyone!

## Contribute

Feel free to open pull requests to expand this documentation, add features, or fix problems.
You can also pick up an existing task or file an issue in [our bug tracker](https://northerntech.atlassian.net/).

## License

This software is licensed under the MIT License. See LICENSE in the root of the repository for the full license text.
