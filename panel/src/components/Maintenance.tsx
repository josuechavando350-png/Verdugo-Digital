import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Api } from '../lib/api';

type Installation = {version:string;state:string;checks:{id:string;ok:boolean;label:string}[];last_backup_at:number|null};
export function Maintenance({api,role}:{api:Api;role:'operator'|'viewer'}){
 const result=useQuery({queryKey:['installation'],queryFn:()=>api.get<Installation>('/installation'),staleTime:30000});
 const [confirmed,setConfirmed]=useState(false);const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');const [error,setError]=useState('');
 async function backup(e:React.FormEvent){
  e.preventDefault();if(!confirmed||busy)return;setBusy(true);setError('');setMessage('');
  try{const saved=await api.post<{saved_directory:string;restore_allowed:boolean}>('/maintenance/backup',{confirm:true});
   setMessage('Respaldo guardado y verificado en '+saved.saved_directory+(saved.restore_allowed?'':'. Requiere conciliación antes de restaurar.'));setConfirmed(false);await result.refetch();
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 return <section className="surface"><span className="eyebrow">INSTALACIÓN Y RECUPERACIÓN</span><h2>Estado de tu instalación</h2>
  {result.isPending?<p>Comprobando…</p>:result.error?<p role="alert">{result.error.message}</p>:<><p>Versión {result.data.version} · {result.data.state==='local_checks_passed'?'Comprobaciones locales correctas':'Hay pendientes por revisar'}</p><ul className="runtime-list">{result.data.checks.map(c=><li key={c.id}><span>{c.label}</span><strong>{c.ok?'Correcto':'Pendiente'}</strong></li>)}</ul></>}
  <p className="footnote">Estas comprobaciones cubren esta instalación. La validación con cuentas reales y los resultados comerciales se verifican por separado.</p>
  {role==='operator'&&<form onSubmit={backup}><h3>Respaldo completo local</h3><p>Incluye configuración y datos de todos los clientes. Contiene información privada sin cifrar. Los perfiles y las claves de variables de entorno se conservan por separado.</p><label className="confirmation"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Confirmo guardar el respaldo privado de todos los clientes.</label><button className="primary" disabled={!confirmed||busy}>{busy?'Guardando…':'Crear respaldo local'}</button></form>}
  {message&&<p role="status" style={{overflowWrap:'anywhere'}}>{message}</p>}{error&&<p role="alert">{error}</p>}
  <p><a href="/es/operacion/">Cómo recuperar o actualizar el producto ↗</a></p>
 </section>;
}
