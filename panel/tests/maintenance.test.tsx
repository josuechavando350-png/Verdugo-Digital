import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Maintenance } from '../src/components/Maintenance';
import { Api } from '../src/lib/api';
const installation={version:'0.26.0',state:'attention_required',checks:[{id:'recent_backup',ok:false,label:'Respaldo íntegro de las últimas 24 horas'}],last_backup_at:null};
function mount(api:Api,role:'operator'|'viewer'){
 return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Maintenance api={api} role={role}/></QueryClientProvider>);
}
describe('installation and local recovery',()=>{
 it('shows pending checks and requires explicit backup confirmation',async()=>{
  const api=new Api('demo');vi.spyOn(api,'get').mockResolvedValue(installation);const post=vi.spyOn(api,'post').mockResolvedValue({saved_directory:'/private/synthetic-backup',restore_allowed:true});
  mount(api,'operator');await screen.findByText('Hay pendientes por revisar',{exact:false});
  const button=screen.getByRole('button',{name:'Crear respaldo local'});expect(button.hasAttribute('disabled')).toBe(true);
  await userEvent.click(screen.getByRole('checkbox'));await userEvent.click(button);
  await screen.findByRole('status');expect(post).toHaveBeenCalledWith('/maintenance/backup',{confirm:true});
  await waitFor(()=>expect(button.hasAttribute('disabled')).toBe(true));
 });
 it('keeps backup unavailable to a viewer and shows failures honestly',async()=>{
  const api=new Api('demo');vi.spyOn(api,'get').mockRejectedValue(new Error('Sin conexión local'));
  mount(api,'viewer');await screen.findByText('Sin conexión local');expect(screen.queryByRole('button',{name:'Crear respaldo local'})).toBeNull();
 });
});
