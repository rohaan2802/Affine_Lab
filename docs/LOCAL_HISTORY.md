# Coursework archive and excluded configuration

All supplied project material is included in the public working tree. Authored
reports, screenshots, maintained/historical source and outputs are organized in
their relevant folders. Remaining instructions, project discussion, audit records
and the supplied executable are under `archive/coursework`.

The supplied executable and instructor document are third-party materials,
separately attributed in `archive/coursework/THIRD_PARTY_NOTICE.md`. The upstream
repository metadata declares no license; inclusion here does not grant rights
or apply the maintained implementation's MIT license to those artifacts.
The current independent package does not need the executable.

Actual API configuration in `.env`, private key files and generated environments,
caches and build outputs stay excluded. Blank configuration examples are included.
`tools/check_publish.py` checks credential patterns and allows only the explicitly
attributed supplied executable at its recorded path and exact SHA-256 digest.
No other executable is silently permitted. This is a hygiene check, not a policy
or redistribution-rights certification.
