import { Feed } from 'feed';
import type { AuditEvent } from './api';
export function auditFeed(events:AuditEvent[]){
  const feed=new Feed({title:'Verdugo · Bitácora local',description:'Eventos del tenant; sin detalles personales',id:'urn:verdugo:audit',link:'http://127.0.0.1/',copyright:'Archivo local del operador',updated:new Date((events[0]?.at||0)*1000)});
  for(const e of events)feed.addItem({title:e.kind,id:'urn:verdugo:event:'+e.id,link:'http://127.0.0.1/#evento-'+e.id,date:new Date(e.at*1000),description:'Evento local #'+e.id});
  return feed.rss2();
}
export function download(text:string,filename:string,type='application/json'){
 const url=URL.createObjectURL(new Blob([text],{type})); const link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
