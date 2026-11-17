import { useState } from 'react';
import type { Api } from '../lib/api';

export type Followup={lead_id:string;channel:string|null;last_stage:string;followup_due_utc_date:string|null;overdue:boolean};
export type Followups={items:Followup[];active_leads:number;overdue_followups:number;truncated:boolean};
const stages:Record<string,string>={identified:'Identificado',contacted:'Contactado',meeting_booked:'Cita agendada',meeting_held:'Reunión realizada',proposal_sent:'Propuesta enviada',followup_due:'Programar seguimiento',won:'Venta con pago declarado',lost:'Perdido'};
const channels:Record<string,string>={referral:'Recomendación',partner:'Socio',outbound:'Prospección',organic:'Orgánico',paid:'Publicidad',other:'Otro'};
export function minorUnits(value:string,allowZero=false){
 if(!/^\d+(?:[.,]\d{1,2})?$/.test(value.trim()))throw new Error('Usa un importe positivo con hasta dos decimales.');
 const [whole,fraction='']=value.trim().replace(',','.').split('.');const amount=Number(whole)*100+Number(fraction.padEnd(2,'0'));
 if(!Number.isSafeInteger(amount)||(allowZero?amount<0:amount<=0)||amount>1e12)throw new Error('Importe fuera de rango.');
 return amount;
}
export default function SalesDesk({api,tenant,dataset,role,followups,onSaved}:{api:Api;tenant:string;dataset:string;role:string;followups:Followups;onSaved:()=>Promise<void>}){
 const [leadId,setLeadId]=useState('');const [name,setName]=useState('');const [email,setEmail]=useState('');const [channel,setChannel]=useState('organic');const [reference,setReference]=useState('');
 const [refCode,setRefCode]=useState('');const [phone,setPhone]=useState('');const [adsConsent,setAdsConsent]=useState(false);const [paidAt,setPaidAt]=useState('');
 const [selected,setSelected]=useState('');const [stage,setStage]=useState('contacted');const [due,setDue]=useState('');const [evidence,setEvidence]=useState('');const [amount,setAmount]=useState('');const [currency,setCurrency]=useState('MXN');const [cost,setCost]=useState('');
 const [eventId,setEventId]=useState(()=>crypto.randomUUID());const [confirmIntake,setConfirmIntake]=useState(false);const [confirmEvent,setConfirmEvent]=useState(false);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [message,setMessage]=useState('');
 const lead=followups.items.find(x=>x.lead_id===selected)||followups.items[0];
 async function intake(e:React.FormEvent){
  e.preventDefault();setError('');setMessage('');if(!confirmIntake){setError('Confirma el registro del prospecto.');return;}setBusy(true);
  try{await api.post('/sales/intake',{tenant,confirm:true,request:{lead_id:leadId,name,email,dataset,channel,evidence_ref:reference,...(refCode?{ref_code:refCode}:{}),...(phone?{phone,ads_user_data_consent:adsConsent}:{})}});await onSaved();setSelected(leadId);setLeadId('');setName('');setEmail('');setReference('');setRefCode('');setPhone('');setAdsConsent(false);setConfirmIntake(false);setMessage('Prospecto identificado. No se enviaron mensajes.');}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 async function record(e:React.FormEvent){
  e.preventDefault();setError('');setMessage('');if(!lead||!confirmEvent){setError('Selecciona un prospecto y confirma el cambio.');return;}
  setBusy(true);
  try{
   const request={event_id:'event-'+eventId,lead_id:lead.lead_id,channel:lead.channel,evidence_ref:evidence};
   const body=stage==='won'?{...request,payment_id:'payment-'+eventId,dataset,currency,amount_minor:minorUnits(amount),cost_minor:minorUnits(cost,true),...(paidAt?{paid_at:new Date(paidAt).toISOString()}:{})}:{...request,kind:stage,...(stage==='followup_due'?{followup_due:due}:{})};
   await api.post('/sales/'+(stage==='won'?'win':'event'),{tenant,confirm:true,request:body});await onSaved();setEventId(crypto.randomUUID());setConfirmEvent(false);setEvidence('');setAmount('');setCost('');setPaidAt('');setMessage(stage==='won'?'Venta y pago declarados juntos. No hay conciliación bancaria.':'Etapa registrada. No se enviaron mensajes ni invitaciones.');
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 return <><section className="surface"><h2>Próximos seguimientos</h2><p>{followups.active_leads} prospectos activos · {followups.overdue_followups} seguimientos vencidos</p>
  {!followups.items.length?<p>No hay prospectos activos en este conjunto de datos.</p>:<ul className="followup-list">{followups.items.map(x=><li key={x.lead_id}><strong>{x.lead_id}</strong><span>{stages[x.last_stage]||x.last_stage}</span><span>{x.followup_due_utc_date?`${x.overdue?'Vencido · ':''}${x.followup_due_utc_date} UTC`:'Sin fecha de seguimiento'}</span></li>)}</ul>}
  {followups.truncated&&<p>Se muestran los primeros 200. Consulta el resto desde la mesa comercial.</p>}</section>
  {role==='operator'&&<><details className="surface"><summary>Registrar prospecto</summary><form className="operation-form" onSubmit={intake}><fieldset disabled={busy}>
   <label>Identificador del prospecto<input value={leadId} onChange={e=>setLeadId(e.target.value)} pattern="[A-Za-z0-9_-]{1,100}" required autoComplete="off"/></label>
   <label>Nombre del prospecto<input value={name} onChange={e=>setName(e.target.value)} required maxLength={200} autoComplete="off"/></label>
   <label>Correo del prospecto<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required maxLength={254} autoComplete="off"/></label>
   <label>Referencia de WhatsApp<input value={refCode} onChange={e=>setRefCode(e.target.value.toUpperCase())} pattern="[A-Z2-7]{6}" maxLength={6} placeholder="ABC234" autoComplete="off"/></label>
   <label>Teléfono opcional · E.164<input type="tel" value={phone} onChange={e=>setPhone(e.target.value)} placeholder="+ y código de país" autoComplete="off" maxLength={40}/></label>
   <label><input type="checkbox" checked={adsConsent} onChange={e=>setAdsConsent(e.target.checked)}/>Tengo consentimiento documentado para usar el teléfono en medición de Google Ads.</label><p>Solo se conserva el hash del teléfono. El consentimiento no se presume por recibir un WhatsApp.</p>
   <label>Canal de origen<select value={channel} onChange={e=>setChannel(e.target.value)}>{Object.entries(channels).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
   <label>Referencia del registro<input value={reference} onChange={e=>setReference(e.target.value)} required maxLength={120} placeholder="registro-001"/></label>
   <label className="confirm"><input type="checkbox" checked={confirmIntake} onChange={e=>setConfirmIntake(e.target.checked)}/>Confirmo registrar este prospecto en {tenant} · {dataset==='demo'?'demostración':'datos reales'}.</label>
   <button className="primary" disabled={busy}>Guardar prospecto</button></fieldset></form></details>
  {lead&&<details className="surface"><summary>Registrar avance o venta</summary><form className="operation-form" onSubmit={record}><fieldset disabled={busy}>
   <label>Prospecto del avance<select value={lead.lead_id} onChange={e=>{setSelected(e.target.value);setConfirmEvent(false);setEventId(crypto.randomUUID());}}>{followups.items.map(x=><option key={x.lead_id}>{x.lead_id}</option>)}</select></label>
   <label>Etapa del avance<select value={stage} onChange={e=>{setStage(e.target.value);setConfirmEvent(false);setEventId(crypto.randomUUID());}}>{Object.entries(stages).filter(([k])=>k!=='identified').map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
   {stage==='followup_due'&&<label>Seguimiento · fecha UTC<input type="date" value={due} onChange={e=>setDue(e.target.value)} required/></label>}
   {stage==='won'&&<><label>Fecha y hora real del pago · hora de este dispositivo<input type="datetime-local" value={paidAt} onChange={e=>setPaidAt(e.target.value)}/></label><p>Requerida para el ciclo cerrado. No se sustituye por la hora de registro.</p><label>Importe recibido declarado<input inputMode="decimal" value={amount} onChange={e=>setAmount(e.target.value)} required/></label><label>Costos declarados<input inputMode="decimal" value={cost} onChange={e=>setCost(e.target.value)} required placeholder="0 si declaras que no hubo costos"/></label><label>Moneda del pago<select value={currency} onChange={e=>setCurrency(e.target.value)}><option>MXN</option><option>USD</option><option>EUR</option></select></label><p>El importe y la venta se guardan juntos. No se comprueba el banco. Los costos también son una declaración del operador.</p></>}
   <label>Referencia de evidencia<input value={evidence} onChange={e=>setEvidence(e.target.value)} required maxLength={120} placeholder="evidencia-001"/></label>
   <label className="confirm"><input type="checkbox" checked={confirmEvent} onChange={e=>setConfirmEvent(e.target.checked)}/>Confirmo este avance para {lead.lead_id}.</label>
   <button className="primary" disabled={busy}>Guardar avance</button></fieldset></form></details>}</>}
  {error&&<p className="notice error" role="alert">{error}</p>}{message&&<p className="notice" role="status">{message}</p>}
 </>;
}
