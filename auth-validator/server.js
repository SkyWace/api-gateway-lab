// Validateur JWT externalisé, utilisé par Traefik (middleware forwardAuth).
// Traefik OSS ne valide pas de JWT nativement : c'est justement un point du comparatif.
// Vérifie : algo RS256, signature (clé publique du realm), exp, nbf, iss.
'use strict';
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 4000);
const EXPECTED_ISS = process.env.EXPECTED_ISS || 'http://keycloak:8080/realms/lab';
const publicKey = crypto.createPublicKey(fs.readFileSync(process.env.PUBLIC_KEY_PATH || '/keys/lab-public.pem'));

const b64url = (s) => Buffer.from(s.replace(/-/g, '+').replace(/_/g, '/'), 'base64');

function verify(token) {
  const parts = token.split('.');
  if (parts.length !== 3) throw new Error('malformed_token');
  const header = JSON.parse(b64url(parts[0]).toString('utf8'));
  if (header.alg !== 'RS256') throw new Error('unsupported_alg');
  const ok = crypto.verify('RSA-SHA256', Buffer.from(`${parts[0]}.${parts[1]}`), publicKey, b64url(parts[2]));
  if (!ok) throw new Error('bad_signature');
  const claims = JSON.parse(b64url(parts[1]).toString('utf8'));
  const now = Math.floor(Date.now() / 1000);
  if (typeof claims.exp !== 'number' || claims.exp < now) throw new Error('token_expired');
  if (claims.nbf && claims.nbf > now + 5) throw new Error('token_not_yet_valid');
  if (claims.iss !== EXPECTED_ISS) throw new Error('bad_issuer');
  return claims;
}

http.createServer((req, res) => {
  if (req.url === '/health') { res.writeHead(200); return res.end('UP'); }
  const auth = req.headers.authorization || '';
  const m = auth.match(/^Bearer\s+(.+)$/i);
  try {
    if (!m) throw new Error('missing_token');
    const claims = verify(m[1].trim());
    res.writeHead(200, { 'X-User-Sub': String(claims.sub || claims.azp || 'unknown') });
    res.end();
  } catch (e) {
    res.writeHead(401, {
      'Content-Type': 'application/json',
      'WWW-Authenticate': `Bearer error="invalid_token", error_description="${e.message}"`,
    });
    res.end(JSON.stringify({ error: e.message }));
  }
}).listen(PORT, () => console.log(`auth-validator on ${PORT}, iss=${EXPECTED_ISS}`));
