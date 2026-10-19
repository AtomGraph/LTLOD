// Harvests VMI's public annual property declaration extracts (FR0001) for politician
// position groups, in a real browser: vmi.lt sits behind a Cloudflare bot challenge and
// rejects datacenter/VPN IPs, so there is no scripted fetch. Run once a year (VMI
// publishes the previous year's extracts by 1 October) on
//   https://www.vmi.lt/evmi/metines-gyventojo-seimos-turto-deklaracijos-duomenu-israsai
// either pasted into the browser console or via Claude in Chrome — the step-by-step
// procedure is the project skill .claude/skills/harvest-declarations/SKILL.md.
//
// The page embeds the search app (https://www.vmi.lt/TPP/fr0001/default.aspx) in an
// iframe; each query (reporting year x position group) reloads the bare form, submits
// it and parses the result list. VMI shows a result only when <= 200 persons match, so
// only groups below that cap per year are harvestable this way (511, municipal council
// members, is not; 588, spouses, is deliberately skipped: private persons).
//
// Returns immediately and runs in the background (~84 queries, ~10 min); progress is
// in window.__hstatus ('running' | 'done' | 'error: …') and window.__hlog. Queries
// already in window.__harvest are skipped, so re-running resumes after an error.
// When done, window.__harvestDownload() saves vmi-fr0001-harvest.json, which goes to
// etl/declarations/data/vmi-fr0001.json.
window.__harvest = window.__harvest || {};
window.__hlog = window.__hlog || [];
window.__hstatus = 'running';

window.__harvestDownload = () => {
  const harvest = window.__harvest;
  // compact: category labels once, items as [labelIndex, value]
  const labels = [...new Set(Object.values(harvest).flatMap(v => v.people.flatMap(p => p.items.map(i => i[0]))))];
  const out = { source: 'https://www.vmi.lt/TPP/fr0001/default.aspx', harvested: new Date().toISOString(), labels, queries: {} };
  for (const k of Object.keys(harvest).sort()) {
    out.queries[k] = {
      found: harvest[k].found,
      people: harvest[k].people.map(p => [p.name, p.group, p.year, p.firstFiled, p.updated,
        p.items.map(([l, v]) => [labels.indexOf(l), v])]),
    };
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: 'application/json' }));
  a.download = 'vmi-fr0001-harvest.json';
  document.body.appendChild(a);
  a.click();
  return { queries: Object.keys(out.queries).length, labels: labels.length,
           people: Object.values(harvest).reduce((n, v) => n + v.people.length, 0) };
};

(async () => {
  const GROUPS = ['506', '505', '510', '502', '519', '536'];
  const FIRST_YEAR = 2012;
  const fr = document.querySelector('iframe');
  const FORM = 'https://www.vmi.lt/TPP/fr0001/default.aspx';
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const loaded = () => new Promise(r => fr.addEventListener('load', r, { once: true }));

  function parse(d) {
    const txt = d.body.innerText;
    const m = txt.match(/Rasta asmenų:\s*(\d+)/);
    const lines = txt.split('\n').map(s => s.trim()).filter(Boolean);
    const people = [];
    let cur = null;
    for (let i = 0; i < lines.length; i++) {
      const l = lines[i];
      if (lines[i + 1] && lines[i + 1].startsWith('Pareigybių grupė:')) {
        cur = { name: l, group: lines[i + 1].replace('Pareigybių grupė:', '').trim(), items: [] };
        people.push(cur);
        i++;
        continue;
      }
      if (!cur) continue;
      const y = l.match(/^Ataskaitiniai metai:\s*(\d{4}), duomenys pateikti pirmą kartą:\s*([\d-]+), aktualūs duomenys pateikti:\s*([\d-]+)/);
      if (y) { cur.year = +y[1]; cur.firstFiled = y[2]; cur.updated = y[3]; continue; }
      const kv = l.match(/^(.+?)\t\s*(-?[\d\s.,]+)$/);
      if (kv) cur.items.push([kv[1].trim(), kv[2].replace(/\s/g, '')]);
    }
    return { found: m ? +m[1] : null, people };
  }

  try {
    if (!fr) throw new Error('no search iframe on this page — open the FR0001 extracts page');
    // the newest reporting year VMI offers (the year dropdown of the bare form)
    let p = loaded(); fr.src = `${FORM}?r=${Date.now()}`; await p;
    const years = [...fr.contentDocument.querySelector('[name=ddMetai]').options]
      .map(o => +o.value).filter(v => v > 0);
    const lastYear = Math.max(...years);
    for (const g of GROUPS) {
      for (let y = lastYear; y >= FIRST_YEAR; y--) {
        const key = `${g}-${y}`;
        if (window.__harvest[key]) continue;
        p = loaded(); fr.src = `${FORM}?r=${Date.now()}`; await p;
        const d = fr.contentDocument;
        if (!d.querySelector('[name=ddMetai]')) throw new Error(`${key}: search form missing (challenge page?)`);
        d.querySelector('[name=ddMetai]').value = String(y);
        d.querySelector('[name=ddPareigGr]').value = g;
        p = loaded(); d.querySelector('[name=butIeskoti]').click(); await p;
        const res = parse(fr.contentDocument);
        if (res.found !== null && res.found !== res.people.length)
          throw new Error(`${key}: VMI found ${res.found}, parsed ${res.people.length} — page layout changed?`);
        window.__harvest[key] = res;
        window.__hlog.push(`${key}: ${res.people.length}`);
        await sleep(1200);
      }
    }
    window.__hstatus = 'done';
  } catch (e) {
    window.__hstatus = `error: ${e.message}`;
  }
})();
'started';
