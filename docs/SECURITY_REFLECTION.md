# Security engineering reflection

## What the exercise establishes

The recorded protocol leaves word spacing and letter distributions recognizable.
It offers only 312 keys, so exhaustive ranking is inexpensive. Repetitive English
phrases and predictable response structure can strengthen frequency and
known-plaintext reasoning. In this project, the attack itself uses ciphertext
frequency scores; known inputs are used afterwards to verify its result.
The mood-derived schedule is another independent weakness: a public mood value
can reveal the intended key directly, even without statistical analysis.

Nibble armor is reversible encoding. Substitution supplies neither modern
confidentiality nor authenticated integrity. A loopback interface limits network
exposure but does not authenticate every process on the host. Content hashes
detect accidental changes relative to a trusted manifest; an attacker able to
replace both files and manifest can replace the hashes too.

## Two alternatives for a real local service

1. **Linux pathname UNIX-domain sockets with access control.** Put the socket
   in a directory restricted to the intended user/group, apply appropriate
   ownership and permissions, and verify peer credentials where appropriate.
   This can restrict which local processes connect without exposing a TCP port.
   It is access control rather than encryption, and does not protect against a
   privileged host compromise. Linux's permission behavior is documented in the
   [UNIX socket manual](https://man7.org/linux/man-pages/man7/unix.7.html);
   abstract socket names do not provide pathname permission checks.
2. **Authenticated TLS on loopback.** A TLS 1.3-capable client/server can use a
   locally trusted certificate authority or a deliberately trusted certificate,
   with hostname/identity validation kept enabled. Client authentication can use
   mutual TLS or an appropriate application credential. A self-signed certificate
   without explicit trust and verification is insufficient. Python's
   [SSL documentation](https://docs.python.org/3.12/library/ssl.html) describes
   certificate validation and client/server contexts. This would replace the
   teaching cipher; it is not implemented as a claimed production service here.

Both need lifecycle management, input validation and a realistic host threat
model. Protect saved plaintext reports and minimize sensitive logging as well.
This lab deliberately retains the weak protocol so the failure remains visible.

## Scope of the extension

The original coursework requested local Ollama inference and a Linux executable.
This portfolio is a separately implemented extension: the default is deterministic
offline replay, and optional fresh Gemini inference uses the user's approved
cloud configuration. Offline replay is not fresh offline LLM inference. No
Ollama installation or model download is performed. The authored coursework reports are included under docs/reports, while
supplied instructions and project notes are retained in archive/coursework; this extension is not presented
as evidence that a fresh Ollama model was run.
