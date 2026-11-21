const $ = (id) => document.getElementById(id);
let liveAvailable = false;
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
async function request(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function render(result, saved) {
  const article = node('article', undefined, 'result');
  article.append(node('h3', `Case ${result.session} · ${saved ? 'RECORDED RESULT' : 'FRESH LIVE RESULT'}`));
  article.append(node('span', result.verified ? 'Independent checks: PASS' : 'Verification did not pass', result.verified ? 'badge' : 'badge bad'));
  article.append(node('p', `Concern: ${result.case.concern}`));
  article.append(node('p', result.plaintext, 'reply'));
  article.append(node('pre', `Recovered key: a=${result.key.a}, b=${result.key.b}, inverse(a)=${result.key.a_inverse}\nEnglish-frequency score: ${Number(result.key.chi_squared).toFixed(2)}`));
  if (result.response) {
    const details = node('details'); details.append(node('summary', 'Actual encrypted request and response'));
    details.append(node('pre', JSON.stringify({request: result.request, response: result.response}, null, 2)));
    article.append(details);
  }
  if (result.run_time) article.append(node('p', `Actual live run: ${result.run_time} · ${result.model}`, 'small'));
  $('results').append(article);
}
function busy(value) {
  $('saved').disabled = value;
  $('live').disabled = value || !liveAvailable;
  $('all').disabled = value || !liveAvailable;
}
async function saved() {
  busy(true);
  try {
    const data = await request('/api/saved'); $('results').replaceChildren();
    data.results.forEach((result) => render(result, true));
    $('message').textContent = `Loaded five verified recorded sessions · ${data.model}. No API call was made.`;
  } catch (error) { $('message').textContent = error.message; }
  finally { busy(false); }
}
async function run(numbers) {
  busy(true); $('results').replaceChildren();
  try {
    for (const number of numbers) {
      $('message').textContent = `Running case ${number} live. Waiting for Gemini; do not start another lab server.`;
      const result = await request('/api/run', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Demo-Request': '1'}, body: JSON.stringify({case: number})});
      render(result, false);
      if (!result.verified) throw new Error(`Case ${number} returned text but independent verification failed.`);
    }
    $('message').textContent = 'Live tests completed and verified. Their JSON records are saved in web_runs/.';
  } catch (error) { $('message').textContent = `Live test stopped: ${error.message}. Saved evidence remains available.`; }
  finally { busy(false); }
}
$('saved').addEventListener('click', saved);
$('live').addEventListener('click', () => run([Number($('case').value)]));
$('all').addEventListener('click', () => run([1,2,3,4,5]));
async function init() {
  try {
    const status = await request('/api/status'); liveAvailable = status.live_available;
    $('status').textContent = `${status.model} · ${liveAvailable ? 'LIVE BACKEND READY' : 'SAVED-ONLY PREVIEW'}${status.capture ? ' · loopback capture enabled' : ''}`;
    status.cases.forEach((item, i) => {
      const option = node('option', `Case ${i+1} · mood ${item.mood}`); option.value = i+1; $('case').append(option);
    });
    for (let i=1; i<=5; i++) {
      const image = node('img'); image.src = `/charts/session_${i}_frequency.png`; image.alt = `Saved session ${i} frequency chart`; image.loading = 'lazy'; $('charts').append(image);
    }
    await saved();
  } catch (error) { $('message').textContent = error.message; }
}
init();
