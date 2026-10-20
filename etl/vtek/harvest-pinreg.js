// Harvests the public private-interest declarations of politicians from VTEK's Private
// Interests Register PINREG (https://pinreg.vtek.lt/) in a real browser: the host is behind
// a Cloudflare challenge, and its search is gated by the app's own (invisible) reCAPTCHA, so
// there is no scripted fetch. Run on https://pinreg.vtek.lt/app/deklaraciju-paieska, pasted
// into the console or via Claude in Chrome; the step-by-step procedure is
// .claude/skills/harvest-vtek/SKILL.md. It is a two-phase harvest:
//
// 1. SEARCH, through the app's own UI (never scripted: the app runs its reCAPTCHA). This
//    script hooks fetch/XHR and records every page of /external/deklaracijos/viesa results
//    the app receives; the operator ticks the position groups (GROUPS below) in
//    "Pagrindinių pareigų pobūdis", clicks IEŠKOTI and pages through to the last page.
//    window.__pinregRows() reports {rows, total} — they must match before phase 2.
// 2. DETAILS: window.__pinregDetails() GETs /external/deklaracijos/{accessUuid}/view/viesa
//    (plain JSON, no token) for every row not yet harvested, ONE REQUEST EVERY 15 s: a polite
//    pace, about an hour for a full run. On HTTP 403 / cf-mitigated it STOPS (never retries
//    through a challenge): let the browser pass the challenge normally, then call it again —
//    finished declarations are kept. Progress: window.__pinregStatus / window.__pinregLog.
//
// Only the declarant's OWN data is kept: name, workplaces and legal-entity ties whose
// kienoRysys is ASMENINIS. Dropped at harvest, never stored: the spouse/partner (sutuoktinis,
// sutuoktinioDarbovietes, kienoRysys PARTNERIO), personal code and birth date, transactions
// (rysiaiDelSandoriu), ties with natural persons (deklaracijosFaRysiai) and the other free-text
// sections. window.__pinregLoad(previousJson) seeds a previous pinreg.json (a partial run) so
// its declarations are kept and only the rest is fetched; window.__pinregDownload() saves
// pinreg.json (-> etl/vtek/data/pinreg.json) with "complete" and the still-"pending" ids.
// var, not const: the script may be pasted again into the same page (re-declaration is fine)
var GROUPS = ['Europos Parlamento narys', 'Meras', 'Ministras pirmininkas, ministras',
                'Respublikos Prezidentas', 'Seimo pirmininkas, Seimo narys'];
window.__pinreg = window.__pinreg || { rows: {}, total: null, declarations: {} };  // accessUuid -> row / declaration
window.__pinregLog = window.__pinregLog || [];
window.__pinregStatus = window.__pinregStatus || 'search: tick the groups, IEŠKOTI, page to the end';

(() => {
  if (window.__pinregHooked) return;
  window.__pinregHooked = true;
  const SEARCH = /\/external\/deklaracijos\/viesa(\?|$)/;
  const record = json => {
    if (!json || !Array.isArray(json.content)) return;
    for (const r of json.content) window.__pinreg.rows[r.accessUuid] = r;
    window.__pinreg.total = json.totalElements;
    window.__pinregLog.push(`search page ${json.number + 1}/${json.totalPages}: +${json.content.length}`);
  };
  const origFetch = window.fetch;
  window.fetch = async (...args) => {
    const res = await origFetch(...args);
    const url = String(args[0] && args[0].url || args[0]);
    if (SEARCH.test(url)) res.clone().json().then(record).catch(() => {});
    return res;
  };
  const origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    if (SEARCH.test(String(url)))
      this.addEventListener('load', () => { try { record(JSON.parse(this.responseText)); } catch (e) { /* not JSON */ } });
    return origOpen.call(this, method, url, ...rest);
  };
})();

window.__pinregRows = () => ({ rows: Object.keys(window.__pinreg.rows).length, total: window.__pinreg.total });

window.__pinregLoad = previous => {
  for (const d of previous.declarations || []) window.__pinreg.declarations[d.accessUuid] = d;
  return Object.keys(window.__pinreg.declarations).length;
};

var keep = (row, j) => ({
  accessUuid: row.accessUuid, submitted: j.pateikimoData, latest: j.yraNaujausiaVersija, type: j.deklaracijosTipas,
  reasons: j.teikimoPriezastysPavadinimai,
  declarant: { givenName: j.teikejas.vardas, familyName: j.teikejas.pavarde },
  listedPosition: row.pareiguPobudisPavadinimas, listedWorkplace: row.darbovietesPavadinimas,
  workplaces: (j.darbovietes || []).map(w => ({ jaKodas: w.jaKodas, name: w.pavadinimas,
    legalForm: w.jaTeisinesFormosPavadinimas, since: w.rysioPradzia, type: w.darbovietesTipas, position: w.pareigos })),
  legalEntityTies: (j.rysiaiSuJa || []).filter(t => t.kienoRysys === 'ASMENINIS')
    .map(t => ({ jaKodas: t.jaKodas, name: t.pavadinimas, registeredInLithuania: t.registruotaLietuvoje,
      legalForm: t.jaTeisinesFormosPavadinimas, legalFormCode: t.jaTeisinesFormosKodas,
      nature: t.rysioPobudzioPavadinimas, since: t.rysioPradzia, until: t.rysioPabaiga,
      inPublicProcurement: t.dalyvaujaViesuosePirkimuose, procurementInfo: t.dalyvavimoVpInformacija,
      notes: t.pastabos })),
});

window.__pinregDetails = (spacingMs = 15000) => {
  window.__pinregStatus = 'details: running';
  (async () => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const todo = Object.values(window.__pinreg.rows).filter(r => !window.__pinreg.declarations[r.accessUuid]);
    try {
      for (const row of todo) {
        const r = await fetch(`/external/deklaracijos/${row.accessUuid}/view/viesa`,
                              { credentials: 'same-origin', headers: { Accept: 'application/json' } });
        if (r.status === 403 || r.headers.get('cf-mitigated'))
          throw new Error(`Cloudflare challenge (HTTP ${r.status}) after ${window.__pinregLog.length} log lines — `
                          + 'stop, let the browser pass it, call __pinregDetails() again later');
        if (!r.ok) throw new Error(`${row.accessUuid}: HTTP ${r.status}`);
        window.__pinreg.declarations[row.accessUuid] = keep(row, await r.json());
        window.__pinregLog.push(`detail ${Object.keys(window.__pinreg.declarations).length}/${window.__pinregRows().rows}`);
        await sleep(spacingMs);
      }
      window.__pinregStatus = 'done';
    } catch (e) {
      window.__pinregStatus = `error: ${e.message}`;
    }
  })();
  return `details: ${Object.values(window.__pinreg.rows).filter(r => !window.__pinreg.declarations[r.accessUuid]).length} to fetch`;
};

window.__pinregDownload = () => {
  const done = window.__pinreg.declarations;
  const rows = Object.keys(window.__pinreg.rows);
  const pending = rows.filter(id => !done[id]);
  const out = { source: 'https://pinreg.vtek.lt/', harvested: new Date().toISOString(),
                complete: rows.length > 0 && pending.length === 0 && rows.length === window.__pinreg.total,
                groups: GROUPS, pending, declarations: Object.values(done) };
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: 'application/json' }));
  a.download = 'pinreg.json';
  document.body.appendChild(a);
  a.click();
  return { declarations: out.declarations.length, pending: pending.length, complete: out.complete };
};
'hooked';
