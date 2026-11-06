const $ = (id) => document.getElementById(id);
let lastResult = null;
function esc(value) { return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function percent(value) { return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'; }
function number(value, suffix='') { return typeof value === 'number' ? `${value.toLocaleString(undefined,{maximumFractionDigits:2})}${suffix}` : '—'; }
function money(value) { return typeof value === 'number' ? `$${value.toFixed(5)}` : 'Not configured'; }
function showToast(message, error=false) { const el=$('toast'); el.textContent=message; el.classList.remove('hidden','error'); if(error)el.classList.add('error'); setTimeout(()=>el.classList.add('hidden'),4200); }
async function api(path, options={}) {
  const response = await fetch(path, {headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
  let data; try { data=await response.json(); } catch { data={detail:await response.text()}; }
  if(!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data;
}
function setBusy(button,busy,label) { button.disabled=busy; if(busy){button.dataset.oldText=button.textContent;button.textContent=label||'Working…';}else if(button.dataset.oldText){button.textContent=button.dataset.oldText;delete button.dataset.oldText;} }
function metricCard(label,value,note='') { return `<div class="metric-card"><div class="metric-label">${esc(label)}</div><div class="metric-value">${esc(value)}</div><div class="metric-note">${esc(note)}</div></div>`; }
function renderMetrics(metrics) {
  $('run-metrics').innerHTML = [
    metricCard('Groundedness',percent(metrics.groundedness),'Claims supported by evidence'),
    metricCard('Evidence coverage',percent(metrics.evidence_coverage),'Claims linked to evidence'),
    metricCard('Citation validity',percent(metrics.citation_validity),'Answer citations resolving to retrieved evidence'),
    metricCard('Pipeline execution',metrics.pipeline_execution_success===true?'Passed':metrics.pipeline_execution_success===false?'Failed':'—','Agent and MCP execution status'),
    metricCard('Retrieval',metrics.retrieval_success===true?'Evidence found':metrics.retrieval_success===false?'No evidence':'—','Whether relevant source records were returned'),
    metricCard('Unsupported claims',percent(metrics.hallucination_rate),'Unsupported or contradicted claims'),
    metricCard('Latency',number(metrics.latency_ms,' ms'),'End-to-end measured time'),
    metricCard('Model retries',number(metrics.model_retries),'Additional attempts after transient errors'),
    metricCard('Retry wait',number(metrics.retry_wait_ms,' ms'),'Time spent in retry backoff'),
    metricCard('Total tokens',number(metrics.total_tokens),'Reported by model API'),
    metricCard('Estimated cost',money(metrics.estimated_cost_usd),'Only shown when rates are configured'),
    metricCard('MCP tools',`${metrics.tool_successes ?? 0}/${metrics.tool_calls ?? 0}`,'Successful calls / total calls'),
    metricCard('Model calls',number(metrics.model_calls),'Recorded model requests')
  ].join('');
}
function renderResearch(result) {
  lastResult=result;
  $('research-empty').classList.add('hidden');
  $('research-results').classList.remove('hidden');
  $('run-id').textContent='';
  $('run-caption').textContent=new Date(result.created_at||Date.now()).toLocaleString();
  $('answer-text').textContent=result.answer || 'No research output was returned.';
  $('answer-status').textContent=result.warnings?.length ? 'Completed with warnings' : 'Completed';
  $('answer-status').classList.toggle('warning',!!result.warnings?.length);
  const warnings=result.warnings||[];
  $('warnings').classList.toggle('hidden',!warnings.length);
  $('warnings').textContent=warnings.join('\n');
}
async function checkHealth() {
  try { const h=await api('/health');$('api-dot').classList.add('good');$('api-status').textContent='API connected';$('sidebar-status').textContent='API connected'; }
  catch(e){$('api-status').textContent='API unavailable';$('sidebar-status').textContent='Start the Python server';$('api-dot').classList.remove('good');}
}
function goPage(page) {
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
  document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.id===`page-${page}`));
  $('page-title').textContent=({research:'Research',evaluation:'Evaluation',documents:'Documents & MCP'})[page]||'Research';
  if(page==='evaluation'){loadMetrics();}
}
document.querySelectorAll('.nav-item').forEach(button=>button.addEventListener('click',()=>goPage(button.dataset.page)));
$('run-button').addEventListener('click',async()=>{
  const question=$('question').value.trim();if(question.length<5){showToast('Enter a research question of at least 5 characters.',true);return;}
  const button=$('run-button');setBusy(button,true,'Agents are working…');$('research-empty').classList.remove('hidden');$('research-empty').querySelector('h3').textContent='Research in progress';$('research-empty').querySelector('p').textContent='Planning, retrieving evidence, verifying claims, and writing the answer.';$('research-results').classList.add('hidden');
  try { const result=await api('/query',{method:'POST',body:JSON.stringify({question,mode:'multi_agent'})});renderResearch(result);showToast('Research run completed.'); }
  catch(e){$('research-empty').querySelector('h3').textContent='The run could not complete';$('research-empty').querySelector('p').textContent=e.message;showToast(e.message,true);}
  finally {setBusy(button,false);}
});
$('question').addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter')$('run-button').click();});
async function loadMetrics() {
  const container=$('aggregate-metrics');container.innerHTML='<div class="loading-card">Loading measured metrics…</div>';
  try {const data=await api('/metrics');if(!data.run_count){container.innerHTML='<div class="loading-card">No runs recorded yet. Run research first; metrics will appear here.</div>';return;}
    const stageCards=Object.entries(data.mean_stage_latencies_ms||{}).map(([stage,value])=>metricCard(`Stage: ${stage}`,number(value,' ms'),'Average stage duration in recent runs'));
    container.innerHTML=[metricCard('Recorded runs',number(data.run_count),'All saved workflow logs'),metricCard('Task success',percent(data.task_success_rate),'Average run outcome in recent runs'),metricCard('Mean groundedness',percent(data.mean_groundedness),'From recorded claim checks'),metricCard('Retrieval success',percent(data.retrieval_success_rate),'Runs that returned source evidence'),metricCard('Agent completion',percent(data.mean_agent_completion_rate),'Expected stages completed per run'),metricCard('MCP tool success',percent(data.tool_success_rate),'Successful calls / total calls'),metricCard('Mean latency (recent)',number(data.mean_latency_ms,' ms'),data.metrics_window||'End-to-end time'),metricCard('Latest run latency',number(data.latest_latency_ms,' ms'),'Most recent research request'),...stageCards].join('');
  } catch(e){container.innerHTML=`<div class="loading-card">Could not load metrics: ${esc(e.message)}</div>`;}
}
checkHealth();
