export type Session = {role:'operator'|'viewer';csrf:string;tenants:string[]};
export type Client = {tenant:string;label?:string;managed:boolean;active:boolean;reason?:string;days_left?:number;paid_until?:string;paused?:boolean};
export type Metric = {spend:number;clicks:number;impressions:number;platform_conversions:number;cost_per_platform_conversion:number|null};
export type AdsReport = {tenant:string;currency:string;dataset:string;start_date:string;end_date:string;totals:Metric;daily:(Metric&{day:string})[];campaigns:(Metric&{platform:string;campaign:string})[];paid_clients:number;cost_per_paid_client:number|null;note:string;pacing?:{monthly_budget:number;spent:number;projected_month_end:number|null;budget_used_percent:number;days_with_data:number;complete_days_elapsed:number};anomalies:{method:string;days:{day:string;score:number}[]};baseline:{state:string;method?:string;result?:{predictions:number[]}};comparison?:{totals:Metric;change_percent:{spend:number|null;clicks:number|null;platform_conversions:number|null}}};
export type AuditEvent = {id:number;kind:string;at:number};
export type Product = {product:{registered:number;connection_states:Record<string,number>;live_verified:number;services:{service:string;kind:string;state:string;enabled:boolean}[]};runtime:{implemented:number;matching_installations:number;services:Record<string,{version_matches:boolean;expected:string;installed:string|null}>};doctor:{state:string;counts:Record<string,number>}};
export class Api {
  token:string; csrf='';
  constructor(token:string){this.token=token;}
  async get<T>(path:string):Promise<T> {return this.request(path);}
  async change(tenant:string,action:string,body:Record<string,unknown>){return this.request('/clients/'+encodeURIComponent(tenant)+'/'+action,body);}
  private async request<T>(path:string,body?:Record<string,unknown>):Promise<T>{
    if(!path.startsWith('/')||path.startsWith('//'))throw new Error('Ruta inválida');
    const response=await fetch('/api'+path,{method:body?'POST':'GET',cache:'no-store',credentials:'omit',headers:{'X-Verdugo-Token':this.token,...(body?{'Content-Type':'application/json','X-Verdugo-CSRF':this.csrf}:{})},...(body?{body:JSON.stringify(body)}:{})});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'No se pudo completar la consulta');
    return data;
  }
}
export function query(params:Record<string,string>){return new URLSearchParams(params).toString();}
export function money(value:number|null|undefined,currency='MXN'){return value==null?'Sin datos':new Intl.NumberFormat('es-MX',{style:'currency',currency,maximumFractionDigits:2}).format(value);}
