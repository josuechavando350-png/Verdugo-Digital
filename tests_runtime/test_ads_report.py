"""Original analytics packages through the same report, without a model service."""
import os
from pathlib import Path
import tempfile
import unittest
from verdugo import ads, local_runtime
from verdugo.engine import Engine

class AdsOriginalRuntime(unittest.TestCase):
    def test_original_anomaly_and_forecast_on_imported_aggregates(self):
        services={'pyod','statsforecast'}
        selected=os.getenv('VERDUGO_RUNTIME_SERVICES')
        if selected and not services <= set(selected.split(',')): self.skipTest('Different runtime group')
        missing=[s for s in services if not local_runtime.installed(s)['version_matches']]
        if missing:
            if os.getenv('VERDUGO_RUNTIME_REQUIRED')=='1': self.fail('Missing analytics: '+','.join(missing))
            self.skipTest('Optional analytics absent')
        cfg={'tenants':{'cliente-demo':{'services':{s:{'enabled':True,'license_reviewed':True,'runtime_reviewed':True,'version':local_runtime.SPECS[s][2]} for s in services}}}}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'synthetic.csv'
            path.write_text('Day,Campaign,Cost,Clicks,Impressions,Conversions\n'+''.join(f'2026-11-{i:02d},cliente-demo,{1000 if i==12 else 1},1,1,1\n' for i in range(1,13)))
            e=Engine(':memory:',cfg,'cliente-demo')
            try:
                ads.import_file(e,'@'+str(path),'google',True,dataset='demo')
                before=len(e.events()); e.role='viewer'
                r=ads.report(e,{'start_date':'2026-11-01','end_date':'2026-11-12','dataset':'demo'})
                self.assertEqual(r['anomalies']['method'],'pyod KNN')
                self.assertIn('2026-11-12',[d['day'] for d in r['anomalies']['days']])
                self.assertEqual(r['baseline']['result']['predictions'],[1000.0]*7)
                self.assertEqual(before,len(e.events())); self.assertEqual(r['paid_clients'],0)
            finally:e.close()
