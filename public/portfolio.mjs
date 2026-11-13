const $=id=>document.getElementById(id);let token='';const pending=new Map();
const stateLabel={running:'En ejecución',completed:'Registrado',failed:'Falló',interrupted:'Interrumpido; revisar'};
function message(text,error=false){$('message').textContent=text;$('message').dataset.error=String(error);}
async function api(path,body){if(!token)throw Error('Introduce el token local.');const r=await fetch(path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),cache:'no-store'});const data=await r.json();if(!r.ok)throw Error(data.error||('HTTP '+r.status));return data;}
async function refresh(){
 const d=await api('/v1/portfolio');$('summary').textContent='Seleccionados: '+d.selected_count+' · Identidades nuevas: '+d.new_identities+' · Instalación conjunta de 50: NO verificada';
 $('modules').replaceChildren();for(const m of d.modules){const card=document.createElement('article');card.className='card';const name=document.createElement('b'),role=document.createElement('p'),state=document.createElement('small');name.textContent=m.id;role.textContent=m.role;state.textContent=m.implemented_operations.length?'Operación local implementada; proveedor en vivo no verificado':'Adaptador pendiente';card.append(name,role,state);$('modules').append(card);}
 $('runs').replaceChildren();for(const run of d.runs){const tr=document.createElement('tr');for(const value of [run.id.slice(0,12),stateLabel[run.state]||run.state,run.error||run.step,run.receipts.map(x=>x.distribution+' '+x.version).join(' → ')]){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('runs').append(tr);}
}
$('login').addEventListener('submit',async e=>{e.preventDefault();token=$('token').value;try{await refresh();message('Conectado al mismo espacio y base de datos de Verdugo.');}catch(error){message(error.message,true);}});
$('opportunity').addEventListener('submit',async e=>{
 e.preventDefault();const f=e.currentTarget,button=f.querySelector('button');button.disabled=true;
 try{const data={name:f.elements.name.value,email:f.elements.email.value,source:f.elements.source.value,html:f.elements.html.value,analytics:f.elements.analytics.checked,marketing:f.elements.marketing.checked};const key=JSON.stringify(data);
 if(!pending.has(key))pending.set(key,{id:crypto.randomUUID(),lead_id:crypto.randomUUID(),...data});
 const r=await api('/v1/portfolio/opportunities',pending.get(key));
 if(r.state==='completed'){pending.delete(key);f.reset();message('Prospecto guardado en el núcleo de Verdugo. No se enviaron campañas.');}
 else message('Estado: '+(stateLabel[r.state]||r.state)+'. No se repetirá la captura automáticamente.',true);
 try{await refresh();}catch{message('La operación respondió, pero no se pudo actualizar el panel. No repitas la captura; consulta el estado.',true);}
 }catch(error){message(error.message,true);}finally{button.disabled=false;}
});
