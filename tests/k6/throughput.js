// Expérience DÉBIT — montée en charge par paliers jusqu'à saturation.
//   docker compose --profile tools run --rm k6 run /scripts/throughput.js -e TARGET=apisix
// Lancer en parallèle : ./scripts/stats.sh <gateway> pour CPU/RAM.
// Options : MAX_RPS (défaut 3000), STEP_DURATION (défaut 30s)
import http from 'k6/http';
import { check } from 'k6';
import { baseUrl, summaryTo } from './lib/common.js';

const MAX = Number(__ENV.MAX_RPS || 3000);
const STEP = __ENV.STEP_DURATION || '30s';

export const options = {
  discardResponseBodies: true,
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
  scenarios: {
    ramp: {
      executor: 'ramping-arrival-rate',
      startRate: 100,
      timeUnit: '1s',
      preAllocatedVUs: 200,
      maxVUs: 1000,
      stages: [0.1, 0.25, 0.5, 0.75, 1].flatMap((f) => [
        { target: Math.round(MAX * f), duration: '5s' },   // montée
        { target: Math.round(MAX * f), duration: STEP },   // palier
      ]),
    },
  },
};

export default function () {
  const id = 1 + Math.floor(Math.random() * 50);
  const res = http.get(`${baseUrl()}/api/catalog/${id}`, {
    headers: { 'X-Client-Id': `bench-${__VU}-${__ITER}` },
    timeout: '10s',
  });
  check(res, { 'status 200': (r) => r.status === 200 });
}

export const handleSummary = summaryTo('throughput');
