TASK: Implement a certificate-ID utility module for this app.

Create a NEW file at exactly this path:

    src/utils/certificateId.ts

The app issues certificate IDs in the canonical form `CERT-` followed by exactly 8
UPPERCASE hexadecimal characters (0-9 and A-F), e.g. `CERT-3F9A2B10`. Implement and
export (named exports, TypeScript) these three functions with EXACTLY this behavior:

1. isValidCertificateId(value: unknown): boolean
   Returns true if and only if `value` is a string that matches the canonical form:
   the literal prefix `CERT-` followed by exactly 8 characters, each one of 0-9 or
   UPPERCASE A-F. Anything else returns false, specifically:
     - lowercase hex (e.g. "CERT-3f9a2b10")            -> false
     - lowercase or altered prefix (e.g. "cert-3F9A2B10", "CERT_3F9A2B10") -> false
     - wrong hex length, 7 or 9 chars                  -> false
     - a non-hex char in the body (e.g. "CERT-3F9A2B1G") -> false
     - missing prefix (e.g. "3F9A2B10")                -> false
     - any leading/trailing whitespace                 -> false
     - a non-string value (number, null, undefined, object) -> false

2. formatCertificateId(input: string): string
   Canonicalizes a user-entered code into the valid form. Algorithm:
     a. Trim leading/trailing whitespace.
     b. Remove a single leading `CERT-` prefix if present, matched CASE-INSENSITIVELY
        (so `CERT-`, `cert-`, `Cert-` are all stripped).
     c. Uppercase what remains.
     d. If the remainder is exactly 8 hex characters (0-9A-F after uppercasing), return
        `CERT-` + that remainder. Otherwise THROW an Error whose message contains the
        exact substring `Invalid certificate ID`.
   Examples (input -> output):
     "cert-3f9a2b10"   -> "CERT-3F9A2B10"
     "  3f9a2b10 "      -> "CERT-3F9A2B10"
     "CERT-ABCDEF12"   -> "CERT-ABCDEF12"
     "3F9A2B10"         -> "CERT-3F9A2B10"
     "xyz"              -> throws Error("... Invalid certificate ID ...")
     "3F9A2B1"          -> throws (7 chars)

3. certificateIdOrNull(input: string): string | null
   Same normalization as formatCertificateId, but returns null instead of throwing when
   the input cannot be canonicalized to a valid certificate ID. On success returns the
   canonical `CERT-XXXXXXXX` string.
     "cert-3f9a2b10"   -> "CERT-3F9A2B10"
     "nope"             -> null

Constraints:
  - Pure module: no imports from the app, no side effects, no I/O.
  - Do not modify any other file. Do not add dependencies.
  - Keep it self-contained in src/utils/certificateId.ts.
