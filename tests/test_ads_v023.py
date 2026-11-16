import contextlib
import io
import json
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verdugo import ads, subscriptions, mcp
from verdugo.engine import Engine
from verdugo.common import VerdugoError
from verdugo.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
GOOGLE = (ROOT/'examples/ads/google.synthetic.csv').read_text()
META = (ROOT/'examples/ads/meta.synthetic.csv').read_text()

class AdsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.config={'tenants':{'cliente-demo':{'services':{}},'otro-demo':{'services':{}}}}
        self.path=Path(self.tmp.name)/'report.csv'; self.path.write_text(GOOGLE)
        self.e=Engine(Path(self.tmp.name)/'state.sqlite',self.config,'cliente-demo'); self.addCleanup(self.e.close)
    def load(self,**kwargs): return ads.import_file(self.e,'@'+str(self.path),'google',**kwargs)
    def report(self,**kwargs): return ads.report(self.e,{'start_date':'2026-11-01','end_date':'2026-11-02',**kwargs})
    def test_preview_and_privacy(self):
        self.assertEqual(self.load()['state'],'planned'); self.assertEqual(self.e.db.execute('SELECT COUNT(*) FROM ads_daily').fetchone()[0],0)
        self.load(execute=True); dump='\n'.join(self.e.db.iterdump())
        for value in ('whatsapp',str(self.path),'Day,Campaign'): self.assertNotIn(value,dump)
        self.assertNotIn('cliente-demo',self.report()['campaigns'][0]['campaign'])
    def test_bilingual_platforms(self):
        for content in (GOOGLE,META,GOOGLE.replace('Day,Campaign,Cost,Clicks,Impressions,Conversions,Conversion action','Día,Campaña,Costo,Clics,Impresiones,Conversiones,Acción de conversión'),META.replace('Día;Nombre de la campaña;Importe gastado (MXN);Clics (todos);Impresiones;Resultados;Tipo de resultado','Day;Campaign name;Amount spent (MXN);Clicks (all);Impressions;Results;Result type')):
            self.assertEqual(ads.parse(content.encode(),'cliente-demo','meta','MXN')[0][2],100250000)
    def test_idempotence_and_correction(self):
        self.assertEqual(self.load(execute=True)['changed'],2)
        self.assertTrue(self.load(execute=True)['replayed'])
        self.path.write_text(GOOGLE.replace('100.25','101.25')); self.assertEqual(self.load(execute=True)['changed'],1)
        self.assertEqual(self.report()['totals']['spend'],151.25)
    def test_tenant_isolation_and_restart(self):
        self.load(execute=True)
        other=Engine(self.e.state_path,self.config,'otro-demo'); self.addCleanup(other.close)
        self.assertEqual(ads.report(other)['totals']['spend'],0)
        reopened=Engine(self.e.state_path,self.config,'cliente-demo'); self.addCleanup(reopened.close)
        self.assertEqual(ads.report(reopened,{'start_date':'2026-11-01','end_date':'2026-11-02'})['totals']['spend'],150.25)
    def test_off_switch_blocks_preview_import_report_and_mcp(self):
        subscriptions.register(self.e,'Cliente demo',execute=True)
        for fn in (self.load,lambda:self.load(execute=True),self.report,lambda:mcp.invoke(self.e,'verdugo_ads_report',{})):
            with self.assertRaisesRegex(VerdugoError,'apagado'): fn()
    def test_viewer_read_only(self):
        self.load(execute=True); self.e.role='viewer'
        self.assertEqual(self.report()['totals']['platform_conversions'],3)
        with self.assertRaises(VerdugoError): self.load()
        with self.assertRaises(VerdugoError): self.load(execute=True)
    def test_malformed_and_pii_columns(self):
        for data in (b'',b'\xff',b'x,y\n1,2',GOOGLE.replace('Cost','Email').encode(),GOOGLE.replace('100.25','NaN').encode(),GOOGLE.replace('2026-11-01','2026-99-99').encode(),GOOGLE.replace('100.25','"100').encode(),GOOGLE.replace(',5,',',5.2,').encode(),GOOGLE.replace('Day,','Day,Date,').encode()):
            with self.subTest(data=data[:30]):
                with self.assertRaises(VerdugoError): ads.parse(data,'cliente-demo','google','MXN')
    def test_size_and_nonregular(self):
        self.path.write_bytes(b'x'*(ads.MAX_BYTES+1))
        with self.assertRaisesRegex(VerdugoError,'5 MiB'): self.load()
        self.path.unlink(); self.path.symlink_to(Path(self.tmp.name))
        with self.assertRaises(VerdugoError): self.load()
    def test_ambiguous_breakdowns_rejected(self):
        data=GOOGLE+GOOGLE.splitlines()[1].replace('whatsapp','calls')+'\n'
        with self.assertRaisesRegex(VerdugoError,'repite'): ads.parse(data.encode(),'cliente-demo','google','MXN')
        with self.assertRaisesRegex(VerdugoError,'duplicadas'): ads.parse((GOOGLE+GOOGLE.splitlines()[1]+'\n').encode(),'cliente-demo','google','MXN')
    def test_no_clients_from_platform_conversions(self):
        self.load(execute=True); result=self.report()
        self.assertEqual(result['paid_clients'],0); self.assertIsNone(result['cost_per_paid_client'])
        self.assertEqual(result['totals']['platform_conversions'],3)
        self.assertEqual(result['totals']['cost_per_platform_conversion'],150.25/3)
    def test_won_paid_only_and_dataset(self):
        self.load(execute=True)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        timestamp=datetime(2026,11,1,12,tzinfo=ZoneInfo('America/Mexico_City')).timestamp()
        for i,(channel,dataset) in enumerate((('paid','real'),('organic','real'),('paid','demo'))):
            self.e.db.execute('INSERT INTO commercial_events VALUES(?,?,?,?,?,?,?,?,?,?)',('cliente-demo',f'event-{i}',f'lead-{i}',dataset,'won',channel,'proof',f'payment-{i}',None,timestamp))
        result=self.report(); self.assertEqual(result['paid_clients'],1); self.assertEqual(result['cost_per_paid_client'],150.25)
        self.assertIsNone(self.report(platform='google')['cost_per_paid_client'])
    def test_comparison_and_pacing(self):
        self.load(execute=True)
        with patch('verdugo.subscriptions.today',return_value=date(2026,11,3)):
            result=self.report(compare_start='2026-10-01',compare_end='2026-10-02',budget_month=3000)
        self.assertIsNone(result['comparison']['change_percent']['spend'])
        self.assertEqual(result['pacing']['projected_month_end'],150.25/2*30)
        with patch('verdugo.subscriptions.today',return_value=date(2026,11,5)):
            self.assertIsNone(self.report(budget_month=3000)['pacing']['projected_month_end'])
    def test_report_validation_and_currency(self):
        for params in ({'compare_start':'2026-01-01'},{'budget_month':-1},{'budget_month':float('nan')},{'platform':'other'},{'end_date':'2025-01-01'},{'currency':'usd'},{'token':'x'}):
            with self.subTest(params=params),self.assertRaises(VerdugoError): self.report(**params)
        with self.assertRaises(VerdugoError): ads.parse(META.encode(),'cliente-demo','meta','USD')
    def test_fallback_and_read_only_optional_workers(self):
        self.path.write_text(GOOGLE.splitlines()[0]+'\n'+''.join(f'2026-11-{i:02d},cliente-demo,{1000 if i==12 else 1},1,1,1,whatsapp\n' for i in range(1,13)))
        self.load(execute=True); count=len(self.e.events())
        result=self.report(end_date='2026-11-12')
        self.assertEqual(result['anomalies']['method'],'z-score simple'); self.assertEqual(len(result['anomalies']['days']),1)
        self.assertEqual(len(self.e.events()),count)
        def analysis(e,s,p):
            return {'state':'available','result':({'scores':[1]*12,'flags':[0]*11+[1]} if s=='pyod' else {'predictions':[1]*7})}
        with patch('verdugo.ads._analysis',side_effect=analysis):
            result=self.report(end_date='2026-11-12'); self.assertEqual(result['anomalies']['method'],'pyod KNN'); self.assertEqual(result['baseline']['result']['predictions'],[1]*7)
    def test_cli_and_mcp_read_tool(self):
        config=Path(self.tmp.name)/'config.json'; config.write_text(json.dumps(self.config))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code=main(['--config',str(config),'--state',self.e.state_path,'--tenant','cliente-demo','ads-import','@'+str(self.path),'--platform','google','--execute'])
        self.assertEqual(code,0); self.assertEqual(json.loads(out.getvalue())['state'],'imported')
        tools={t['name']:t for t in mcp.tool_definitions()}
        self.assertTrue(tools['verdugo_ads_report']['annotations']['readOnlyHint']); self.assertNotIn('verdugo_ads_import',tools)
        self.assertEqual(mcp.invoke(self.e,'verdugo_ads_report',{'params':{'start_date':'2026-11-01','end_date':'2026-11-02'}})['totals']['spend'],150.25)
