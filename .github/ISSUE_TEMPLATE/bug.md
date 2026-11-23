---
name: Bug Report
about: Create a report to help reproduce and fix a compiler, runtime, or standard library defect
title: "[BUG] "
labels: bug
assignees: ''
---

## Description
<!-- A clear and concise description of the bug. -->

## Velo Version
<!-- Run `velo version` and paste the full output here (e.g. Velo 2.0.0-pre (commit abc1234, windows/x86_64, gcc)). -->
```
velo version
```

## Environment
- **Operating System:** (e.g. Windows 11 x86_64, Linux Ubuntu 24.04, macOS Sonoma)
- **C Compiler:** (e.g. GCC 14.2 UCRT64, Clang 19, MSVC)
- **Velo Command:** (e.g. `velo check`, `velo build -o app.exe`, `velo run`, `velo emit-c`)

## Minimal `.vl` Repro
<!-- Provide a minimal, self-contained Velo code snippet reproducing the issue. Keep it as small as possible. -->
```velo
use sys.io

act main() {
    // Minimal reproduction snippet here
}
```

## Steps to Reproduce
1. Save the snippet as `repro.vl`
2. Run command: `velo check repro.vl` (or `velo run repro.vl`)
3. See error or unexpected output

## Expected Behavior
<!-- A clear and concise description of what you expected to happen. -->

## Actual Behavior
<!-- Paste the complete error diagnostic, compiler panic, or unexpected runtime output. -->
```
[Velo Error] ...
```

## Additional Context / Regression Info
<!-- Add any other context about the problem here (e.g., did this work in an earlier version or commit? Does it reproduce with `--no-line-directives` or `--unsafe-heap`?). -->
