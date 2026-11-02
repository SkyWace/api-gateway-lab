// Expérience LATENCE — débit constant, mesure P50/P95/P99 et surcoût vs baseline "direct".
//   docker compose --profile tools run --rm k6 run /scripts/latency.js -e TARGET=kong
// Options : RATE (req/s, défaut 200), DURATION (défaut 60s), ENDPOINT=catalog|orders
// Note : X-Client-Id unique par requête pour ne PAS déclencher le rate limiting
// (le plugin reste actif sur la route, son coût est donc inclus dans la mesure).
import http from 'k6/http';
import { check } from 'k6';
import { baseUrl, getToken, summaryTo } from './lib/common.js';

const ENDPOINT = __ENV.ENDPOINT || 'catalog';

export const options = {
  discardResponseBodies: true,
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 200),
      timeUnit: '1s',
      duration: __ENV.DURATION || '60s',
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
};

export function setup() {
  if (ENDPOINT === 'orders' && (__ENV.TARGET || 'direct') !== 'direct') return { token: getToken() };
  return {};
}

export default function (data) {
  const base = baseUrl();
  const id = 1 + Math.floor(Math.random() * 50);
  const headers = { 'X-Client-Id': `bench-${__VU}-${__ITER}` };
  let url;
  if (ENDPOINT === 'orders') {
    url = (__ENV.TARGET || 'direct') === 'direct' ? `http://orders:3000/api/orders/${id}` : `${base}/api/orders/${id}`;
    if (data.token) headers.Authorization = `Bearer ${data.token}`;
  } else {
    url = `${base}/api/catalog/${id}`;
  }
  const res = http.get(url, { headers, tags: { endpoint: ENDPOINT } });
  check(res, { 'status 200': (r) => r.status === 200 });
}

export const handleSummary = summaryTo(`latency-${ENDPOINT}`);
