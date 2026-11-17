import { useRef, useState } from 'react';
import { Api, money } from '../lib/api';

type Preview={tenant:string;platform:string;dataset:string;currency:string;start_date:string;end_date:string;daily_campaign_aggregates:number;preview_fingerprint:string;totals:{spend:number;platform_conversions:number}};
const MAX_BYTES=5*1024*1024;
export function fileBase64(file:File):Promise<string>{
 return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(new Error('No se pudo leer el archivo.'));reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(file);});
}
export default function AdsImport({api,tenant,dataset,onImported}:{api:Api;tenant:string;dataset:string;onImported:(preview:Preview)=>Promise<void>}){
 const input=useRef<HTMLInputElement>(null);const [platform,setPlatform]=useState('google');const [currency,setCurrency]=useState('MXN');
 const [preview,setPreview]=useState<Preview|null>(null);const [payload,setPayload]=useState<Record<string,unknown>|null>(null);
 const [confirm,setConfirm]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [message,setMessage]=useState('');
 function invalidate(){setPreview(null);setPayload(null);setConfirm(false);setMessage('');setError('');}
 async function inspect(e:React.FormEvent){
  e.preventDefault();invalidate();const file=input.current?.files?.[0];
  if(!file||file.size===0||file.size>MAX_BYTES){setError('Selecciona un CSV de máximo 5 MiB.');return;}
  setBusy(true);
  try{const body={tenant,dataset,platform,currency,csv_base64:await fileBase64(file)};const data=await api.post<Preview>('/ads/import',{...body,confirm:false});setPayload(body);setPreview(data);}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 async function save(){
  if(!confirm||!preview||!payload){setError('Revisa y confirma la vista previa.');return;}
  setBusy(true);setError('');
  try{const result=await api.post<{changed:number;replayed:boolean}>('/ads/import',{...payload,confirm:true,preview_fingerprint:preview.preview_fingerprint});await onImported(preview);setMessage(result.replayed?'El archivo ya estaba importado; no se duplicaron métricas.':`Importación guardada: ${result.changed} agregados actualizados.`);setPreview(null);setPayload(null);setConfirm(false);if(input.current)input.current.value='';}
  catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 return <details className="surface"><summary>Importar reporte de anuncios</summary><form className="operation-form" onSubmit={inspect}>
  <fieldset disabled={busy}><div className="filters"><label>Plataforma del archivo<select value={platform} onChange={e=>{setPlatform(e.target.value);invalidate();}}><option value="google">Google Ads</option><option value="meta">Meta Ads</option></select></label>
  <label>Moneda del archivo<select value={currency} onChange={e=>{setCurrency(e.target.value);invalidate();}}><option>MXN</option><option>USD</option><option>EUR</option></select></label></div>
  <label>Archivo CSV diario<input ref={input} type="file" accept=".csv,text/csv" onChange={invalidate} required/></label>
  <p>Destino: <strong>{tenant}</strong> · {dataset==='demo'?'Demostración':'Datos reales declarados'}. Hasta 5 MiB, por día y campaña, sin columnas de personas.</p>
  <button disabled={busy}>{busy?'Procesando…':'Ver vista previa'}</button></fieldset></form>
  {preview&&<div className="operation-form"><p><strong>{preview.daily_campaign_aggregates} agregados</strong> · {preview.start_date} a {preview.end_date}</p><p>Gasto: {money(preview.totals.spend,preview.currency)} · Conversiones: {preview.totals.platform_conversions}. No equivalen a clientes.</p>
  <label className="confirm"><input type="checkbox" checked={confirm} onChange={e=>setConfirm(e.target.checked)} disabled={busy}/>Confirmo importar estos datos en {tenant}.</label>
  <button className="primary" type="button" disabled={busy||!confirm} onClick={save}>Confirmar importación</button></div>}
  {error&&<p className="error" role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
 </details>;
}
