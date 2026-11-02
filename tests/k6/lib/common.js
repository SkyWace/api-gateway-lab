// Cibles vues depuis le réseau Docker (k6 tourne dans le compose -> pas de bruit lié au NAT de l'hôte)
import http from 'k6/http';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

export const TARGETS = {
  direct: 'http://catalog-1:3000',   // baseline sans gateway (1 instance)
  kong: 'http://kong:8000',
  apisix: 'http://apisix:9080',
  traefik: 'http://traefik:80',
  scg: 'http://scg:8080',
};

export function baseUrl() {
  const t = __ENV.TARGET || 'direct';
  if (!TARGETS[t]) throw new Error(`TARGET inconnu : ${t} (${Object.keys(TARGETS).join(', ')})`);
  return TARGETS[t];
}

export function getToken() {
  const kc = __ENV.KEYCLOAK_URL || 'http://keycloak:8080';
  const res = http.post(`${kc}/realms/lab/protocol/openid-connect/token`, {
    grant_type: 'client_credentials',
    client_id: 'lab-client',
    client_secret: 'lab-secret',
  });
  if (res.status !== 200) throw new Error(`Token Keycloak impossible : ${res.status} ${res.body}`);
  return res.json('access_token');
}

// Écrit le résumé texte en console + JSON dans /results/<TARGET>-<test>-<horodatage>.json
export function summaryTo(testName) {
  return (data) => {
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const file = `/results/${__ENV.TARGET || 'direct'}-${testName}-${stamp}.json`;
    return {
      stdout: textSummary(data, { indent: ' ', enableColors: true }),
      [file]: JSON.stringify(data, null, 2),
    };
  };
}
