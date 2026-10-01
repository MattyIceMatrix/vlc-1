# 60-second clean-room quickstart

Run on a fresh machine with only Git, Python 3, and Node:

```sh
bash quickstart.sh
```

The script clones the canonical GitLab repository, discovers the vector index under `aer1-implementations/vectors`, validates the core receipt rules plus the profile and anchor boundaries, checks that Node is available, and prints a full N/N pass result with elapsed milliseconds. It has no package installation and makes no network request other than the clone. Pass a different repository URL as the first argument; set `AER1_QUICKSTART_DIR=/path` to retain the clone.

The requested Docker validation could not be run in this sandbox because neither `docker` nor `podman` is installed. The same script was run against the public canonical GitLab clone from the available sandbox and its measured wall-clock result is recorded in the final acceptance notes.

---
AER-1 is created by Brennan Zambo. Learn more at https://zambo.dev.
