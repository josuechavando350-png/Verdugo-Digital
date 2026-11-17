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
# Used only when the export has no "all clicks" column (common in Meta exports).
SECONDARY = {'link clicks': 'clicks', 'clics en el enlace': 'clicks'}
# Unknown columns are ignored and never stored, except headers that look like personal data.
PII_WORDS = {'email', 'e-mail', 'correo', 'telefono', 'phone', 'celular', 'movil', 'apellido', 'apellidos',
             'address', 'direccion', 'gclid', 'fbclid', 'ip', 'curp', 'rfc'}
PII_PHRASES = ('nombre completo', 'full name', 'first name', 'last name', 'user id', 'id de usuario',
               'nombre del cliente', 'customer name')
EMPTY = ('', '--', '—', '-')
MONTHS = {'ene': 1, 'jan': 1, 'enero': 1, 'january': 1, 'feb': 2, 'febrero': 2, 'february': 2,
          'mar': 3, 'marzo': 3, 'march': 3, 'abr': 4, 'apr': 4, 'abril': 4, 'april': 4,
          'may': 5, 'mayo': 5, 'jun': 6, 'junio': 6, 'june': 6, 'jul': 7, 'julio': 7, 'july': 7,
          'ago': 8, 'aug': 8, 'agosto': 8, 'august': 8, 'sep': 9, 'sept': 9, 'septiembre': 9,
          'september': 9, 'oct': 10, 'octubre': 10, 'october': 10, 'nov': 11, 'noviembre': 11,
          'november': 11, 'dic': 12, 'dec': 12, 'diciembre': 12, 'december': 12}


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise VerdugoError('Usa fechas YYYY-MM-DD')
    try: return date.fromisoformat(value)
    except ValueError: raise VerdugoError('Fecha no válida') from None


def _text_day(value):
    """Dates as the ad platforms print them: 2026-11-01, 1 nov 2026, 1 de noviembre de 2026, Nov 1, 2026."""
    v = _header(value).replace(',', ' ').replace('.', ' ')
    v = re.sub(r'\bde\b', ' ', v); v = re.sub(r'\s+', ' ', v).strip()
    m = re.fullmatch(r'(\d{1,2}) ([a-z]+) (\d{4})', v) or None
    if m and m[2] in MONTHS: d, mo, y = int(m[1]), MONTHS[m[2]], int(m[3])
    else:
        m = re.fullmatch(r'([a-z]+) (\d{1,2}) (\d{4})', v)
        if not (m and m[1] in MONTHS): return None
        d, mo, y = int(m[2]), MONTHS[m[1]], int(m[3])
    try: return date(y, mo, d)
    except ValueError: raise VerdugoError('Fecha no válida') from None


