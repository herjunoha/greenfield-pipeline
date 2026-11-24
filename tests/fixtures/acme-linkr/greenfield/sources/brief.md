# acme-linkr brief

Acme wants a small link-shortening service and a command-line client for it. Synthetic: a fictional company.

## Terms
A short code is the 6-character tail of a short link. A visit is one redirect served for a code.

## Create
Anyone with an API key can create a short link from a web address. The service returns the short code.

## Redirect
A visitor who opens a short link is sent to the original address.

## Unknown
A code that does not exist answers "not found".

## Schemes
Only http and https addresses are accepted. Anything else is refused and nothing is stored.

## Auth
Creating a link needs an API key. Opening one does not.

## Speed
Redirects should feel instant: 95 percent within 200 ms at about 20 requests a second.

## Cli
`linkr create <address>` prints the short code. `linkr stats <code>` prints how many visits it has had.
