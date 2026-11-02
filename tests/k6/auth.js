// Expérience AUTHENTIFICATION — matrice de cas, résultat attendu vs obtenu.
//   docker compose --profile tools run --rm k6 run /scripts/auth.js -e TARGET=apisix
import http from 'k6/http';
import { check } from 'k6';
import encoding from 'k6/encoding';
import { baseUrl, getToken, summaryTo } from './lib/common.js';

export const options = { vus: 1, iterations: 1 };

export function setup() { return { token: getToken() }; }

function forge(token, mutate) {
  const [h, p, s] = token.split('.');
  const payload = JSON.parse(encoding.b64decode(p, 'rawurl', 's'));
  mutate(payload);
  return `${h}.${encoding.b64encode(JSON.stringify(payload), 'rawurl')}.${s}`;
}

export default function (data) {
  const url = `${baseUrl()}/api/orders/1`;
  const t = data.token;
  const [h, p] = t.split('.');
  const cases = [
    ['public catalog sans token -> 200', `${baseUrl()}/api/catalog/1`, null, 200],
    ['orders sans token -> 401', url, null, 401],
    ['orders token valide -> 200', url, `Bearer ${t}`, 200],
    ['orders token malformé -> 401', url, 'Bearer abc.def', 401],
    ['orders signature altérée -> 401', url, `Bearer ${h}.${p}.AAAA`, 401],
    ['orders payload modifié (sub) -> 401', url, `Bearer ${forge(t, (x) => { x.sub = 'admin'; })}`, 401],
    ['orders exp modifié (signature cassée) -> 401', url, `Bearer ${forge(t, (x) => { x.exp = 1000; })}`, 401],
    ['orders alg=none -> 401', url, `Bearer ${encoding.b64encode('{"alg":"none","typ":"JWT"}', 'rawurl')}.${p}.`, 401],
    ['orders schéma Basic -> 401', url, 'Basic YWxpY2U6YWxpY2U=', 401],
  ];
  for (const [name, u, auth, expected] of cases) {
    const headers = { 'X-Client-Id': 'auth-test' };
    if (auth) headers.Authorization = auth;
    const res = http.get(u, { headers });
    const ok = check(res, { [name]: (r) => r.status === expected });
    console.log(`${ok ? 'OK ' : 'KO '} ${name} | obtenu=${res.status} | www-authenticate=${res.headers['Www-Authenticate'] || '-'}`);
  }
}

export const handleSummary = summaryTo('auth');
