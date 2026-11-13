const $=id=>document.getElementById(id);
let token='',leads=[];
const pending=new Map();
const label={new:'Nuevo',qualified:'Calificado',won:'Venta declarada',lost:'Perdido'};
function message(text,error=false){$('message').textContent=text;$('message').dataset.error=String(error);}
async function api(path,options={}){
  if(!token)throw Error('Introduzca el token local.');
  const response=await fetch(path,{...options,headers:{Authorization:'Bearer '+token,...options.headers},cache:'no-store'});
  const value=await response.json();
  if(!response.ok)throw Error(value.error||('HTTP '+response.status));
  return value;
}
function consentSelection(){const lead=leads.find(l=>l.id===$('lead-choice').value);for(const key of ['analytics','marketing'])$('consent-form').elements[key].checked=!!lead?.[key];}
async function refresh(){
  const [result,report,capabilities]=await Promise.all([api('/v1/leads?limit=100'),api('/v1/report'),api('/v1/capabilities')]);
  leads=result.leads;const chosen=$('lead-choice').value;$('lead-choice').replaceChildren(new Option('Seleccione un prospecto',''));$('leads').replaceChildren();
  for(const lead of leads){$('lead-choice').add(new Option(lead.name+' · '+label[lead.stage],lead.id));const row=document.createElement('tr');for(const value of [lead.name,lead.source,label[lead.stage],lead.analytics?'Sí':'No',lead.marketing?'Sí':'No']){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}$('leads').append(row);}
  if(leads.some(l=>l.id===chosen))$('lead-choice').value=chosen;consentSelection();
  $('metrics').replaceChildren();
  const cards=[...report.stages.map(s=>[label[s.stage],String(s.count)]),...report.declared_sales.map(s=>['Venta declarada '+s.currency,(s.amount_minor/100).toFixed(2)+' · '+s.orders+' pedidos'])];
  if(!cards.length)cards.push(['Prospectos','0']);
  for(const [name,value] of cards){const card=document.createElement('div');card.className='card';const title=document.createElement('small'),n=document.createElement('strong');title.textContent=name;n.textContent=value;card.append(title,n);$('metrics').append(card);}
  $('workspace').textContent='Espacio: '+capabilities.workspace+' · Eventos: '+report.events+' · Destinos habilitados: '+(capabilities.enabled_destinations.join(', ')||'ninguno');
}
async function save(type,leadId,data){
  // Keep the event ID after uncertain HTTP failures so a retry does not duplicate a local write.
  const key=JSON.stringify([type,leadId,data]);
  if(!pending.has(key))pending.set(key,{id:crypto.randomUUID(),type,lead_id:leadId||crypto.randomUUID(),data});
  const receipt=await api('/v1/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(pending.get(key))});
  pending.delete(key);
  try{await refresh();message(receipt.replayed?'El evento ya estaba guardado; no se duplicó.':'Evento guardado en la base local.');}
  catch{message('Evento guardado. No se pudo actualizar el panel; use Entrar / actualizar, no repita la captura.',true);}
}
function attach(formId,action){$(formId).addEventListener('submit',async event=>{event.preventDefault();const buttons=[...event.currentTarget.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);try{await action(event.currentTarget);}catch(error){message(error.message,true);}finally{buttons.forEach(b=>b.disabled=false);}});}
function selected(){const id=$('lead-choice').value;if(!id)throw Error('Seleccione un prospecto.');return id;}
attach('access',async()=>{token=$('token').value;await refresh();message('Conectado al núcleo local. Proveedores originales no certificados.');});
attach('lead-form',async form=>{await save('lead.created',null,{name:form.elements.name.value,email:form.elements.email.value,source:form.elements.source.value,analytics:form.elements.analytics.checked,marketing:form.elements.marketing.checked});form.reset();});
attach('stage-form',async form=>save('lead.stage_changed',selected(),{stage:form.elements.stage.value}));
attach('sale-form',async form=>save('sale.recorded',selected(),{order_id:form.elements.order_id.value,amount_minor:Number(form.elements.amount_minor.value),currency:form.elements.currency.value}));
attach('consent-form',async form=>save('consent.updated',selected(),{analytics:form.elements.analytics.checked,marketing:form.elements.marketing.checked}));
$('lead-choice').addEventListener('change',consentSelection);
$('check-systems').addEventListener('click',async event=>{event.currentTarget.disabled=true;try{const result=await api('/v1/systems');$('systems').replaceChildren();for(const system of result.systems){const card=document.createElement('div');card.className='card';card.textContent=system.id+': '+system.state;$('systems').append(card);}message('Sondas de conectividad terminadas; no equivalen a integración E2E.');}catch(error){message(error.message,true);}finally{$('check-systems').disabled=false;}});
