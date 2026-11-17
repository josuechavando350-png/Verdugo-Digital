"""Tenant-scoped daily advertising aggregates. Never retain CSVs or campaign names."""
import calendar
import csv
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import io
import math
import os
from pathlib import Path
import re
import stat
import statistics
import unicodedata
from zoneinfo import ZoneInfo

from .common import VerdugoError, fields
from . import subscriptions, local_runtime

MAX_BYTES = 5 * 1024 * 1024
SCHEMA = '''
CREATE TABLE IF NOT EXISTS ads_daily (
 tenant TEXT NOT NULL, platform TEXT NOT NULL, dataset TEXT NOT NULL,
 currency TEXT NOT NULL, day TEXT NOT NULL, campaign TEXT NOT NULL,
 spend_micros INTEGER NOT NULL, clicks INTEGER NOT NULL,
 impressions INTEGER NOT NULL, conversions REAL NOT NULL,
 PRIMARY KEY(tenant,platform,dataset,currency,day,campaign));
'''
ALIASES = {
 'day': ('day', 'date', 'dia', 'fecha', 'reporting starts', 'inicio del informe'),
 'end': ('reporting ends', 'fin del informe'),
 'campaign': ('campaign', 'campaign name', 'campana', 'nombre de la campana'),
 'spend': ('cost', 'spend', 'amount spent', 'costo', 'coste', 'importe gastado'),
 'clicks': ('clicks', 'clicks (all)', 'clics', 'clics (todos)'),
 'impressions': ('impressions', 'impr.', 'impresiones'),
 'conversions': ('conversions', 'conversiones', 'results', 'resultados'),
 'action': ('conversion action', 'accion de conversion', 'result type', 'tipo de resultado', 'indicador de resultado'),
 'currency': ('currency', 'currency code', 'moneda', 'codigo de moneda'),
}


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise VerdugoError('Usa fechas YYYY-MM-DD')
    try: return date.fromisoformat(value)
    except ValueError: raise VerdugoError('Fecha no válida') from None


