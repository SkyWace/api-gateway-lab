// Expérience RATE LIMITING — quota configuré : 10 req/s par X-Client-Id sur /api/catalog.
//   docker compose --profile tools run --rm k6 run /scripts/ratelimit.js -e TARGET=traefik
// client-greedy envoie 30 req/s (attendu ≈ 10 acceptées/s, ≈ 20 en 429)
// client-polite envoie 5 req/s (attendu : 0 refus -> équité entre clients)
// client-burst envoie des rafales de 25 requêtes simultanées toutes les 2 s (comportement du burst)
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';
import { baseUrl, summaryTo } from './lib/common.js';

const accepted = new Counter('accepted');
const limited = new Counter('limited_429');
const other = new Counter('other_status');

const DURATION = __ENV.DURATION || '30s';
export const options = {
  discardResponseBodies: true,
  scenarios: {
    greedy: { executor: 'constant-arrival-rate', rate: 30, timeUnit: '1s', duration: DURATION, preAllocatedVUs: 20, env: { CLIENT: 'client-greedy' } },
    polite: { executor: 'constant-arrival-rate', rate: 5, timeUnit: '1s', duration: DURATION, preAllocatedVUs: 5, env: { CLIENT: 'client-polite' } },
    burst:  { executor: 'constant-arrival-rate', rate: 1, timeUnit: '2s', duration: DURATION, preAllocatedVUs: 5, exec: 'burst', env: { CLIENT: 'client-burst' } },
  },
};

function record(res, client) {
  const tags = { client };
  if (res.status === 200) accepted.add(1, tags);
  else if (res.status === 429) limited.add(1, tags);
  else other.add(1, { client, status: String(res.status) });
}

export default function () {
  const res = http.get(`${baseUrl()}/api/catalog/1`, { headers: { 'X-Client-Id': __ENV.CLIENT } });
  record(res, __ENV.CLIENT);
}

export function burst() {
  const reqs = Array.from({ length: 25 }, () => ['GET', `${baseUrl()}/api/catalog/1`, null, { headers: { 'X-Client-Id': __ENV.CLIENT } }]);
  for (const r of http.batch(reqs)) record(r, __ENV.CLIENT);
}

// Répartition par client lisible directement dans le résumé
options.thresholds = {
  'accepted{client:client-greedy}': ['count>=0'],
  'limited_429{client:client-greedy}': ['count>=0'],
  'accepted{client:client-polite}': ['count>=0'],
  'limited_429{client:client-polite}': ['count>=0'],
  'accepted{client:client-burst}': ['count>=0'],
  'limited_429{client:client-burst}': ['count>=0'],
};

export const handleSummary = summaryTo('ratelimit');
