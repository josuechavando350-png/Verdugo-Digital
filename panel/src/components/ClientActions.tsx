import { useState, useEffect, useRef } from 'react';
import type { Client } from '../lib/api';
import { registration, payment, pause } from '../lib/forms';
export function ClientActions({client,role,save}:{client:Client;role:string;save:(action:string,body:Record<string,unknown>)=>Promise<unknown>}){
 const [action,setAction]=useState('');const [label,setLabel]=useState(client.tenant);const [until,setUntil]=useState('');const [reason,setReason]=useState('');const [confirm,setConfirm]=useState(false);const [pending,setPending]=useState(false);const [error,setError]=useState('');
 const dialog=useRef<HTMLElement>(null);
 useEffect(()=>{
  if(!action)return;
  const previous=document.activeElement as HTMLElement;
  const focusable=()=>Array.from(dialog.current?.querySelectorAll<HTMLElement>('input,button')||[]).filter(e=>!e.hasAttribute('disabled'));
  focusable()[0]?.focus();
  const key=(e:KeyboardEvent)=>{if(e.key==='Escape'&&!pending)setAction('');if(e.key==='Tab'){const items=focusable();const first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}};
  document.addEventListener('keydown',key);return()=>{document.removeEventListener('keydown',key);previous?.focus();};
 },[action,pending]);
 if(role!=='operator')return null;
 const titles:Record<string,string>={register:'Registrar cliente',pay:'Registrar pago',pause:'Pausar',resume:'Reanudar'};
 async function submit(){
  setError('');
  const result=action==='register'?registration.safeParse({label,grace_days:0}):action==='pay'?payment.safeParse({until}):action==='pause'?pause.safeParse({reason}):{success:true as const,data:{}};
  if(!result.success){setError(result.error.issues[0].message);return;}
  if(!confirm){setError('Marca la confirmación antes de continuar.');return;}
  setPending(true);
  try{await save(action,{...result.data,confirm:true});setAction('');setConfirm(false);}catch(e){setError((e as Error).message);}finally{setPending(false);}
 }
 return <><div className="client-actions">{(client.managed?['pay',client.paused?'resume':'pause']:['register']).map(a=><button key={a} className="small" onClick={()=>{setAction(a);setConfirm(false);setError('');}}>{titles[a]}</button>)}</div>{action&&<div className="modal-backdrop"><section ref={dialog} role="dialog" aria-modal="true" aria-label={titles[action]} className="dialog"><span className="eyebrow">{client.tenant}</span><h2>{titles[action]}</h2><p>El cambio quedará en la bitácora del cliente.</p>{action==='register'&&<label>Etiqueta del cliente<input value={label} onChange={e=>setLabel(e.target.value)}/></label>}{action==='pay'&&<><label>Pagado hasta<input type="date" value={until} onChange={e=>setUntil(e.target.value)}/></label><p className="muted">Declaración del operador. No se verifica el banco.</p></>}{action==='pause'&&<label>Motivo<input value={reason} onChange={e=>setReason(e.target.value)}/></label>}<label className="confirm"><input type="checkbox" checked={confirm} onChange={e=>setConfirm(e.target.checked)}/>Confirmo aplicar este cambio a {client.tenant}.</label>{error&&<p role="alert" className="error">{error}</p>}<div className="actions"><button disabled={pending} onClick={()=>setAction('')}>Cancelar</button><button className="primary" disabled={pending} onClick={submit}>{pending?'Guardando…':'Confirmar cambio'}</button></div></section></div>}</>;
}
