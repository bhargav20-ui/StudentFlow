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
    metricCard('Unsupported claims',percent(metrics.hallucination_rate),'Unsupported or contradicted claims'),
    metricCard('Latency',number(metrics.latency_ms,' ms'),'End-to-end measured time'),
    metricCard('Total tokens',number(metrics.total_tokens),'Reported by model API'),
    metricCard('Estimated cost',money(metrics.estimated_cost_usd),'Only shown when rates are configured'),
    metricCard('MCP tools',`${metrics.tool_successes ?? 0}/${metrics.tool_calls ?? 0}`,'Successful calls / total calls'),
    metricCard('Model calls',number(metrics.model_calls),'Recorded model requests')
  ].join('');
}
function renderResearch(result) {
  lastResult=result;
  $('research-empty').classList.add('hidden');$('research-results').classList.remove('hidden');
  $('run-id').textContent=result.run_id || '';$('run-caption').textContent=`${result.mode==='single_agent'?'Single-agent baseline':'Multi-agent + MCP'} · ${new Date(result.created_at||Date.now()).toLocaleString()}`;
  $('answer-text').textContent=result.answer || 'No answer returned.';
  $('answer-status').textContent=result.warnings?.length?'Completed with warnings':'Completed';$('answer-status').classList.toggle('warning',!!result.warnings?.length);
  const warnings=result.warnings||[];$('warnings').classList.toggle('hidden',!warnings.length);$('warnings').textContent=warnings.join('\n');
  renderMetrics(result.metrics||{});
  const events=result.events||[];
  $('workflow-list').innerHTML=events.length?events.map((event,i)=>`<div class="workflow-item"><span class="workflow-line ${esc(event.status||'')}"></span><div><div class="workflow-name">${esc(event.agent||`Stage ${i+1}`)}</div><div class="workflow-message">${esc(event.message||'Stage recorded')}</div></div><div class="workflow-time">${number(event.latency_ms,' ms')}</div></div>`).join(''):'<p class="muted">No workflow trace was recorded.</p>';
  const evidence=result.evidence||[];$('evidence-count').textContent=`${evidence.length} sources`;
  $('evidence-list').innerHTML=evidence.length?evidence.map(item=>`<div class="evidence-item"><div class="evidence-title">${esc(item.title||item.document_id)}</div><div class="evidence-meta">${esc(item.evidence_id||'')} · ${esc(item.document_id||'')} · relevance ${esc(item.relevance??'—')}</div><div class="evidence-text">${esc(item.text||'')}</div></div>`).join(''):'<p class="muted">No relevant evidence was retrieved. The system should not guess missing facts.</p>';
  const claims=result.claims||[];$('claim-count').textContent=`${claims.length} claims`;
  $('claims-list').innerHTML=claims.length?claims.map(claim=>`<div class="claim-item"><div><div class="claim-text">${esc(claim.statement||'Claim')}</div><div class="claim-reason">${esc(claim.reason||'')} ${claim.evidence_ids?.length?`· Evidence: ${esc(claim.evidence_ids.join(', '))}`:'· No evidence IDs'}</div></div><span class="claim-status ${esc(String(claim.status||'unsupported').toLowerCase())}">${esc(claim.status||'UNASSESSED')}</span></div>`).join(''):'<p class="muted">No structured claims were returned for verification.</p>';
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
  if(page==='documents'){loadDocuments();loadTools();}
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
    container.innerHTML=[metricCard('Recorded runs',number(data.run_count),'Completed workflow logs'),metricCard('Task success',percent(data.task_success_rate),'Average recorded run outcome'),metricCard('Mean groundedness',percent(data.mean_groundedness),'From recorded claim checks'),metricCard('Mean unsupported claims',percent(data.mean_hallucination_rate),'Unsupported / contradicted'),metricCard('MCP tool success',percent(data.tool_success_rate),'Successful calls / total calls'),metricCard('Mean latency',number(data.mean_latency_ms,' ms'),'End-to-end time'),metricCard('P95 latency',number(data.p95_latency_ms,' ms'),'95th-percentile recorded run'),metricCard('Mean tokens',number(data.mean_tokens),'Model-reported usage')].join('');
  } catch(e){container.innerHTML=`<div class="loading-card">Could not load metrics: ${esc(e.message)}</div>`;}
}
$('compare-button').addEventListener('click',async()=>{
  const question=$('compare-question').value.trim();if(question.length<5){showToast('Enter a question to compare.',true);return;}
  const button=$('compare-button');setBusy(button,true,'Running both approaches…');$('compare-output').textContent='The single-agent baseline and multi-agent workflow will each run once.';
  try{const result=await api('/comparison',{method:'POST',body:JSON.stringify({question})});const b=result.baseline.metrics||{},m=result.multi_agent.metrics||{};
    const rows=[['Groundedness',percent(b.groundedness),percent(m.groundedness)],['Evidence coverage',percent(b.evidence_coverage),percent(m.evidence_coverage)],['Unsupported claims',percent(b.hallucination_rate),percent(m.hallucination_rate)],['Latency',number(b.latency_ms,' ms'),number(m.latency_ms,' ms')],['Tokens',number(b.total_tokens),number(m.total_tokens)],['Estimated cost',money(b.estimated_cost_usd),money(m.estimated_cost_usd)]];
    $('compare-output').innerHTML=`<div class="table-wrap"><table><thead><tr><th>Metric</th><th>Single-agent baseline</th><th>Multi-agent + MCP</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r[0])}</td><td>${esc(r[1])}</td><td>${esc(r[2])}</td></tr>`).join('')}</tbody></table></div><p class="muted">This is one measured comparison, not a statistically reliable conclusion. Repeat across the same test set before claiming improvement.</p><button id="show-multi-result" class="secondary">View multi-agent run</button>`;
    $('show-multi-result').addEventListener('click',()=>{renderResearch(result.multi_agent);goPage('research');});await loadMetrics();showToast('Comparison completed.');
  }catch(e){$('compare-output').textContent=`Comparison failed: ${e.message}`;showToast(e.message,true);}finally{setBusy(button,false);}
});
async function loadDocuments(){
  try{const data=await api('/documents');$('document-count').textContent=`${data.count} sources`;$('document-list').innerHTML=(data.documents||[]).map(doc=>`<div class="document-item"><div class="document-title">${esc(doc.title)}</div><div class="document-meta">${esc(doc.document_id)} · ${esc(doc.source||'source not specified')}</div><div class="evidence-text">${esc(doc.text||'')}</div></div>`).join('')||'<p class="muted">No documents in the knowledge base.</p>';}
  catch(e){$('document-list').textContent=e.message;}
}
$('document-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=event.submitter;const payload={title:$('doc-title').value.trim(),source:$('doc-source').value.trim()||'user-added',text:$('doc-text').value.trim()};setBusy(button,true,'Adding source…');$('doc-message').textContent='';
  try{const result=await api('/documents',{method:'POST',body:JSON.stringify(payload)});$('doc-message').textContent=`Added ${result.document.document_id}. The researcher can now retrieve it through MCP.`;$('document-form').reset();await loadDocuments();showToast('Document added to the searchable corpus.');}
  catch(e){$('doc-message').textContent=e.message;$('doc-message').style.color='#bd4545';showToast(e.message,true);}finally{setBusy(button,false);}
});
$('refresh-documents').addEventListener('click',async()=>{await loadDocuments();await loadTools();showToast('Documents and MCP tools refreshed.');});
$('check-mcp').addEventListener('click',loadTools);
async function loadTools(){
  $('mcp-status').textContent='Checking';$('mcp-tools').innerHTML='<p class="muted">Discovering MCP tools…</p>';
  try{const data=await api('/mcp/tools');$('mcp-status').textContent=`Connected · ${data.count}`;$('mcp-status').classList.remove('warning');$('mcp-tools').innerHTML=(data.tools||[]).map(tool=>`<div class="tool-item"><div class="tool-check">✓</div><div><div class="tool-name">${esc(tool.name)}</div><div class="tool-description">${esc(tool.description)}</div></div></div>`).join('');}
  catch(e){$('mcp-status').textContent='Unavailable';$('mcp-status').classList.add('warning');$('mcp-tools').innerHTML=`<p class="muted">${esc(e.message)}</p>`;}
}
checkHealth();
