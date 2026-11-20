# Velo Package Management and Registry Specification

This document specifies the Velo package management architecture, dependency resolution rules, transport security requirements, and the registry HTTP index format implemented in Phase 72.

---

## 1. Architecture and Trust Model

The Velo package ecosystem is built on four core principles:
1. **Decentralized and Static**: A Velo package registry is a purely static HTTP/HTTPS repository. It requires no dynamic servers, server-side APIs, database engines, or privileged user accounts. A registry can be hosted on GitHub Pages, Cloudflare Pages, Amazon S3, or any static file server.
2. **Cryptographic Integrity by Construction**: Every registry entry binds an immutable version string to a downloadable archive URL and a cryptographic SHA-256 digest. Content is verified before compilation.
3. **Transport Security by Default**: Registry lookups and package downloads must use HTTPS with strict TLS 1.3 certificate validation. Plaintext HTTP or unverified TLS requires an explicit `--insecure` flag that emits a warning.
4. **Reproducibility**: `velo.lock` records the exact content hashes of all dependencies. If a downloaded archive or local file does not match the locked hash, the build fails immediately.

---

## 2. Registry Index Format (`index.json`)

### 2.1 Endpoint URL Layout

For any package named `<name>`, the package index is located at:
```
<registry-root>/<name>/index.json
```

Where:
- `<registry-root>` defaults to `https://pkg.velolang.org` or is configured via the `VELO_REGISTRY` environment variable or command-line option.
- `<name>` is the canonical package identifier (matching `[a-zA-Z_][a-zA-Z0-9_]*`).

### 2.2 Schema

An `index.json` document lists all published versions of a package. The primary schema groups releases under a `versions` object:

```json
{
  "name": "math_lib",
  "description": "Fast arbitrary-precision mathematics for Velo",
  "versions": {
    "1.0.0": {
      "url": "https://pkg.velolang.org/tarballs/math_lib-1.0.0.tar.gz",
      "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a"
    },
    "1.1.0": {
      "url": "https://pkg.velolang.org/tarballs/math_lib-1.1.0.tar.gz",
      "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    }
  }
}
```

The registry index parser also accepts a flat dictionary mapping versions directly to version descriptors:

```json
{
  "1.0.0": {
    "url": "https://pkg.velolang.org/tarballs/math_lib-1.0.0.tar.gz",
    "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a"
  }
}
```

### 2.3 Required Fields

Each version entry must contain:
- `url` (string): Full URL where the package archive (`.tar.gz` or `.tar`) can be downloaded. Must be HTTPS unless `--insecure` is specified.
- `sha256` (string): 64-character lowercase hexadecimal representation of the SHA-256 digest of the archive bytes.

---

## 3. Dependency Declaration in `velo.pkg`

Package manifests (`velo.pkg`) declare dependencies inside the `deps` block:

```velo
pkg {
    name: "my_application"
    version: "0.1.0"
    entry: "src/main.vl"
}

deps {
    # 1. Registry dependency (resolves against <registry>/<name>/index.json)
    json: "1.2.0"

    # 2. Git dependency (cloned into .velo_cache/deps/math with commit tracking)
    math: git "https://github.com/example/math.git" @ "v2.1.0"

    # 3. Local filesystem dependency
    shared: local "../shared_lib"
}
```

---

## 4. Transport Security and the `--insecure` Flag

Security Invariants **I72.3** and **I73.5** enforce strict transport controls:

1. **HTTPS Enforcement**: If a registry index URL or package archive URL begins with `http://`, the resolver immediately aborts with:
   ```
   [Velo Error] Plaintext HTTP registry URL '<url>' is disallowed without explicit --insecure flag.
   ```
2. **Insecure Mode**: Passing `--insecure` allows plaintext HTTP and disables peer certificate verification for HTTPS, but prints a visible security warning:
   ```
   [Velo Warning] Insecure connection to '<url>': cleartext HTTP used.
   [Velo Warning] TLS certificate verification disabled via --insecure for registry '<url>'.
   ```
3. **No Degraded Fallback**: A failed HTTPS connection never silently falls back to plaintext HTTP.

---

## 5. Publishing to a Registry

Publishing a package does not require API keys or server credentials:
1. Run `velo pkg publish` (Phase 72.6) to archive `src/` and `std/` into a `.tar.gz` archive.
2. The compiler calculates the archive's SHA-256 digest and prints the corresponding JSON block.
3. Submit a Pull Request updating `<name>/index.json` in the registry repository.
