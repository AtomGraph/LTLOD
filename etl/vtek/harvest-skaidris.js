// Harvests VTEK's public lobbying register SKAIDRIS (https://skaidris.vtek.lt/) in a real
// browser: the host is behind a Cloudflare challenge, so there is no scripted fetch. Run
// on https://skaidris.vtek.lt/public/home/main, pasted into the console or via Claude in
// Chrome; the step-by-step procedure is .claude/skills/harvest-vtek/SKILL.md.
//
// Three public lists, paged 100 at a time through the app's own JSON endpoints, with the
// app's own same-site CSRF header (X-XSRF-TOKEN from the XSRF-TOKEN cookie), exactly as the
// Angular app sends it. No reCAPTCHA is involved.
//   lobbyists     POST /action/public/lobbyist    (registered lobbyists, active + blocked)
//   transparency  POST /action/public/documents   (lobbyists' transparency declarations)
//   influence     POST /action/public/documents   (officials' experienced-influence declarations)
//
// Returns immediately and runs in the background (~30 requests, 1.5 s apart); progress is
// in window.__skStatus ('running' | 'done' | 'error: …') and window.__skLog. Pages already
// fetched are kept, so re-running resumes after an error. NEVER retry through a Cloudflare
// challenge (HTTP 403 / cf-mitigated): the script stops, and the user's browser must pass
// the challenge normally before re-running.
// When done, window.__skDownload() saves skaidris.json (compacted, ~4 MB instead of ~40 MB
// of app metadata), which goes to etl/vtek/data/skaidris.json.
window.__sk = window.__sk || { lobbyists: {}, transparency: {}, influence: {} };  // key -> {page -> list}
window.__skPages = window.__skPages || {};  // key -> page count reported by the server
window.__skLog = window.__skLog || [];
window.__skStatus = 'running';

window.__skDownload = () => {
  // a declaration's fieldList is a tree of {structureField: {name}, value: {stringValue |
  // valueList | booleanValue …}, fieldList}: flatten to {fieldName: value}; JSON-looking
  // strings are parsed, repeated names (influencedPerson) become arrays
  const fname = f => (f.structureField || {}).name || '?';
  const fval = f => {
    const v = f.value || {};
    let s = v.stringValue;
    if (s != null && /^[\[{]/.test(s)) { try { s = JSON.parse(s); } catch (e) { /* keep the string */ } }
    const kids = (f.fieldList || []).length ? flat(f.fieldList) : null;
    if (kids) return s != null && s !== '' ? { value: s, fields: kids } : kids;
    return s != null && s !== '' ? s
      : (v.valueList && v.valueList.length ? v.valueList : (v.booleanValue ?? v.numberValue ?? v.dateValue ?? null));
  };
  const flat = list => {
    const o = {};
    for (const f of list || []) {
      const k = fname(f), x = fval(f);
      if (x == null) continue;
      if (k in o) o[k] = [].concat(o[k], [x]); else o[k] = x;
    }
    return o;
  };
  const doc = d => ({ id: d.id, name: d.name, type: d.type && d.type.name, status: d.resourceStatusEnum,
                      created: d.createdDate, modified: d.lastModifiedDate, fields: flat(d.fieldList) });
  // lobbyists are flat records: drop internal keys (owner/representative ids, history, access)
  const INTERNAL = /^(ownerUuid|representativeUuid|access.*|.*[hH]istory.*)$/;
  const lobbyist = l => Object.fromEntries(Object.entries(l).filter(([k]) => !INTERNAL.test(k)));
  const all = key => Object.keys(window.__sk[key]).sort((a, b) => a - b).flatMap(p => window.__sk[key][p]);
  const out = { source: 'https://skaidris.vtek.lt/', harvested: new Date().toISOString(),
                lobbyists: all('lobbyists').map(lobbyist),
                transparency: all('transparency').map(doc), influence: all('influence').map(doc) };
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: 'application/json' }));
  a.download = 'skaidris.json';
  document.body.appendChild(a);
  a.click();
  return { lobbyists: out.lobbyists.length, transparency: out.transparency.length, influence: out.influence.length };
};

(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const xsrf = () => decodeURIComponent((document.cookie.match(/(?:^|; )XSRF-TOKEN=([^;]*)/) || [])[1] || '');
  const post = async (url, body) => {
    const r = await fetch(url, { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'locale': 'lt', 'X-XSRF-TOKEN': xsrf() },
      body: JSON.stringify(body) });
    if (r.status === 403 || r.headers.get('cf-mitigated'))
      throw new Error(`${url}: Cloudflare challenge (HTTP ${r.status}) — let the browser pass it, then re-run`);
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    const j = await r.json();
    if (j.type !== 'success') throw new Error(`${url}: ${j.type} ${j.text}`);
    return j.details;  // {pageSize, pageCount, totalElements, list}
  };
  const SETS = {
    lobbyists: ['/action/public/lobbyist', { resourceStatusEnumList: ['ACTIVE', 'BLOCKED'], viewType: 1,
      offenderType: 'LOBBYIST', orderBy: 'name', sortingOrder: 'asc' }],
    transparency: ['/action/public/documents', { dateRange: {}, documentTypeName: 'Lobisto skaidrumo deklaracija',
      viewType: 10, resourceStatusEnum: 'SUBMITTED', fieldMap: {},
      sortingOrderList: [{ fieldName: 'fieldMap.executionDate', sortingOrder: 'desc' }] }],
    influence: ['/action/public/documents', { dateRange: {}, documentTypeName: 'Asmens, patyrusio lobistinę įtaką, deklaracija',
      viewType: 26, resourceStatusEnum: 'SUBMITTED', fieldMap: { lobbyist_notFound: { booleanValue: true, not: true } },
      orderBy: 'name', sortingOrder: 'desc' }],
  };
  try {
    if (location.host !== 'skaidris.vtek.lt') throw new Error('open https://skaidris.vtek.lt/public/home/main first');
    for (const [key, [url, base]] of Object.entries(SETS)) {
      for (let page = 1; ; page++) {
        if (!window.__sk[key][page]) {
          const d = await post(url, { ...base, page, pageSize: 100 });
          window.__sk[key][page] = d.list || [];
          window.__skPages[key] = d.pageCount || 1;
          window.__skLog.push(`${key} p${page}/${window.__skPages[key]} +${(d.list || []).length} (total ${d.totalElements})`);
          await sleep(1500);
        }
        if (!window.__sk[key][page].length || page >= window.__skPages[key]) break;
      }
    }
    window.__skStatus = 'done';
  } catch (e) {
    window.__skStatus = `error: ${e.message}`;
  }
})();
'started';
