# Public intermediate certificate

`rnp-icpedu-2025.pem` is the public **RNP ICPEdu GR46 OV TLS CA 2025** intermediate certificate, obtained from the certificate authority's HTTPS endpoint:

https://secure.globalsign.com/cacert/rnpicpedugr46ovtlsca2025.crt

SHA-256 of the original DER certificate:

`e10747d4da7bab09cba9952f019d3534cb9fba070bf13d8791b1699cd2ff59dd`

The UFRN portal did not supply a complete chain during validation. This public intermediate completes the chain. TLS hostname and certificate validation remain enabled. `VERIFY_X509_PARTIAL_CHAIN` is explicitly disabled so the intermediate is not accepted as a trust anchor: the chain must terminate in a root from certifi (or the explicitly configured SOURCE_CA_BUNDLE).

No private key is included. Re-check the issuing authority when the portal rotates its certificate. Never replace this with `verify=False`.
