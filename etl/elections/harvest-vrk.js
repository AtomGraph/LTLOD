// Harvests VRK's open political-campaign-finance data and Seimas candidates in a real
// browser. VRK's open-data Spinta API (https://atviriduomenys.vrk.lt/, the target of the
// data.gov.lt "Politinės kampanijos pajamos / išlaidos" and "Kandidatai" distributions)
// sits behind a Cloudflare bot challenge. In a real browser the challenge passes by
// itself, and Spinta's JSON API then works via fetch() from the page. Never script
// around the challenge. Run on
//   https://atviriduomenys.vrk.lt/datasets/gov/vrk/:ns
// either pasted into the browser console or via Claude in Chrome. The step-by-step
// procedure is the project skill .claude/skills/harvest-vrk/SKILL.md.
//
// Three models, one request each (Spinta honours limit(1000000); ~74k income rows come
// back in one response):
//   Pajamos    -> vrk-pajamos.csv             campaign income, all campaigns
//   Islaidos   -> vrk-islaidos.csv            campaign expenses, all campaigns
//   Kandidatai -> vrk-kandidatai-seimas.csv   Seimas election candidates only
// Privacy: natural-person donors keep no identity (their code, gender and age group are
// dropped), and natural-person service providers are blanked (their hash column too).
// Candidates in an election are public by law.
//
// Returns immediately and runs in the background (~1 min). Progress is in
// window.__vrkStatus ('running' | 'income' | 'expenses' | 'candidates' | 'done' |
// 'error: …'). When done, window.__vrkSizes() reports each file's rows and MB, and
// window.__vrkDownload(name) saves one file (call it once per file, after asking).
// Chrome blocks the 2nd and later script-initiated downloads from one site until the
// user allows "Automatic downloads" for atviriduomenys.vrk.lt.
// The files go to etl/elections/data/ (gitignored source files).
window.__vrkStatus = 'running';
window.__vrk = {};
window.__vrkRows = {};

window.__vrkSizes = () => Object.fromEntries(Object.keys(window.__vrk).map(name => [name, {
  rows: window.__vrkRows[name],
  mb: Math.round(window.__vrk[name].length / 1e5) / 10,
}]));

window.__vrkDownload = name => {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([window.__vrk[name]], { type: 'text/csv' }));
  a.download = name;
  a.click();
  return name;
};

(async () => {
  try {
    const json = u => fetch(u, { headers: { Accept: 'application/json' } }).then(r => {
      if (!r.ok) throw new Error(`${u}: HTTP ${r.status}`);
      return r.json();
    });
    const cell = v => v == null ? '' : /[",\n\r]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v);
    const csv = (rows, cols) => [cols.join(','), ...rows.map(r => cols.map(c => cell(r[c])).join(','))].join('\n') + '\n';
    const all = async model => {
      const data = (await json(`/datasets/gov/vrk/${model}?limit(1000000)`))._data;
      if (!data || !data.length) throw new Error(`${model}: no rows (did the challenge reappear?)`);
      return data;
    };
    const save = (name, rows, cols) => { window.__vrk[name] = csv(rows, cols); window.__vrkRows[name] = rows.length; };

    window.__vrkStatus = 'income';
    const income = await all('Pajamos');
    save('vrk-pajamos.csv', income, Object.keys(income[0]).filter(c =>
      !c.startsWith('_') && !['aukotojo_kodas', 'lytis', 'amziaus_grupe'].includes(c)));

    window.__vrkStatus = 'expenses';
    const expenses = await all('Islaidos');
    for (const r of expenses) if (r.pasl_teikejo_tipas === 'F') { r.pasl_teikejas = null; r.pasl_teikejo_vardas = null; }
    save('vrk-islaidos.csv', expenses, Object.keys(expenses[0]).filter(c =>
      !c.startsWith('_') && c !== 'pasl_teikejo_fa_hash_kodas'));

    window.__vrkStatus = 'candidates';
    const candidates = (await all('Kandidatai')).filter(r => /Seimo rinkimai/.test(r.rinkimu_pavad || ''));
    save('vrk-kandidatai-seimas.csv', candidates, Object.keys(candidates[0]).filter(c => !c.startsWith('_')));

    window.__vrkStatus = 'done';
  } catch (e) {
    window.__vrkStatus = 'error: ' + e.message;
  }
})();
'started';
