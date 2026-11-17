import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Api } from '../src/lib/api';
import AdsImport from '../src/components/AdsImport';
import NewClient from '../src/components/NewClient';
import SalesDesk, { minorUnits } from '../src/components/SalesDesk';
afterEach(()=>vi.restoreAllMocks());
// jsdom's native required-file validity ignores user-event's FileList; browser E2E covers native submission.
const preview={tenant:'cliente-demo',platform:'google',dataset:'demo',currency:'MXN',start_date:'2026-11-01',end_date:'2026-11-01',daily_campaign_aggregates:1,preview_fingerprint:'a'.repeat(64),totals:{spend:30,platform_conversions:2}};
describe('Operator workday',()=>{
 it('previews CSV before confirmation and never sends the file name',async()=>{
  const api=new Api('synthetic');const post=vi.spyOn(api,'post').mockResolvedValueOnce(preview).mockResolvedValueOnce({changed:1,replayed:false});const saved=vi.fn().mockResolvedValue(undefined);
  render(<AdsImport api={api} tenant="cliente-demo" dataset="demo" onImported={saved}/>);
  await userEvent.click(screen.getByText('Importar reporte de anuncios'));
  await userEvent.upload(screen.getByLabelText('Archivo CSV diario'),new File(['synthetic csv'],'private-local-name.csv',{type:'text/csv'}));
  expect((screen.getByLabelText('Archivo CSV diario') as HTMLInputElement).files).toHaveLength(1);fireEvent.submit(screen.getByLabelText('Archivo CSV diario').closest('form')!);await screen.findByText('1 agregados');
  expect(post.mock.calls[0][1].confirm).toBe(false);expect(JSON.stringify(post.mock.calls)).not.toContain('private-local-name');
  expect(screen.getByRole('button',{name:'Confirmar importación'}).hasAttribute('disabled')).toBe(true);
  await userEvent.click(screen.getByRole('checkbox'));await userEvent.click(screen.getByText('Confirmar importación'));
  await waitFor(()=>expect(saved).toHaveBeenCalledWith(preview));expect(post.mock.calls[1][1].preview_fingerprint).toBe(preview.preview_fingerprint);
  expect(screen.queryByText('1 agregados')).toBeNull();
 });
 it('invalidates a CSV confirmation when its scope changes',async()=>{
  const api=new Api('synthetic');const post=vi.spyOn(api,'post').mockResolvedValue(preview);
  render(<AdsImport api={api} tenant="cliente-demo" dataset="demo" onImported={vi.fn()}/>);
  await userEvent.click(screen.getByText('Importar reporte de anuncios'));
  await userEvent.upload(screen.getByLabelText('Archivo CSV diario'),new File(['csv'],'demo.csv',{type:'text/csv'}));
  expect((screen.getByLabelText('Archivo CSV diario') as HTMLInputElement).files).toHaveLength(1);fireEvent.submit(screen.getByLabelText('Archivo CSV diario').closest('form')!);await screen.findByText('1 agregados');
  await userEvent.selectOptions(screen.getByLabelText('Plataforma del archivo'),'meta');
  expect(screen.queryByText('Confirmar importación')).toBeNull();expect(post).toHaveBeenCalledTimes(1);
 });
 it('requires explicit confirmation before creating a client',async()=>{
  const api=new Api('synthetic');const post=vi.spyOn(api,'post').mockResolvedValue({state:'applied'});const created=vi.fn().mockResolvedValue(undefined);
  render(<NewClient api={api} onCreated={created}/>);await userEvent.click(screen.getByText('Crear cliente'));
  await userEvent.type(screen.getByLabelText('Identificador del nuevo cliente'),'cliente-demo');await userEvent.click(screen.getByText('Crear cliente apagado'));
  expect(post).not.toHaveBeenCalled();await userEvent.click(screen.getByRole('checkbox'));await userEvent.click(screen.getByText('Crear cliente apagado'));
  expect(post).toHaveBeenCalledWith('/tenants',{tenant:'cliente-demo',confirm:true});expect(created).toHaveBeenCalledWith('cliente-demo');
 });
 it('hides sales mutations for a viewer but shows the followup queue',()=>{
  render(<SalesDesk api={new Api('synthetic')} tenant="cliente-demo" dataset="demo" role="viewer" followups={{items:[{lead_id:'lead-demo',channel:'paid',last_stage:'identified',followup_due_utc_date:null,overdue:false}],active_leads:1,overdue_followups:0,truncated:false}} onSaved={vi.fn()}/>);
  expect(screen.getByText('lead-demo')).toBeTruthy();expect(screen.queryByText('Registrar prospecto')).toBeNull();expect(screen.queryByText('Registrar avance o venta')).toBeNull();
 });
 it('converts declared amounts exactly and rejects fractions of a cent',()=>{
  expect(minorUnits('1200,25')).toBe(120025);expect(minorUnits('0',true)).toBe(0);
  for(const invalid of ['0','1.001','NaN','1,000.00','-10'])expect(()=>minorUnits(invalid)).toThrow();
 });
});
