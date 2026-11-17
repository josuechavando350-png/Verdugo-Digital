import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Api, query, money } from '../lib/api';
type Report={leads_with_reference:number;matched_leads:number;won_leads_with_reference:number;uploaded:number;uploaded_value_minor_by_currency:Record<string,number>;cost_per_paid_client_by_currency:Record<string,number|null>;reconciliation:{event_id:string;state:string}[]};
export function ClosedLoop({api,tenant}:{api:Api;tenant:string}){
 const [start,setStart]=useState('');const [end,setEnd]=useState('');
 const result=useQuery({queryKey:['closed-loop',tenant,start,end],queryFn:()=>api.get<Report>('/closed-loop?'+query({tenant,...(start?{start_date:start}:{}),...(end?{end_date:end}:{})})),retry:false});
 return <section className="surface"><h2>Ciclo cerrado · clientes que pagaron</h2><p>Datos reales declarados. Clics a WhatsApp con referencia: no medidos; el fragmento no envía datos.</p>
 <div className="filters"><label>Ciclo desde · UTC<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>Ciclo hasta · UTC<input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label></div>
 {result.error?<p role="alert">{result.error.message}</p>:result.isPending?<p>Consultando ciclo…</p>:<><p>Prospectos con referencia: {result.data.leads_with_reference} · Empatados: {result.data.matched_leads} · Ganados con referencia: {result.data.won_leads_with_reference} · Subidos: {result.data.uploaded}</p>
 {Object.entries(result.data.uploaded_value_minor_by_currency).map(([c,v])=><p key={c}>Valor subido: {money(v/100,c)}</p>)}
 {Object.entries(result.data.cost_per_paid_client_by_currency).map(([c,v])=><p key={c}>Costo por cliente que pagó: {money(v,c)}</p>)}
 <p>Eventos por conciliar: {result.data.reconciliation.length}</p>{result.data.reconciliation.map(r=><p key={r.event_id}>{r.event_id}: {r.state}</p>)}</>}
 <p>La carga y la exportación se realizan por CLI con el operador. Una respuesta aceptada por Google no demuestra atribución ni mejora de ventas.</p></section>;
}
