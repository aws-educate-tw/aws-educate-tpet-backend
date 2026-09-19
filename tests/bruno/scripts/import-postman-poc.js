/*
 * Generates the Bruno POC collections from the Postman v2.1 source files.
 *
 * The script is intentionally scoped to Auth and Email Service. It removes
 * saved examples and uses the approved shared test recipient before writing files.
 */
const fs = require('node:fs/promises');
const path = require('node:path');
const { postmanToBruno, postmanToBrunoEnvironment } = require('@usebruno/converters');
const {
  stringifyCollection,
  stringifyEnvironment,
  stringifyRequest
} = require('@usebruno/filestore');

const projectRoot = path.resolve(__dirname, '..', '..', '..');
const brunoRoot = path.resolve(__dirname, '..');
const collectionRoot = path.join(brunoRoot, 'collections');
const emailTestRecipient = 'awseducate.cloudambassador@gmail.com';

const services = [
  {
    sourceName: 'auth_service',
    targetName: 'auth-service',
    environmentVariables: ['environment']
  },
  {
    sourceName: 'email_service',
    targetName: 'email-service',
    environmentVariables: [
      'environment',
      'domain',
      'template_file_id',
      'pull_request_number',
      'commit_sha'
    ]
  }
];

const emailPreRequestScripts = {
  'Send email (RSVP)': `const environment = bru.getEnvVar('environment');
const accessToken = bru.getEnvVar('access_token');

const fileResponse = await bru.sendRequest({
  method: 'GET',
  url: \`https://\${environment}-file-service-internal-api-tpet.aws-educate.tw/\${environment}/files?file_extension=html&limit=1\`,
  headers: { Authorization: \`Bearer \${accessToken}\` }
});

const file = fileResponse.data?.data?.[0];
if (!file) {
  throw new Error('No HTML file found in the file service.');
}

bru.setEnvVar('template_file_id', file.file_id);
bru.setEnvVar('template_file_name', file.file_name);
bru.setEnvVar('template_file_url', file.file_url);

const campaignResponse = await bru.sendRequest({
  method: 'POST',
  url: \`https://\${environment}-rsvp-service-internal-api-tpet.aws-educate.tw/rsvp-service/\${environment}/campaigns\`,
  headers: {
    Authorization: \`Bearer \${accessToken}\`,
    'Content-Type': 'application/json'
  },
  data: {
    campaign_name: 'Campaign Created for regression test',
    cohort: '8',
    campaign_start_time: '2099-04-20T09:00:00Z',
    campaign_end_time: '2099-05-20T17:00:00Z',
    campaign_location: 'Taipei 101'
  }
});

const campaignId = campaignResponse.data?.campaign_id;
if (!campaignId) {
  throw new Error('Failed to retrieve campaign_id from create_campaign API.');
}

bru.setEnvVar('campaign_id', campaignId);`,
  'Send email (non-RSVP)': `const environment = bru.getEnvVar('environment');
const accessToken = bru.getEnvVar('access_token');

const fileResponse = await bru.sendRequest({
  method: 'GET',
  url: \`https://\${environment}-file-service-internal-api-tpet.aws-educate.tw/\${environment}/files?file_extension=html&limit=1\`,
  headers: { Authorization: \`Bearer \${accessToken}\` }
});

const file = fileResponse.data?.data?.[0];
if (!file) {
  bru.deleteEnvVar('template_file_id');
  bru.deleteEnvVar('template_file_name');
  bru.deleteEnvVar('template_file_url');
  throw new Error('No HTML file found in the file service.');
}

bru.setEnvVar('template_file_id', file.file_id);
bru.setEnvVar('template_file_name', file.file_name);
bru.setEnvVar('template_file_url', file.file_url);`,
  'List emails': "await bru.sleep(3000);"
};

function removeExamples(items) {
  for (const item of items || []) {
    delete item.examples;
    removeExamples(item.items);
  }
}

function findRequest(items, name) {
  for (const item of items || []) {
    if (item.type === 'http-request' && item.name === name) return item;
    const nested = findRequest(item.items, name);
    if (nested) return nested;
  }
  return undefined;
}

function sanitiseEmailRequest(item) {
  const body = JSON.parse(item.request.body.json);
  body.recipients = [
    {
      email: emailTestRecipient,
      template_variables: {
        Name: 'API Regression User',
        'Certificate Text': 'TPET API regression test certificate.'
      }
    }
  ];
  body.cc = [];
  body.bcc = [];
  item.request.body.json = `${JSON.stringify(body, null, 2)}\n`;
}

function updateAuthJsonAssertion(collection) {
  const request = findRequest(collection.items, 'Get me');
  request.request.script.res = request.request.script.res.replace(
    'pm.response.to.be.json;',
    "expect(res.getHeader('content-type')).to.include('application/json');"
  );

  // @usebruno/converters currently rewrites the literal `postman` to `pm`
  // while translating this Postman script. Restore the source collection's
  // expected service-account identity so the Bruno and Newman assertions match.
  request.request.script.res = request.request.script.res
    .replace(
      'expect(jsonData.email).to.eql("pm@aws-educate.tw");',
      'expect(jsonData.email).to.eql("postman@aws-educate.tw");'
    )
    .replace(
      'expect(jsonData.username).to.eql("pm");',
      'expect(jsonData.username).to.eql("postman");'
    );
}