def number(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+(?:[.,]\d{1,6})?', value.strip()):
        raise VerdugoError('Número inválido; exporta sin separadores de miles ni símbolos de moneda')
    try: n = Decimal(value.strip().replace(',', '.'))
    except InvalidOperation: raise VerdugoError('Número inválido') from None
    if not n.is_finite() or not 0 <= n <= 10**9:
        raise VerdugoError('Métrica fuera de rango')
    return n


def _header(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', value.lower().strip()) if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', value)


def _scope(platform, dataset, currency):
    if platform not in ('google', 'meta') or dataset not in ('real', 'demo'):
        raise VerdugoError('Plataforma o conjunto de datos inválido')
    if not isinstance(currency, str) or not re.fullmatch('[A-Z]{3}', currency):
        raise VerdugoError('Declara una moneda de tres letras')


def _access(engine, write=False):
    if engine.role not in (('operator',) if write else ('operator', 'viewer')):
        raise VerdugoError('Operator role required' if write else 'Operator or viewer role required')
    subscriptions.check(engine)


def parse(raw, tenant, platform, currency):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise VerdugoError('CSV vacío o mayor de 5 MiB')
    try:
        content = raw.decode('utf-8-sig')
        if '\x00' in content: raise ValueError()
        dialect = csv.Sniffer().sniff(content[:8192], delimiters=',;\t')
        reader = csv.reader(io.StringIO(content), dialect=dialect, strict=True)
        header = next(reader)
        lookup = {alias: key for key, aliases in ALIASES.items() for alias in aliases}
        columns = []
        for cell in header:
            normalized = _header(cell)
            # Meta includes the currency in this recognized metric header.
            match = re.fullmatch(r'(importe gastado|amount spent) \(([a-z]{3})\)', normalized)
            if match:
                if match[2].upper() != currency: raise VerdugoError('La moneda del CSV no coincide')
                normalized = match[1]
            if normalized not in lookup:
                raise VerdugoError('Columna no admitida: exporta solo métricas diarias, sin datos personales')
            columns.append(lookup[normalized])
        if len(set(columns)) != len(columns) or not {'day','campaign','spend','clicks','impressions','conversions'} <= set(columns):
            raise VerdugoError('Faltan columnas requeridas o hay columnas duplicadas')
        groups, seen = {}, set()
        for index, values in enumerate(reader):
            if index >= 20000: raise VerdugoError('CSV supera 20000 filas')
            if len(values) != len(columns): raise VerdugoError('Fila CSV incompleta')
            row = dict(zip(columns, (v.strip() for v in values)))
            date_value = day(row['day']).isoformat()
            if 'end' in row and row['end'] != date_value:
                raise VerdugoError('Exporta por día; no se aceptan totales de varios días')
            if row.get('currency', currency) != currency:
                raise VerdugoError('No se pueden mezclar monedas')
            name = row['campaign']
            if not name or len(name) > 200 or any(ord(c) < 32 for c in name):
                raise VerdugoError('Campaña inválida')
            campaign = 'campaign-' + hashlib.sha256((tenant+'\0'+platform+'\0'+name).encode()).hexdigest()[:24]
            nums = {key: number(row[key]) for key in ('spend','clicks','impressions','conversions')}
            if any(nums[key] != nums[key].to_integral_value() for key in ('clicks','impressions')):
                raise VerdugoError('Clics e impresiones deben ser enteros')
            key = date_value, campaign
            action_key = (*key, row.get('action', ''))
            if action_key in seen:
                raise VerdugoError('Filas duplicadas o desgloses ambiguos; exporta una fila por día, campaña y acción')
            seen.add(action_key)
            values = [int(nums['spend']*1000000), int(nums['clicks']), int(nums['impressions']), nums['conversions']]
            if key in groups:
                # Segmented conversion exports can repeat exposure metrics. Refuse to guess.
                if any(groups[key][:3]) and any(values[:3]):
                    raise VerdugoError('Desglose por acción repite gasto o tráfico; exporta sin ese desglose')
                groups[key] = [a+b for a,b in zip(groups[key], values)]
            else: groups[key] = values
        if not groups: raise VerdugoError('CSV sin métricas')
        if len(groups) > 10000: raise VerdugoError('Demasiados agregados diarios')
        return [(d,c,*v[:3],float(v[3])) for (d,c),v in sorted(groups.items())]
    except (UnicodeError, csv.Error, StopIteration, ValueError):
        raise VerdugoError('CSV malformado; se requiere UTF-8 con encabezados') from None


def import_file(engine, source, platform, execute=False, dataset='real', currency='MXN'):
    _access(engine, write=True)
    _scope(platform, dataset, currency)
    if type(execute) is not bool: raise VerdugoError('execute debe ser booleano')
    if not isinstance(source, str) or not source.startswith('@'):
        raise VerdugoError('Se requiere @archivo.csv local')
    try:
        fd = os.open(Path(source[1:]).expanduser(), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise VerdugoError('CSV debe ser un archivo regular de máximo 5 MiB')
            raw = stream.read(MAX_BYTES + 1)
    except OSError: raise VerdugoError('No se puede leer el CSV local') from None
    return import_bytes(engine, raw, platform, execute, dataset, currency)


def import_bytes(engine, raw, platform, execute=False, dataset='real', currency='MXN', expected_fingerprint=None):
    """Same importer for a private local file and a bounded panel upload.

    The optional fingerprint binds an operator's confirmation to the exact
    bytes, tenant and scope previewed. Raw content is never persisted.
    """
    _access(engine, write=True)
    _scope(platform, dataset, currency)
    if type(execute) is not bool: raise VerdugoError('execute debe ser booleano')
    rows = parse(raw, engine.tenant, platform, currency)
    fingerprint = hashlib.sha256(('\0'.join((engine.tenant, platform, dataset, currency))+'\0').encode()+raw).hexdigest()
    if expected_fingerprint is not None:
        if not isinstance(expected_fingerprint, str) or not re.fullmatch('[a-f0-9]{64}', expected_fingerprint) or not hmac.compare_digest(expected_fingerprint, fingerprint):
            raise VerdugoError('El archivo o su destino cambió: revisa una nueva vista previa')
    summary = {'operation': 'ads.import', 'tenant': engine.tenant, 'platform': platform,
               'dataset': dataset, 'currency': currency, 'daily_campaign_aggregates': len(rows),
               'start_date': rows[0][0], 'end_date': rows[-1][0], 'raw_retained': False,
               'campaign_names_retained': False, 'external_calls_made': False,
               'preview_fingerprint': fingerprint,
               'totals': {'spend': sum(r[2] for r in rows)/1000000,
                          'clicks': sum(r[3] for r in rows), 'impressions': sum(r[4] for r in rows),
                          'platform_conversions': sum(r[5] for r in rows)}}
    if not execute: return summary | {'state': 'planned'}
    with engine.transaction():
        _access(engine, write=True)
        changed = 0
        for row in rows:
            cursor = engine.db.execute('''INSERT INTO ads_daily VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant,platform,dataset,currency,day,campaign) DO UPDATE SET
                 spend_micros=excluded.spend_micros,clicks=excluded.clicks,
                 impressions=excluded.impressions,conversions=excluded.conversions
                WHERE spend_micros!=excluded.spend_micros OR clicks!=excluded.clicks
                 OR impressions!=excluded.impressions OR conversions!=excluded.conversions''',
                (engine.tenant, platform, dataset, currency, *row))
            changed += cursor.rowcount
        if changed: engine.event('ads-import', 'ads.imported', summary | {'changed': changed})
    return summary | {'state': 'imported', 'changed': changed, 'replayed': changed == 0}


def _totals(rows):
    spend = sum(r['spend_micros'] for r in rows) / 1000000
    conv = sum(r['conversions'] for r in rows)
    return {'spend': spend, 'clicks': sum(r['clicks'] for r in rows),
            'impressions': sum(r['impressions'] for r in rows), 'platform_conversions': conv,
            'cost_per_platform_conversion': spend / conv if conv else None}


def _analysis(engine, service, params):
    """Read-only worker; preserves operator enable/license/runtime gates, no plans/events."""
    operation = local_runtime.SPECS[service][0]
    try:
        cfg = engine.preflight(service, operation)
        request = local_runtime.build(service, operation, params, cfg)
        return {'state': 'available', 'result': local_runtime.execute(request, cfg)['result']}
    except VerdugoError:
        return {'state': 'unavailable_or_not_reviewed'}


def report(engine, params=None):
    _access(engine)
    p = {} if params is None else params
    if isinstance(p, dict) and type(p.get('budget_month')) is float and not math.isfinite(p['budget_month']):
        raise VerdugoError('Presupuesto mensual debe ser finito')
    fields(p, (), ('start_date','end_date','compare_start','compare_end','budget_month','month','platform','dataset','currency'))
    now = subscriptions.today()
    end = day(p.get('end_date', now.isoformat()))
    start = day(p.get('start_date', (end-timedelta(days=29)).isoformat()))
    if not 0 <= (end-start).days < 366: raise VerdugoError('Periodo máximo: 366 días')
    dataset, currency, platform = p.get('dataset','real'), p.get('currency','MXN'), p.get('platform')
    _scope(platform or 'google', dataset, currency)
    query = 'SELECT * FROM ads_daily WHERE tenant=? AND dataset=? AND currency=? AND day BETWEEN ? AND ?'
    args = [engine.tenant, dataset, currency]
    def rows_between(a,b):
        suffix = ' AND platform=?' if platform else ''
        return list(engine.db.execute(query+suffix+' ORDER BY day,campaign', args+[a.isoformat(),b.isoformat()]+([platform] if platform else [])))
    rows = rows_between(start,end)
    totals = _totals(rows)
    campaigns = sorted({(r['platform'],r['campaign']) for r in rows})
    daily = [{'day': d, **_totals([r for r in rows if r['day']==d])} for d in sorted({r['day'] for r in rows})]
    tz = ZoneInfo(subscriptions.BILLING_TZ)
    bounds = [datetime.combine(d,time(),tzinfo=tz).timestamp() for d in (start,end+timedelta(days=1))]
    won = engine.db.execute("SELECT COUNT(DISTINCT lead_id) FROM commercial_events WHERE tenant=? AND dataset=? AND kind='won' AND channel='paid' AND created>=? AND created<?", (engine.tenant,dataset,*bounds)).fetchone()[0]
    out = {'state':'observed_local','tenant':engine.tenant,'dataset':dataset,'currency':currency,
        'start_date':start.isoformat(),'end_date':end.isoformat(),'totals':totals,
        'campaigns':[{'platform':plat,'campaign':c,**_totals([r for r in rows if r['campaign']==c and r['platform']==plat])} for plat,c in campaigns],
        'daily':daily, 'paid_clients':won,
        'cost_per_paid_client':totals['spend']/won if won and not platform else None,
        'paid_client_scope':'todos los anuncios; el libro no atribuye ventas a una plataforma o campaña',
        'bank_reconciled':False,'external_calls_made':False,
        'note':'Conversión de la plataforma no significa cliente que pagó. Ventas won del canal paid: pagos declarados por el operador; demo no es ingreso real.'}
    if ('compare_start' in p) != ('compare_end' in p): raise VerdugoError('Indica ambas fechas de comparación')
    if 'compare_start' in p:
        a,b=day(p['compare_start']),day(p['compare_end'])
        if not 0 <= (b-a).days < 366: raise VerdugoError('Comparación máxima: 366 días')
        previous=_totals(rows_between(a,b))
        out['comparison']={'start_date':a.isoformat(),'end_date':b.isoformat(),'totals':previous,
            'change_percent':{k:100*(totals[k]-previous[k])/previous[k] if previous[k] else None for k in ('spend','clicks','platform_conversions')}}
    if 'budget_month' in p:
        value=p['budget_month']
        if type(value) not in (int,float) or not math.isfinite(value) or not 0 < value <= 10**9:
            raise VerdugoError('Presupuesto mensual debe ser positivo')
        month=p.get('month',end.strftime('%Y-%m'))
        if not isinstance(month,str) or not re.fullmatch(r'\d{4}-\d{2}',month): raise VerdugoError('Mes YYYY-MM requerido')
        first=day(month+'-01'); days=calendar.monthrange(first.year,first.month)[1]
        last=first+timedelta(days=days-1); cutoff=min(last,now-timedelta(days=1))
        month_rows=rows_between(first,cutoff) if cutoff>=first else []
        elapsed=max(0,(cutoff-first).days+1)
        covered=len({r['day'] for r in month_rows})
        spent=_totals(month_rows)['spend']
        projection=spent/elapsed*days if elapsed and covered==elapsed else None
        out['pacing']={'month':month,'monthly_budget':value,'spent':spent,'complete_days_elapsed':elapsed,
            'days_with_data':covered,'projected_month_end':projection,'budget_used_percent':100*spent/value,
            'projection_note':'Proyección lineal, no promesa; requiere datos de todos los días completos transcurridos.'}
    values=[r['spend'] for r in daily]
    deviation=statistics.pstdev(values) if len(values)>1 else 0
    avg=statistics.mean(values) if values else 0
    out['anomalies']={'method':'z-score simple','threshold':3,'days':[{'day':r['day'],'score':(r['spend']-avg)/deviation} for r in daily if deviation and abs((r['spend']-avg)/deviation)>=3]}
    if len(values)>=10:
        analysis=_analysis(engine,'pyod',{'dataset':dataset,'reference':[[x] for x in values[-200:]],'current':[[x] for x in values[-200:]]})
        if analysis['state']=='available':
            result=analysis['result']
            out['anomalies']={'method':'pyod KNN','days':[{'day':r['day'],'score':score} for r,score,flag in zip(daily[-200:],result['scores'],result['flags']) if flag]}
        else: out['anomalies']['fallback_reason']=analysis['state']
    out['baseline']={'state':'insufficient_data'}
    if len(values)>=2:
        contiguous=all(day(b['day'])-day(a['day'])==timedelta(days=1) for a,b in zip(daily,daily[1:]))
        out['baseline']=_analysis(engine,'statsforecast',{'dataset':dataset,'values':values[-200:],'horizon':7}) if contiguous else {'state':'missing_calendar_days'}
        if out['baseline']['state']=='available': out['baseline']['method']='statsforecast Naive; no precisión validada'
    return out
