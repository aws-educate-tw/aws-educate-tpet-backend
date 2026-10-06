# TPET Bruno API Regression

This directory contains the Bruno migration for all five version-controlled
TPET API regression collections. The collections are generated from
the existing Postman v2.1 JSON files, then adjusted only where Bruno requires a
different scripting API.

## Scope

- Auth Service: bearer authentication, preview environment and response tests.
- Email Service: request chaining, environment mutation, dynamic variables and
  collection sequencing.
- File Service: multipart HTML upload and a HEAD request for the uploaded file.
- RSVP Service: nine requests, response-dependent assertions, and Preview
  participant fixtures.
- Webhook Service: webhook creation and response checks.
- Bruno CLI: JSON, JUnit and HTML reports; non-zero exit status on test failure.

The generated collections exclude saved Postman response examples. They are not
needed to execute a collection and retaining them would copy historical API
data into a second format.

## Install and regenerate

```bash
cd tests/bruno
npm ci
npm run import:postman
```

`scripts/import-postman-collections.js` is idempotent and is the source of the manual
migration changes. It performs the following transformations:

- converts Postman v2.1 collections and preview environments with the official
  `@usebruno/converters` package;
- retains all 17 requests and their test scripts;
- rewrites the unsupported `pm.response.to.be.json` assertion;
- rewrites `pm.sendRequest` callback flows using awaited `bru.sendRequest`;
- replaces the ineffective List Emails timeout with `await bru.sleep(3000)`;
- removes saved examples and replaces the historical personal recipient data
  with the approved shared regression-test mailbox;
- makes `access_token` a Bruno secret variable.
- repairs the File Service multipart fixture path and rewrites its asynchronous
  `pm.sendRequest` assertion;
- repairs RSVP request-body access, JSON-content checks, commented JSON bodies,
  and collection variables; replaces the example participant with a test identity;
- leaves the RSVP participant token blank in the Bruno environment.

## Local execution

Auth, Email, File, and Webhook use a valid Preview access token. Email sends to
the shared regression-test mailbox configured in its request bodies. RSVP's
first two requests also need a participant JWT signed for the Preview fixture;
pass it as `--env-var token="$RSVP_TOKEN"` for a local run.

```bash
cd tests/bruno/collections/auth-service
../../node_modules/.bin/bru run . -r \
  --env preview \
  --env-var access_token="$ACCESS_TOKEN" \
  --reporter-html /tmp/auth-report.html \
  --reporter-junit /tmp/auth-report.xml \
  --reporter-skip-headers Authorization \
  --reporter-skip-body
```

```bash
cd tests/bruno/collections/email-service
../../node_modules/.bin/bru run . -r \
  --env preview \
  --env-var access_token="$ACCESS_TOKEN" \
  --env-var pull_request_number=local \
  --env-var commit_sha=local \
  --reporter-html /tmp/email-report.html \
  --reporter-junit /tmp/email-report.xml \
  --reporter-skip-headers Authorization \
  --reporter-skip-body
```

The CLI process exits non-zero when a request, test or assertion fails. Reports
must always use `--reporter-skip-headers Authorization --reporter-skip-body`.
The GitHub Actions job summary uses the sanitized JSON and JUnit reports to show
request and test totals directly on the run page.

## CI runtime secrets

The GitHub Actions workflow at
`.github/workflows/bruno_api_regression.yaml` injects secrets only at
runtime:

- `aws-educate-tpet/preview/service-accounts/postman/access-token` provides the
  API access token.

The workflow offers a manual selector for `auth`, `email`, `file`, `rsvp`,
`webhook`, or `all`, plus a branch-scoped Auth trigger. The other collections
are manual because they change Preview data. The RSVP job retrieves
`aws-educate-tpet/preview/jwt-hs256-secret` and signs a one-hour participant
JWT for the existing Preview run and participant fixture. The workflow uploads
JSON, JUnit, and HTML reports as artifacts and excludes request/response bodies
and the Authorization header from those reports.

## Validation boundary

All five collections parse and their scripts pass JavaScript syntax checks.
The original Newman service workflows still run independently. The new File,
RSVP, and Webhook collections require a manual Preview CI run to establish live
request and assertion parity. RSVP has response-dependent test branches, so its
78 declared assertions are not a fixed per-run pass count. Its Preview fixture
must still exist and the CI AWS identity must be able to read the JWT signing
secret.
