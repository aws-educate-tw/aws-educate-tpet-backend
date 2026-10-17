#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const readOption = (name) => {
  const index = process.argv.indexOf(name);
  return index === -1 ? undefined : process.argv[index + 1];
};

const service = readOption('--service');
const jsonPath = readOption('--json');
const junitPath = readOption('--junit');

if (!service || !jsonPath || !junitPath) {
  throw new Error('Usage: write-github-summary.js --service <name> --json <path> --junit <path>');
}

const readAttributes = (element) => Object.fromEntries(
  [...element.matchAll(/([\w-]+)="([^"]*)"/g)].map(([, key, value]) => [key, value])
);

const numberAttribute = (attributes, name) => Number(attributes[name] || 0);

const summaryTitle = `${service[0].toUpperCase()}${service.slice(1)} Service`;
const artifactName = `bruno-api-regression-${service}-service-${process.env.GITHUB_RUN_ID || '<run-id>'}`;

let markdown;

if (!fs.existsSync(jsonPath) || !fs.existsSync(junitPath)) {
  markdown = [
    `## Bruno API Regression — ${summaryTitle}`,
    '',
    '> ⚠️ Bruno did not generate both JSON and JUnit reports. Check the collection step log for the root cause.',
    '',
    `Expected artifact: \`${artifactName}\``
  ].join('\n');
} else {
  const iterations = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  const requests = iterations.flatMap((iteration) => iteration.results || []);
  const passedRequests = requests.filter((request) => request.status === 'pass').length;
  const failedRequests = requests.filter((request) => request.status === 'fail' || request.status === 'error').length;
  const skippedRequests = requests.filter((request) => request.status === 'skipped').length;

  const junit = fs.readFileSync(junitPath, 'utf8');
  const suites = [...junit.matchAll(/<testsuite\b[^>]*>/g)].map(([suite]) => readAttributes(suite));
  const tests = suites.reduce((total, suite) => total + numberAttribute(suite, 'tests'), 0);
  const failures = suites.reduce((total, suite) => total + numberAttribute(suite, 'failures'), 0);
  const errors = suites.reduce((total, suite) => total + numberAttribute(suite, 'errors'), 0);
  const skipped = suites.reduce((total, suite) => total + numberAttribute(suite, 'skipped'), 0);
  const passedTests = tests - failures - errors - skipped;
  const passed = failedRequests === 0 && failures === 0 && errors === 0;

  markdown = [
    `## Bruno API Regression — ${summaryTitle}`,
    '',
    `**Status: ${passed ? '✅ Passed' : '❌ Failed'}**`,
    '',
    '| Metric | Result |',
    '| --- | ---: |',
    `| Requests | ${passedRequests} passed / ${requests.length} total |`,
    `| Tests | ${passedTests} passed / ${tests} total |`,
    `| Failed tests | ${failures} |`,
    `| Test errors | ${errors} |`,
    `| Skipped | ${skipped} |`,
    '',
    `Reports: artifact \`${artifactName}\` (HTML, JSON, and JUnit).`
  ].join('\n');

  if (failedRequests > 0 || skippedRequests > 0) {
    markdown += `\n\nRequest results: ${failedRequests} failed, ${skippedRequests} skipped.`;
  }
}

const summaryFile = process.env.GITHUB_STEP_SUMMARY;
if (summaryFile) {
  fs.appendFileSync(summaryFile, `${markdown}\n`);
} else {
  process.stdout.write(`${markdown}\n`);
}
