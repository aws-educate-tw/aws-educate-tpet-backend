#!/usr/bin/env node

// Create a short-lived token for the existing Preview participant fixture.
// The signing secret is read only at CI runtime and never written to a file.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const signingSecret = process.env.RSVP_SIGNING_SECRET;
if (!signingSecret) throw new Error('RSVP_SIGNING_SECRET is required');

const environmentPath = path.resolve(
  __dirname, '../../rsvp_service/api_regression/rsvp_service_preview_environment.json'
);
const environment = JSON.parse(fs.readFileSync(environmentPath, 'utf8'));
const values = Object.fromEntries(environment.values.map(({ key, value }) => [key, value]));
const prefix = `${values.run_id}_`;
if (!values.run_id_participant_id?.startsWith(prefix)) {
  throw new Error('RSVP Preview participant fixture does not match its run ID');
}

const now = Math.floor(Date.now() / 1000);
const header = { alg: 'HS256', typ: 'JWT' };
const payload = {
  run_id: values.run_id,
  participant_id: values.run_id_participant_id.slice(prefix.length),
  campaign_id: values.campaign_id,
  email_id: 'bruno-regression',
  name: 'API Regression User',
  iat: now,
  exp: now + 3600
};
const unsigned = [header, payload]
  .map((part) => Buffer.from(JSON.stringify(part)).toString('base64url'))
  .join('.');
const signature = crypto.createHmac('sha256', signingSecret)
  .update(unsigned)
  .digest('base64url');
process.stdout.write(`${unsigned}.${signature}`);
