import fs from 'node:fs';
import { UploadPost } from 'upload-post';

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => {
      try {
        resolve(data.trim() ? JSON.parse(data) : {});
      } catch (error) {
        reject(new Error(`Invalid JSON input: ${error.message}`));
      }
    });
    process.stdin.on('error', reject);
  });
}

function requireString(value, name) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`${name} is required.`);
  }
  return value.trim();
}

async function main() {
  const apiKey = process.env.UPLOAD_POST_API_KEY;
  if (!apiKey) throw new Error('UPLOAD_POST_API_KEY is not configured.');

  const input = await readStdin();
  const client = new UploadPost(apiKey);
  const action = requireString(input.action, 'action');
  let result;

  switch (action) {
    case 'upload_video': {
      const filePath = requireString(input.filePath, 'filePath');
      if (!fs.existsSync(filePath)) throw new Error(`Video not found: ${filePath}`);
      const options = { ...(input.options || {}) };
      if (!options.user) throw new Error('options.user is required.');
      if (!Array.isArray(options.platforms) || options.platforms.length === 0) {
        throw new Error('options.platforms must contain at least one platform.');
      }
      result = await client.upload(filePath, options);
      break;
    }
    case 'status':
      result = await client.getStatus(requireString(input.requestId, 'requestId'));
      break;
    case 'job_status':
      result = await client.getJobStatus(requireString(input.jobId, 'jobId'));
      break;
    case 'history':
      result = await client.getHistory(input.options || { page: 1, limit: 20 });
      break;
    case 'analytics':
      result = await client.getAnalytics(
        requireString(input.user, 'user'),
        input.options || {},
      );
      break;
    case 'list_scheduled':
      result = await client.listScheduled();
      break;
    case 'list_users':
      result = await client.listUsers();
      break;
    case 'create_user':
      result = await client.createUser(requireString(input.user, 'user'));
      break;
    case 'generate_connect_url':
      result = await client.generateJwt(
        requireString(input.user, 'user'),
        input.options || {},
      );
      break;
    default:
      throw new Error(`Unsupported action: ${action}`);
  }

  process.stdout.write(JSON.stringify({ ok: true, result }));
}

main().catch(error => {
  process.stdout.write(JSON.stringify({ ok: false, error: error.message }));
  process.exitCode = 1;
});