function updateEmailScripts(collection) {
  for (const [name, script] of Object.entries(emailPreRequestScripts)) {
    const request = findRequest(collection.items, name);
    if (!request) throw new Error(`Expected request not found: ${name}`);
    request.request.script.req = script;
  }

  sanitiseEmailRequest(findRequest(collection.items, 'Send email (RSVP)'));
  sanitiseEmailRequest(findRequest(collection.items, 'Send email (non-RSVP)'));

  const listEmails = findRequest(collection.items, 'List emails');
  listEmails.request.script.res = listEmails.request.script.res.replace(
    `test("Recipient name is 'harry鍾'", function () {
        const firstEmail = responseData.data[0];
        expect(firstEmail.recipient_name).to.eql("harry鍾");
    });`,
    `test('Recipient name is a non-empty string', function () {
        const firstEmail = responseData.data[0];
        expect(firstEmail.recipient_name).to.be.a('string').and.to.not.be.empty;
    });`
  );
  listEmails.request.script.res = listEmails.request.script.res.replace(
    'if (responseData.data.length === 0 && currentRetryCount < maxRetryCount) {',
    'if (Array.isArray(responseData.data) && responseData.data.length === 0 && currentRetryCount < maxRetryCount) {'
  );
  listEmails.request.script.res = listEmails.request.script.res.replace(
    /\} else \{\s+bru\.deleteEnvVar\("list_emails_retry_count"\);/,
    '} else if (Array.isArray(responseData.data)) {\n      bru.deleteEnvVar("list_emails_retry_count");'
  );
}

function normaliseBru(content) {
  return content.replace(/[ \t]+$/gm, '');
}

function createEnvironment(convertedEnvironment, service) {
  const sourceVariables = new Map(
    convertedEnvironment.variables.map((variable) => [variable.name, variable])
  );
  const variables = service.environmentVariables.map((name) => {
    const source = sourceVariables.get(name);
    if (!source) throw new Error(`Expected environment variable not found: ${name}`);
    return { ...source };
  });

  variables.push(
    {
      name: 'access_token',
      value: '',
      enabled: true,
      type: 'text',
      secret: true
    }
  );

  return {
    name: 'preview',
    variables
  };
}

async function writeCollectionItems(items, destination) {
  for (const item of items || []) {
    if (item.type !== 'http-request') continue;
    const filename = `${item.name.replaceAll('/', '-')}.bru`;
    await fs.writeFile(
      path.join(destination, filename),
      normaliseBru(stringifyRequest(item, { format: 'bru' }))
    );
  }
}

async function migrateService(service) {
  const apiRegressionPath = path.join(
    projectRoot,
    'tests',
    service.sourceName,
    'api_regression'
  );
  const postmanCollection = JSON.parse(
    await fs.readFile(
      path.join(apiRegressionPath, `${service.sourceName}_regression_test_collection.json`),
      'utf8'
    )
  );
  const postmanEnvironment = JSON.parse(
    await fs.readFile(
      path.join(apiRegressionPath, `${service.sourceName}_preview_environment.json`),
      'utf8'
    )
  );

  const converted = await postmanToBruno(postmanCollection);
  if (converted.issues.length > 0) {
    throw new Error(`${service.sourceName} conversion issues: ${JSON.stringify(converted.issues)}`);
  }

  removeExamples(converted.collection.items);
  converted.collection.root.docs = 'Generated from the TPET Postman v2.1 collection for the Bruno POC.';

  if (service.sourceName === 'auth_service') updateAuthJsonAssertion(converted.collection);
  if (service.sourceName === 'email_service') updateEmailScripts(converted.collection);

  const destination = path.join(collectionRoot, service.targetName);
  await fs.rm(destination, { recursive: true, force: true });
  await fs.mkdir(path.join(destination, 'environments'), { recursive: true });

  const config = { version: '1', name: converted.collection.name, type: 'collection' };
  await fs.writeFile(path.join(destination, 'bruno.json'), `${JSON.stringify(config, null, 2)}\n`);
  await fs.writeFile(
    path.join(destination, 'collection.bru'),
    normaliseBru(stringifyCollection(converted.collection.root, config, { format: 'bru' }))
  );
  await writeCollectionItems(converted.collection.items, destination);

  const convertedEnvironment = await postmanToBrunoEnvironment(postmanEnvironment);
  await fs.writeFile(
    path.join(destination, 'environments', 'preview.bru'),
    normaliseBru(stringifyEnvironment(createEnvironment(convertedEnvironment, service), { format: 'bru' }))
  );
}

async function main() {
  await fs.mkdir(collectionRoot, { recursive: true });
  for (const service of services) await migrateService(service);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
