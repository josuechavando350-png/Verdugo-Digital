# C2PA acceptance fixtures

The unsigned PNG and remote-manifest PNG are unchanged test assets from
`contentauth/c2pa-rs` at `0e92435c6d621c02c9bde2a8d82346295ed1f509`.
Their exact source paths and SHA-256 digests are in `provenance.json`.
The upstream MIT and Apache-2.0 license files accompany these assets.

`signed-test.png` is an offline derivative of the unsigned asset, signed using
c2pa-python 0.39.0 (native SDK 0.92.0), the upstream **public example** es256
certificate/key, a `c2pa.created` action and no thumbnail. No user credential
or private production signing key was used or committed. The example signer
is untrusted; this is deliberate. The tests must never claim authenticity.

Tests inspect the signed asset, a modified IHDR with repaired PNG CRC, an
unsigned asset, and a remote-manifest asset. Remote manifest retrieval and
OCSP are disabled in the original SDK context. Python audit hooks alone do
not isolate native code; CI also isolates the OS network namespace.
