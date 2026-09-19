# TPET Bruno API Regression

This directory contains the Phase 1 Bruno migration for the Auth Service and
Email Service API regression collections. The collections are generated from
the existing Postman v2.1 JSON files, then adjusted only where Bruno requires a
different scripting API.

## Scope

- Auth Service: bearer authentication, preview environment and response tests.
- Email Service: request chaining, environment mutation, dynamic variables and
  collection sequencing.
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
- retains the six Auth and Email requests and their test scripts;
- rewrites the unsupported `pm.response.to.be.json` assertion;
- rewrites `pm.sendRequest` callback flows using awaited `bru.sendRequest`;
- replaces the ineffective List Emails timeout with `await bru.sleep(3000)`;
- removes saved examples and replaces the historical personal recipient data
  with the approved shared regression-test mailbox;
- makes `access_token` a Bruno secret variable.

## Local execution

The Auth collection requires only a valid preview access token. The Email
collection sends to the shared regression-test mailbox configured in its
request bodies.

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

The workflow offers a manual service selector and a branch-scoped Auth trigger.
The Email collection is not run automatically because it has external side
effects. The workflow uploads JSON, JUnit and HTML reports as artifacts and
excludes request/response bodies and the Authorization header from those reports.

## Known Phase 1 boundary

The selected collections contain no multipart upload request. The existing File
Service collection is the multipart case, so end-to-end multipart validation is
not satisfied by the current Auth/Email scope. It should be added as a focused
follow-up migration before declaring the full Phase 1 acceptance criteria complete.
