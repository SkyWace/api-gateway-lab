// Expérience SERVICE INDISPONIBLE — trafic continu pendant qu'on casse un backend.
//   Terminal 1 : docker compose --profile tools run --rm k6 run /scripts/resilience.js -e TARGET=kong -e ENDPOINT=catalog
//   Terminal 2 : ./scripts/chaos.sh kill-catalog2   (ou errors-orders / slow-orders / kill-orders)
// La série temporelle (statut + durée par requête) est exportée en CSV pour tracer le graphique.
//   ENDPOINT=catalog : 2 instances -> on observe le failover (health checks, retries)
//   ENDPOINT=orders  : 1 instance  -> on observe timeout / circuit breaker / code renvoyé
import http from 'k6/http';
import { Counter } from 'k6/metrics';
import { baseUrl, getToken, summaryTo } from './lib/common.js';

const ENDPOINT = __ENV.ENDPOINT || 'catalog';
const byStatus = new Counter('responses_by_status');

export const options = {
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
  scenarios: {
    steady: { executor: 'constant-arrival-rate', rate: Number(__ENV.RATE || 20), timeUnit: '1s', duration: __ENV.DURATION || '120s', preAllocatedVUs: 50, maxVUs: 200 },
  },
};

export function setup() {
  return ENDPOINT === 'orders' ? { token: getToken() } : {};
}

export default function (data) {
  const headers = { 'X-Client-Id': `res-${__VU}-${__ITER}` };
  if (data.token) headers.Authorization = `Bearer ${data.token}`;
  const res = http.get(`${baseUrl()}/api/${ENDPOINT}/1`, { headers, timeout: '15s' });
  byStatus.add(1, { status: String(res.status), instance: res.headers['X-Instance'] || 'none' });
  // Ligne CSV exploitée par scripts/csv-from-log.sh : t_ms;status;duration_ms;instance
  console.log(`CSV;${Date.now()};${res.status};${res.timings.duration.toFixed(1)};${res.headers['X-Instance'] || 'none'}`);
}

export const handleSummary = summaryTo(`resilience-${ENDPOINT}`);
