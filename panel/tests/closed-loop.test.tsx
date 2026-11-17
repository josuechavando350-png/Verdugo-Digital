import { afterEach, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Api } from '../src/lib/api';
import { ClosedLoop } from '../src/components/ClosedLoop';
import SalesDesk from '../src/components/SalesDesk';
afterEach(()=>vi.restoreAllMocks());
it('shows missing click measurement and currency totals with no upload control',async()=>{
 const api=new Api('synthetic');const get=vi.spyOn(api,'get').mockResolvedValue({leads_with_reference:2,matched_leads:1,won_leads_with_reference:1,uploaded:1,uploaded_value_minor_by_currency:{MXN:12345},cost_per_paid_client_by_currency:{MXN:null},reconciliation:[]});
 const client=new QueryClient();render(<QueryClientProvider client={client}><ClosedLoop api={api} tenant="cliente-demo"/></QueryClientProvider>);
 await screen.findByText(/Prospectos con referencia: 2/);expect(screen.getByText(/no medidos/)).toBeTruthy();expect(screen.getByText(/Valor subido/).textContent).toContain('123.45');expect(screen.getByText(/Costo por cliente/).textContent).toContain('Sin datos');expect(screen.queryByRole('button')).toBeNull();
 fireEvent.change(screen.getByLabelText('Ciclo desde · UTC'),{target:{value:'2026-11-01'}});await waitFor(()=>expect(get).toHaveBeenLastCalledWith('/closed-loop?tenant=cliente-demo&start_date=2026-11-01'));client.clear();
});
it('submits optional reference/phone only on confirmed intake and clears sensitive input',async()=>{
 const api=new Api('synthetic');const post=vi.spyOn(api,'post').mockResolvedValue({state:'recorded'});
 render(<SalesDesk api={api} tenant="cliente-demo" dataset="real" role="operator" followups={{items:[],active_leads:0,overdue_followups:0,truncated:false}} onSaved={vi.fn().mockResolvedValue(undefined)}/>);
 await userEvent.click(screen.getByText('Registrar prospecto'));
 for(const [label,value] of [['Identificador del prospecto','lead-demo'],['Nombre del prospecto','cliente-demo'],['Correo del prospecto','demo@example.invalid'],['Referencia del registro','synthetic'],['Referencia de WhatsApp','abc234'],['Teléfono opcional · E.164','+15550000000']])await userEvent.type(screen.getByLabelText(label),value);
 expect((screen.getByLabelText(/Tengo consentimiento/) as HTMLInputElement).checked).toBe(false);
 await userEvent.click(screen.getByLabelText(/Confirmo registrar/));await userEvent.click(screen.getByText('Guardar prospecto'));
 await screen.findByRole('status');expect(post.mock.calls[0][1].request).toMatchObject({ref_code:'ABC234',phone:'+15550000000',ads_user_data_consent:false});expect((screen.getByLabelText('Teléfono opcional · E.164') as HTMLInputElement).value).toBe('');
});
