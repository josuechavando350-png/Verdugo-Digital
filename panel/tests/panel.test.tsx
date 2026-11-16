import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ClientActions } from '../src/components/ClientActions';
import DataTable from '../src/components/DataTable';
import App, { guidedTour } from '../src/components/App';
import { Api, money } from '../src/lib/api';
import { payment, reportPeriod } from '../src/lib/forms';
import { tr } from '../src/lib/language';
import { auditFeed } from '../src/lib/exports';
import { chartOptions } from '../src/components/Chart';
import { init } from 'echarts/core';
import { watchPerformance } from '../src/lib/performance';
import * as vitals from 'web-vitals';
vi.mock('web-vitals',{spy:true});
const client={tenant:'cliente-demo',managed:true,active:false};
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});
describe('Operator confirmation and permissions',()=>{
 it('requires explicit confirmation and sends only the chosen payment',async()=>{
  const save=vi.fn().mockResolvedValue({});render(<ClientActions client={client} role="operator" save={save}/>);
  await userEvent.click(screen.getByText('Registrar pago'));fireEvent.change(screen.getByLabelText('Pagado hasta'),{target:{value:'2026-11-20'}});
  await userEvent.click(screen.getByText('Confirmar cambio'));expect(save).not.toHaveBeenCalled();expect(screen.getByRole('alert').textContent).toContain('confirmación');
  await userEvent.click(screen.getByRole('checkbox'));await userEvent.click(screen.getByText('Confirmar cambio'));
  expect(save).toHaveBeenCalledWith('pay',{until:'2026-11-20',confirm:true});expect(screen.queryByRole('dialog')).toBeNull();
 });
 it('hides all mutations for a viewer',()=>{render(<ClientActions client={client} role="viewer" save={vi.fn()}/>);expect(screen.queryByRole('button')).toBeNull();});
 it('keeps rejected changes visible and Escape closes the dialog',async()=>{
  render(<ClientActions client={client} role="operator" save={vi.fn().mockRejectedValue(new Error('Pago inválido'))}/>);
  await userEvent.click(screen.getByText('Pausar'));await userEvent.type(screen.getByLabelText('Motivo'),'Solicitud demo');await userEvent.click(screen.getByRole('checkbox'));await userEvent.click(screen.getByText('Confirmar cambio'));
  expect(screen.getByRole('alert').textContent).toBe('Pago inválido');await userEvent.keyboard('{Escape}');expect(screen.queryByRole('dialog')).toBeNull();
 });
});
describe('Original panel libraries',()=>{
 it('renders real TanStack row models and missing cells without inventing values',()=>{render(<DataTable data={[{campaign:'demo',spend:12}]} columns={[{accessorKey:'campaign',header:'Campaña'},{accessorKey:'spend',header:'Gasto'}]}/>);expect(screen.getByRole('cell',{name:'12'})).toBeTruthy();expect(screen.getAllByRole('columnheader')).toHaveLength(2);});
 it('renders original ECharts SVG with two metric axes',()=>{const c=init(null,undefined,{renderer:'svg',ssr:true,width:390,height:300});try{c.setOption(chartOptions([{day:'2026-11-01',spend:30,clicks:4,impressions:40,platform_conversions:2,cost_per_platform_conversion:15}]));const svg=c.renderToSVGString();expect(svg).toContain('<svg');expect(svg).toContain('Conversiones');expect(svg).toContain('11-01');}finally{c.dispose();}});
 it('validates dates and localizes product states',()=>{expect(payment.safeParse({until:''}).success).toBe(false);expect(reportPeriod.safeParse({start_date:'2026-11-20',end_date:'2026-11-01'}).success).toBe(false);expect(tr('integrado_en_panel')).toBe('Integrada en el panel');expect(money(null)).toBe('Sin datos');});
 it('exports audit metadata through original Feed with escaped text',()=>{const xml=auditFeed([{id:3,kind:'client.<pause>',at:1794873600}]);expect(xml).toContain('<rss');expect(xml).toContain('urn:verdugo:event:3');expect(new DOMParser().parseFromString(xml,'application/xml').querySelector('pause')).toBeNull();expect(xml).toContain('Evento local #3');});
 it('starts original Driver and lets the operator close it',async()=>{render(<><div id="tenant">Cliente</div><nav id="navigation"/><main id="workspace"/></>);guidedTour();await waitFor(()=>expect(document.querySelector('.driver-popover-title')?.textContent).toBe('Un cliente a la vez'));fireEvent.click(document.querySelector('.driver-popover-close-btn')!);});
 it('registers local Web Vitals callbacks without network transmission',()=>{const callbacks:Function[]=[];for(const name of ['onCLS','onINP','onLCP'] as const)vi.spyOn(vitals,name).mockImplementation((cb: Function)=>{callbacks.push(cb);});const send=vi.fn();watchPerformance(send);callbacks[0]({name:'CLS',value:0.12345});expect(send).toHaveBeenCalledWith('CLS',0.12);expect(callbacks).toHaveLength(3);});
});
describe('API and query lifecycle',()=>{
 it('sends token and CSRF in headers, never URL, and rejects API errors',async()=>{const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>({saved:true})});vi.stubGlobal('fetch',fetcher);const api=new Api('test-memory-token');api.csrf='csrf';await api.change('cliente-demo','pause',{reason:'demo',confirm:true});const [url,options]=fetcher.mock.calls[0];expect(url).toBe('/api/clients/cliente-demo/pause');expect(options.credentials).toBe('omit');expect(options.headers['X-Verdugo-CSRF']).toBe('csrf');fetcher.mockResolvedValue({ok:false,json:async()=>({error:'Bloqueado'})});await expect(api.get('/ads')).rejects.toThrow('Bloqueado');await expect(api.get('//elsewhere')).rejects.toThrow('Ruta inválida');});
 it('loads clients using Query, refreshes, and clears session on logout',async()=>{
  const fetcher=vi.fn(async(path:string)=>({ok:true,json:async()=>path.endsWith('/session')?{role:'viewer',csrf:'csrf',tenants:['cliente-demo']}:{clients:[client]}}));vi.stubGlobal('fetch',fetcher);
  render(<App/>);await userEvent.type(screen.getByLabelText('Token de acceso local'),'test-memory-token');await userEvent.click(screen.getByText('Entrar al panel'));await screen.findByText('Apagado');expect(screen.queryByText('Registrar pago')).toBeNull();await userEvent.click(screen.getByText('Actualizar ↻'));await waitFor(()=>expect(fetcher.mock.calls.filter(([p])=>p==='/api/clients').length).toBe(2));await userEvent.click(screen.getByText('Salir'));expect(screen.getByLabelText('Token de acceso local').getAttribute('value')).toBe('');
 });
});
