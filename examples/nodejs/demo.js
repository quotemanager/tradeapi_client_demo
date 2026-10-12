'use strict';
// Standard-library local HTTP consumer: node examples/nodejs/demo.js ths query funds
const fs = require('fs');
const path = require('path');
const http = require('http');
const ROOT = path.resolve(__dirname, '../..');

function readObject(file) {
  if (fs.statSync(file).size > 65536) throw Error('JSON file exceeds 64 KiB');
  const value = JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Expected JSON object');
  return value;
}

function prepare(args) {
  const execute = args.includes('--execute');
  args = args.filter(x => x !== '--execute');
  if (args.length < 1 || args.length > 3) throw Error('Usage: demo PRODUCT [COMMAND [VALUE]] [--execute]');
  const [product, command = 'query', value = ''] = args;
  const contract = readObject(path.join(ROOT, 'config/api-contract.json'));
  if (!['tdx', 'ths'].includes(product)) throw Error('PRODUCT must be tdx or ths');
  const profile = contract[product];
  let spec;
  if (command === 'query') {
    const category = value || 'funds';
    if (!Object.prototype.hasOwnProperty.call(profile.queries, category)) throw Error('Unsupported query');
    spec = {method: 'GET', path: profile.queries[category], input: 'none', live: false};
  } else {
    if (!Object.prototype.hasOwnProperty.call(profile.commands, command)) throw Error('Unsupported command');
    spec = {...profile.commands[command]};
  }
  let body = null;
  if (spec.input === 'file') {
    if (!value) throw Error('Pass a user-created JSON file');
    body = readObject(value);
  } else if (spec.input.startsWith('id-')) {
    if (!/^[A-Za-z0-9_-]{1,128}$/.test(value)) throw Error('Pass an existing action/preview ID');
    if (spec.input === 'id-path') spec.path += value;
    else body = {preview_id: value};
  } else if (value && command !== 'query') throw Error('This command takes no VALUE');
  return {profile, spec, body, execute};
}

function call(url, token, spec, body) {
  return new Promise((resolve, reject) => {
    const data = body === null ? null : Buffer.from(JSON.stringify(body), 'utf8');
    const headers = {'Content-Type': 'application/json'};
    if (token) headers.Authorization = 'Bearer ' + token;
    if (data) headers['Content-Length'] = data.length;
    // No proxy, redirect, pooled connection or retry mechanism.
    const request = http.request(url + spec.path, {method: spec.method, headers, agent: false}, response => {
      const chunks = []; let size = 0;
      response.on('data', chunk => {
        size += chunk.length;
        if (size > 16 * 1024 * 1024) response.destroy(Error('Response exceeds 16 MiB'));
        else chunks.push(chunk);
      });
      response.on('error', reject);
      response.on('aborted', () => reject(Error('Interrupted response; do not resubmit')));
      response.on('end', () => {
        try {
          const value = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid response object');
          resolve({status: response.statusCode, value});
        } catch (error) { reject(error); }
      });
    });
    const timer = setTimeout(() => request.destroy(Error('90-second timeout; do not resubmit')), 90000);
    request.on('close', () => clearTimeout(timer));
    request.on('error', reject);
    request.end(data);
  });
}

async function main(args) {
  const {profile, spec, body, execute} = prepare(args);
  if (spec.live && !execute) {
    console.log(JSON.stringify({dry_run: true, method: spec.method, path: spec.path, body,
      note: 'Nothing sent. --execute submits ONE REAL action.'}, null, 2));
    return 0;
  }
  const url = (process.env[profile.url_env] || profile.base_url).replace(/\/$/, '');
  const parsed = new URL(url);
  if (parsed.protocol !== 'http:' || parsed.hostname !== '127.0.0.1' || !parsed.port ||
      parsed.username || parsed.password || parsed.search || parsed.hash || parsed.pathname !== '/') {
    throw Error('URL must be http://127.0.0.1:<port>');
  }
  const token = (process.env[profile.token_env] || '').trim();
  if (spec.path !== '/health' && !/^[A-Za-z0-9_-]{32,256}$/.test(token)) throw Error('Set ' + profile.token_env);
  const {status, value} = await call(url, token, spec, body);
  console.log('HTTP', status);
  console.log(JSON.stringify(value, null, 2));
  return status === 200 && value.ok !== false ? 0 : 1;
}

if (require.main === module) main(process.argv.slice(2)).then(code => {process.exitCode = code;}).catch(error => {
  console.error(error.message, '\nNo automatic retry. Reconcile any action in the official client.');
  process.exitCode = 1;
});
module.exports = {prepare, call, main};
