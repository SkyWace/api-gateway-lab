// Expérience DÉBIT — montée en charge par paliers jusqu'à saturation.
//   docker compose --profile tools run --rm k6 run /scripts/throughput.js -e TARGET=kong
// Lancer en parallèle : ./scripts/stats.sh <gateway> pour CPU/RAM.
// Options : MAX_RPS (défaut 3000), STEP_SECONDS (défaut 30)
// Le résumé détaille chaque palier : http_reqs{palier:X} (débit réellement obtenu) et
// http_req_duration{palier:X} (latence). Débit obtenu = count / (STEP_SECONDS + 5).
import http from 'k6/http';
import { check } from 'k6';
import { baseUrl, summaryTo } from './lib/common.js';

const MAX = Number(__ENV.MAX_RPS || 3000);
const STEP = Number(__ENV.STEP_SECONDS || 30);
const RAMP = 5;
const TARGETS = [0.1, 0.25, 0.5, 0.75, 1].map((f) => Math.round(MAX * f));

const thresholds = {};
for (const t of TARGETS) {
  thresholds[`http_req_duration{palier:${t}}`] = ['p(95)>=0'];
  thresholds[`http_reqs{palier:${t}}`] = ['count>=0'];
  thresholds[`http_req_failed{palier:${t}}`] = ['rate>=0'];
}

export const options = {
  discardResponseBodies: true,
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'max'],
  thresholds,
  scenarios: {
    ramp: {
      executor: 'ramping-arrival-rate',
      startRate: 100,
      timeUnit: '1s',
      preAllocatedVUs: 600,   // VU créés d'avance : sinon k6 perd des itérations en en allouant pendant le test
      maxVUs: 1000,
      stages: TARGETS.flatMap((t) => [
        { target: t, duration: `${RAMP}s` },   // montée
        { target: t, duration: `${STEP}s` },   // palier
      ]),
    },
  },
};

export function setup() { return { t0: Date.now() }; }

export default function (data) {
  const elapsed = (Date.now() - data.t0) / 1000;
  const idx = Math.min(TARGETS.length - 1, Math.floor(elapsed / (STEP + RAMP)));
  const res = http.get(`${baseUrl()}/api/catalog/${1 + Math.floor(Math.random() * 50)}`, {
    headers: { 'X-Client-Id': `bench-${__VU}-${__ITER}` },
    timeout: '10s',
    tags: { palier: String(TARGETS[idx]) },
  });
  check(res, { 'status 200': (r) => r.status === 200 });
}

export const handleSummary = summaryTo('throughput');