def _days(values):
    """Parse one file's dates with a single format. Slash dates must be unambiguous."""
    if all(re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) for v in values): return [day(v) for v in values]
    if all(re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', v) for v in values):
        parts = [tuple(int(x) for x in v.split('/')) for v in values]
        if any(a > 12 for a, b, _ in parts): order = 'dmy'
        elif any(b > 12 for a, b, _ in parts): order = 'mdy'
        else: raise VerdugoError('Fechas ambiguas (día/mes): exporta con formato AAAA-MM-DD')
        try: return [date(y, b, a) if order == 'dmy' else date(y, a, b) for a, b, y in parts]
        except ValueError: raise VerdugoError('Fecha no válida') from None
    out = [_text_day(v) for v in values]
    if any(d is None for d in out): raise VerdugoError('Usa fechas YYYY-MM-DD')
    return out


def number(value, integer=False):
    """Read 1,234.56 / 1.234,56 / 100,25 / $1,234 / -- as the platforms export them."""
    if not isinstance(value, str): raise VerdugoError('Número inválido')
    v = value.strip().replace('\u00a0', '').replace(' ', '')
    v = re.sub(r'^(MX\$|US\$|\$|MXN|USD)', '', v)
    if v in EMPTY: return Decimal(0)
    if not re.fullmatch(r'[\d.,]+', v) or not v[0].isdigit() or not v[-1].isdigit():
        raise VerdugoError('Número inválido; exporta sin símbolos ni porcentajes')
    grouped = lambda sep: re.fullmatch(r'\d{1,3}(?:' + re.escape(sep) + r'\d{3})+', v)
    if '.' in v and ',' in v:
        dec = '.' if v.rindex('.') > v.rindex(',') else ','
        thou = ',' if dec == '.' else '.'
        whole, _, frac = v.rpartition(dec)
        if not re.fullmatch(r'\d{1,3}(?:' + re.escape(thou) + r'\d{3})*', whole) or not 1 <= len(frac) <= 6:
            raise VerdugoError('Número inválido')
        v = whole.replace(thou, '') + '.' + frac
    elif ',' in v or '.' in v:
        sep = ',' if ',' in v else '.'
        if v.count(sep) > 1 or (integer and grouped(sep)) or (sep == ',' and grouped(sep)):
            if not grouped(sep): raise VerdugoError('Número inválido')
            v = v.replace(sep, '')
        else:
            if not re.fullmatch(r'\d+' + re.escape(sep) + r'\d{1,6}', v): raise VerdugoError('Número inválido')
            v = v.replace(sep, '.')
    try: n = Decimal(v)
    except InvalidOperation: raise VerdugoError('Número inválido') from None
    if not n.is_finite() or not 0 <= n <= 10**9:
        raise VerdugoError('Métrica fuera de rango')
    if integer and n != n.to_integral_value(): raise VerdugoError('Clics e impresiones deben ser enteros')
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


def _decode(raw):
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'): return raw.decode('utf-16')
    return raw.decode('utf-8-sig')


def _is_pii(normalized):
    words = set(re.split(r'[^a-z0-9-]+', normalized))
    return bool(words & PII_WORDS) or any(p in normalized for p in PII_PHRASES)


def _map_header(cells, currency):
    lookup = {alias: key for key, aliases in ALIASES.items() for alias in aliases}
    columns, secondary = [], []
    for cell in cells:
        normalized = _header(cell)
        match = re.fullmatch(r'(importe gastado|amount spent|costo|cost) \(([a-z]{3})\)', normalized)
        if match:
            if match[2].upper() != currency: raise VerdugoError('La moneda del CSV no coincide')
            normalized = match[1]
        if normalized in lookup: columns.append(lookup[normalized])
        elif normalized in SECONDARY: columns.append(None); secondary.append((len(columns)-1, SECONDARY[normalized]))
        elif _is_pii(normalized):
            raise VerdugoError('Columna no admitida: exporta solo métricas diarias, sin datos personales')
        else: columns.append(None)  # ignored metric (CTR, CPC, estado...), never stored
    for index, key in secondary:
        if key not in columns: columns[index] = key
    named = [c for c in columns if c]
    if len(set(named)) != len(named): raise VerdugoError('Faltan columnas requeridas o hay columnas duplicadas')
    return columns


def _find_header(lines, currency):
    """Google puts a title and a date range above the header; skip up to 12 such lines."""
    for index, line in enumerate(lines[:12]):
        for delimiter in (',', ';', '\t'):
            try: cells = next(csv.reader([line], delimiter=delimiter))
            except (csv.Error, StopIteration): continue
            if len(cells) < 4: continue
            names = {_header(c) for c in cells}
            if any(n in ALIASES['day'] for n in names) and any(n in ALIASES['campaign'] for n in names):
                return index, delimiter, _map_header(cells, currency)
    raise VerdugoError('Faltan columnas requeridas o hay columnas duplicadas')


def parse(raw, tenant, platform, currency):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise VerdugoError('CSV vacío o mayor de 5 MiB')
    try:
        content = _decode(raw)
        if '\x00' in content: raise ValueError()
        lines = content.splitlines(keepends=True)
        start, delimiter, columns = _find_header(lines, currency)
        if not {'day','campaign','spend','clicks','impressions','conversions'} <= set(columns):
            raise VerdugoError('Faltan columnas requeridas o hay columnas duplicadas')
        reader = csv.reader(io.StringIO(''.join(lines[start+1:])), delimiter=delimiter, strict=True)
        records = []
        for index, values in enumerate(reader):
            if index >= 20000: raise VerdugoError('CSV supera 20000 filas')
            if not any(v.strip() for v in values): continue
            # Google appends "Total: cuenta / campañas" rows; they are sums, not days.
            if any(_header(v).startswith('total') for v in values[:3]): continue
            if len(values) != len(columns): raise VerdugoError('Fila CSV incompleta')
            records.append({k: v.strip() for k, v in zip(columns, values) if k})
        if not records: raise VerdugoError('CSV sin métricas')
        dates = _days([r['day'] for r in records])
        ends = _days([r['end'] for r in records]) if 'end' in columns else dates
        groups, seen = {}, set()
        for row, when, until in zip(records, dates, ends):
            if until != when: raise VerdugoError('Exporta por día; no se aceptan totales de varios días')
            date_value = when.isoformat()
            if row.get('currency', currency) not in (currency, ''):
                raise VerdugoError('No se pueden mezclar monedas')
            name = row['campaign']
            if not name or len(name) > 200 or any(ord(c) < 32 for c in name):
                raise VerdugoError('Campaña inválida')
            campaign = 'campaign-' + hashlib.sha256((tenant+'\0'+platform+'\0'+name).encode()).hexdigest()[:24]
            nums = {key: number(row[key], key in ('clicks','impressions')) for key in ('spend','clicks','impressions','conversions')}
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
