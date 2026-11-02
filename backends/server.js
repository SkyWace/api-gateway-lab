// API factice commune aux services "catalog" et "orders".
// Zéro dépendance (module http natif) pour que l'image soit identique et légère.
// Variables : PREFIX (/api/catalog | /api/orders), DATA_FILE, INSTANCE_ID, PORT.
'use strict';
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 3000);
const PREFIX = process.env.PREFIX || '/api/catalog';
const INSTANCE = process.env.INSTANCE_ID || require('os').hostname();
const items = JSON.parse(fs.readFileSync(process.env.DATA_FILE || '/data/catalog.json', 'utf8'));

// Mode chaos, piloté à chaud via /admin/chaos (jamais exposé par les gateways)
const chaos = { delayMs: 0, errorRate: 0 };

const ECHO_HEADERS = ['x-request-id', 'x-correlation-id', 'traceparent', 'x-client-id', 'x-user-sub', 'x-consumer-username'];

function send(res, status, body, extra = {}) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
    'X-Instance': INSTANCE,
    ...extra,
  });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve) => {
    let data = '';
    req.on('data', (c) => { data += c; if (data.length > 1e6) req.destroy(); });
    req.on('end', () => resolve(data));
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const path = url.pathname;
  const seen = {};
  for (const h of ECHO_HEADERS) if (req.headers[h]) seen[h] = req.headers[h];

  if (path === '/health') return send(res, 200, { status: 'UP', instance: INSTANCE });

  if (path === '/admin/chaos') {
    if (url.searchParams.has('delay')) chaos.delayMs = Number(url.searchParams.get('delay')) || 0;
    if (url.searchParams.has('error')) chaos.errorRate = Math.min(1, Math.max(0, Number(url.searchParams.get('error')) || 0));
    return send(res, 200, { instance: INSTANCE, chaos });
  }

  if (!path.startsWith(PREFIX)) return send(res, 404, { error: 'not_found', path });

  if (chaos.delayMs) await new Promise((r) => setTimeout(r, chaos.delayMs));
  if (chaos.errorRate && Math.random() < chaos.errorRate) {
    return send(res, 500, { error: 'injected_failure', instance: INSTANCE });
  }

  const rest = path.slice(PREFIX.length).replace(/^\/+/, '');

  if (req.method === 'GET' && rest === '') {
    const limit = Math.min(Number(url.searchParams.get('limit')) || items.length, items.length);
    return send(res, 200, { instance: INSTANCE, headersSeen: seen, count: limit, items: items.slice(0, limit) });
  }
  if (req.method === 'GET' && /^\d+$/.test(rest)) {
    const item = items.find((i) => String(i.id) === rest);
    return item
      ? send(res, 200, { instance: INSTANCE, headersSeen: seen, item })
      : send(res, 404, { error: 'not_found', id: rest });
  }
  if (req.method === 'POST' && rest === '') {
    const raw = await readBody(req);
    let body;
    try { body = JSON.parse(raw || '{}'); } catch { return send(res, 400, { error: 'invalid_json' }); }
    return send(res, 201, { instance: INSTANCE, headersSeen: seen, created: { id: crypto.randomUUID(), ...body } });
  }
  return send(res, 405, { error: 'method_not_allowed' });
});

server.keepAliveTimeout = 65000;
server.listen(PORT, () => console.log(`[${INSTANCE}] ${PREFIX} listening on ${PORT}`));
process.on('SIGTERM', () => server.close(() => process.exit(0)));
