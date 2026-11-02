// Expérience RÉPARTITION — 1000 requêtes sur /api/catalog, comptage par instance (en-tête X-Instance).
//   docker compose --profile tools run --rm k6 run /scripts/loadbalancing.js -e TARGET=scg
import http from 'k6/http';
import { Counter } from 'k6/metrics';
import { baseUrl, summaryTo } from './lib/common.js';

const perInstance = new Counter('hits');

export const options = {
  discardResponseBodies: true,
  scenarios: { lb: { executor: 'shared-iterations', vus: 10, iterations: Number(__ENV.N || 1000) } },
  thresholds: {
    'hits{instance:catalog-1}': ['count>=0'],
    'hits{instance:catalog-2}': ['count>=0'],
    'hits{instance:none}': ['count>=0'],
  },
};

export default function () {
  const res = http.get(`${baseUrl()}/api/catalog/1`, { headers: { 'X-Client-Id': `lb-${__VU}-${__ITER}` } });
  perInstance.add(1, { instance: res.headers['X-Instance'] || 'none' });
}

export const handleSummary = summaryTo('loadbalancing');
