import { useState } from 'react';
import type { Api } from '../lib/api';

export default function NewClient({api,onCreated}:{api:Api;onCreated:(tenant:string)=>Promise<void>}) {
 const [name,setName]=useState('');const [confirmed,setConfirmed]=useState(false);
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function submit(e:React.FormEvent){
  e.preventDefault();setError('');
  if(!/^[A-Za-z0-9_-]{1,100}$/.test(name)){setError('Usa letras, números, guiones o guiones bajos.');return;}
  if(!confirmed){setError('Confirma la creación del cliente.');return;}
  setBusy(true);
  try{await api.post('/tenants',{tenant:name,confirm:true});setName('');setConfirmed(false);await onCreated(name);}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 return <details className="surface"><summary>Crear cliente</summary><form className="operation-form" onSubmit={submit}>
  <label>Identificador del nuevo cliente<input value={name} onChange={e=>{setName(e.target.value);setConfirmed(false);}} autoComplete="off" required maxLength={100}/></label>
  <p>Se crea apagado. Después registra su etiqueta y el periodo pagado en su tarjeta.</p>
  <label className="confirm"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Confirmo crear este cliente con todos los servicios apagados.</label>
  {error&&<p className="error" role="alert">{error}</p>}<button className="primary" disabled={busy}>{busy?'Creando…':'Crear cliente apagado'}</button>
 </form></details>;
}
