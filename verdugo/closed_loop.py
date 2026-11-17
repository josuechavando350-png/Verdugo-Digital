"""Consent-scoped offline conversions. No remote writes without exact local approval."""
import base64
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .common import VerdugoError, digest, encode, identifier, text
from . import license_policy, subscriptions
from .adapters import connection

PIN = 'f253b400dc5924b731fcb42dbcd99e485200581e'
SCHEMA = '''
CREATE TABLE IF NOT EXISTS cycle_leads (
 tenant TEXT, lead_id TEXT, ref_code TEXT, phone_hash TEXT, consent INTEGER NOT NULL,
 created REAL NOT NULL, PRIMARY KEY(tenant,lead_id));
CREATE TABLE IF NOT EXISTS cycle_payments (
 tenant TEXT, event_id TEXT, paid_at TEXT NOT NULL, PRIMARY KEY(tenant,event_id));
CREATE TABLE IF NOT EXISTS cycle_matches (
 tenant TEXT, ref_code TEXT, day TEXT, gclid TEXT, ambiguous INTEGER NOT NULL,
 PRIMARY KEY(tenant,ref_code,day));
CREATE TABLE IF NOT EXISTS cycle_batches (
 tenant TEXT, key TEXT, binding TEXT NOT NULL, rows_json TEXT NOT NULL, PRIMARY KEY(tenant,key));
CREATE TABLE IF NOT EXISTS cycle_uploads (
 tenant TEXT, event_id TEXT, key TEXT NOT NULL, state TEXT NOT NULL,
 amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, paid_at TEXT NOT NULL,
 updated REAL NOT NULL, PRIMARY KEY(tenant,event_id));
'''


def ref_code(gclid):
    return base64.b32encode(hashlib.sha256(gclid.encode()).digest()).decode()[:6]


def attribution(data):
    ref = data.get('ref_code')
    if ref is not None and (not isinstance(ref, str) or not re.fullmatch('[A-Z2-7]{6}', ref)):
        raise VerdugoError('Referencia inválida: seis caracteres A-Z o 2-7')
    phone_hash = None
    if data.get('phone') is not None:
        raw = data['phone']
        if not isinstance(raw, str) or len(raw)>40: raise VerdugoError('Teléfono E.164 inválido')
        normalized = re.sub(r'[ ()-]', '', raw.strip())
        if not re.fullmatch(r'\+[1-9][0-9]{7,14}', normalized):
            raise VerdugoError('Incluye + y código de país; no se adivina el país')
        phone_hash = hashlib.sha256(normalized.encode()).hexdigest()
    consent = data.get('ads_user_data_consent', False)
    if type(consent) is not bool: raise VerdugoError('Consentimiento inválido')
    return {'ref_code': ref, 'phone_hash': phone_hash, 'consent': consent}


def payment_time(value):
    try:
        d = datetime.fromisoformat(value)
        if d.tzinfo is None or d.timestamp()>time.time()+60: raise ValueError()
        return d.astimezone(timezone.utc).isoformat(timespec='seconds')
    except (ValueError, TypeError, OverflowError): raise VerdugoError('Hora del pago inválida; usa ISO 8601 con zona horaria') from None


def _settings(e, api=False):
    subscriptions.check(e)
    cfg = e.config['tenants'][e.tenant].get('services', {}).get('google-ads', {})
    if cfg.get('enabled') is not True or cfg.get('license_reviewed') is not True:
        raise VerdugoError('Revisa y habilita Google Ads en la configuración privada')
    license_policy.check('google-ads', cfg)
    settings = cfg.get('closed_loop', {})
    if settings.get('privacy_reviewed') is not True: raise VerdugoError('Revisión de privacidad requerida')
    for k in ('customer_id', 'conversion_action_id'):
        if not re.fullmatch(r'[0-9]{1,20}', str(settings.get(k, ''))): raise VerdugoError('Cuenta o acción privada inválida')
    name = text(settings.get('conversion_name'), 100)
    if name.lstrip()[0] in '=+-@': raise VerdugoError('Nombre de conversión inválido para CSV')
    try: ZoneInfo(settings['account_timezone'])
    except (KeyError, ValueError, TypeError, ZoneInfoNotFoundError):
        raise VerdugoError('Zona horaria IANA de Google Ads requerida') from None
    if api: e.preflight('google-ads', 'accounts.summary')
    return cfg, settings


def _binding(e):
    cfg,_=_settings(e)
    credentials={k:os.environ.get(cfg[k]) for k in ('token_env','developer_token_env') if isinstance(cfg.get(k),str)}
    return digest({'config':cfg,'credentials':credentials})


def _request(e, suffix, body, write=False):
    cfg, settings = _settings(e, True)
    origin, token, headers = connection('google-ads', cfg)
    if origin != 'https://googleads.googleapis.com': raise VerdugoError('Origen Google Ads fijo requerido')
    login = settings.get('login_customer_id')
    if login is not None:
        if not re.fullmatch('[0-9]{1,20}', str(login)): raise VerdugoError('Cuenta administradora inválida')
        headers['login-customer-id'] = str(login)
    headers['Content-Type'] = 'application/json'
    return {'public': {'service':'google-ads', 'operation':'closed-loop', 'method':'POST',
            'url':origin+'/v26/customers/'+str(settings['customer_id'])+suffix,'body':body},
            'headers':headers, 'mutates':write, 'secret_values':[token,headers['developer-token']]}, cfg


def match(e, day, execute=False):
    if e.role != 'operator': raise VerdugoError('Operator role required')
    cfg, settings = _settings(e, True)
    try:
        d = date.fromisoformat(day)
        today = datetime.now(ZoneInfo(settings['account_timezone'])).date()
        if d.isoformat()!=day or not 0<=(today-d).days<=90: raise ValueError()
    except (ValueError, TypeError): raise VerdugoError('Consulta un día ISO dentro de los últimos 90 días') from None
    query = "SELECT click_view.gclid, segments.date FROM click_view WHERE segments.date = '"+day+"'"
    if not execute: return {'state':'planned', 'day':day, 'query':query,'external_calls_made':False}
    refs = {r[0] for r in e.db.execute('SELECT DISTINCT ref_code FROM cycle_leads WHERE tenant=? AND ref_code IS NOT NULL',(e.tenant,))}
    found = {}; page = None; seen = set()
    # Complete pagination before persisting anything; never claim an incomplete day is unambiguous.
    for _ in range(100):
        req, cfg = _request(e, '/googleAds:search', {'query':query, **({'pageToken':page} if page else {})})
        try: response = e.transport(req, cfg)
        except Exception: raise VerdugoError('No se pudo leer click_view; respuesta privada omitida') from None
        if not isinstance(response, dict) or not isinstance(response.get('results', []), list): raise VerdugoError('Respuesta click_view inválida')
        for row in response.get('results', []):
            try:
                gclid = row['clickView']['gclid']
                if row['segments']['date']!=day or not isinstance(gclid,str) or not re.fullmatch('[A-Za-z0-9_-]{1,512}',gclid): raise ValueError()
            except (KeyError,TypeError,ValueError): raise VerdugoError('Fila click_view inválida') from None
            ref = ref_code(gclid)
            if ref in refs: found.setdefault(ref,set()).add(gclid)
        page = response.get('nextPageToken')
        if not page: break
        if not isinstance(page,str) or len(page)>4096 or page in seen: raise VerdugoError('Paginación click_view inválida')
        seen.add(page)
    else: raise VerdugoError('Límite de paginación: no se guardó un día incompleto')
    counts={"matched":0,"ambiguous":0}
    with e.transaction():
        subscriptions.check(e)
        for ref, ids in found.items():
            old=e.db.execute('SELECT gclid,ambiguous FROM cycle_matches WHERE tenant=? AND ref_code=? AND day=?',(e.tenant,ref,day)).fetchone()
            if old and old['gclid']: ids.add(old['gclid'])
            ambiguous=len(ids)!=1 or bool(old and old['ambiguous'])
            counts['ambiguous' if ambiguous else 'matched']+=1
            e.db.execute('INSERT OR REPLACE INTO cycle_matches VALUES(?,?,?,?,?)',(e.tenant,ref,day,None if ambiguous else next(iter(ids)),int(ambiguous)))
        e.event('closed-loop','closed_loop.matched',{'day':day,'references':len(found)})
    return {'state':'matched','day':day,**counts,'external_calls_made':True}


def _rows(e):
    cfg, settings = _settings(e)
    rows=[]; excluded={}
    events=e.db.execute("SELECT c.*,l.ref_code,l.phone_hash,l.consent,p.paid_at FROM commercial_events c JOIN cycle_leads l ON l.tenant=c.tenant AND l.lead_id=c.lead_id LEFT JOIN cycle_payments p ON p.tenant=c.tenant AND p.event_id=c.event_id WHERE c.tenant=? AND c.kind='won' AND c.dataset='real' ORDER BY c.created,c.event_id",(e.tenant,)).fetchall()
    for event in events:
        reason=None
        prior=e.db.execute('SELECT state FROM cycle_uploads WHERE tenant=? AND event_id=?',(e.tenant,event['event_id'])).fetchone()
        matches=e.db.execute('SELECT * FROM cycle_matches WHERE tenant=? AND ref_code=?',(e.tenant,event['ref_code'])).fetchall()
        if prior and prior['state']!='not_uploaded': reason='already_reserved_or_uploaded'
        elif not event['paid_at']: reason='payment_time_required'
        elif not matches: reason='unmatched'
        elif any(r['ambiguous'] for r in matches) or len({r['gclid'] for r in matches})!=1: reason='ambiguous'
        else:
            start=min(datetime.combine(date.fromisoformat(r['day']),datetime.min.time(),ZoneInfo(settings['account_timezone'])).timestamp() for r in matches)
            if time.time()-start>90*86400: reason='expired'
            elif datetime.fromisoformat(event['paid_at']).timestamp()<start: reason='payment_before_click_day'
        if reason: excluded[reason]=excluded.get(reason,0)+1; continue
        payment=e.record('payment',event['payment_id'])
        if not payment or payment['lead_id']!=event['lead_id'] or payment['dataset']!='real': continue
        wire={'gclid':matches[0]['gclid'],'conversionAction':'customers/'+str(settings['customer_id'])+'/conversionActions/'+str(settings['conversion_action_id']),
              'conversionDateTime':event['paid_at'].replace('T',' '),'conversionValue':payment['amount_minor']/100,
              'currencyCode':payment['currency'],'orderId':event['event_id']}
        if event['phone_hash'] and event['consent'] and time.time()-start <= 63*86400:
            wire['userIdentifiers']=[{'hashedPhoneNumber':event['phone_hash'],'userIdentifierSource':'FIRST_PARTY'}]
            wire['consent']={'adUserData':'GRANTED'}
        rows.append({'event_id':event['event_id'],'amount_minor':payment['amount_minor'],'paid_at':event['paid_at'],'currency':payment['currency'],'wire':wire})
    if len(rows)>50: excluded['batch_limit']=len(rows)-50;rows=rows[:50]
    return rows, excluded, settings


def plan(e, key=None):
    if e.role!='operator': raise VerdugoError('Operator role required')
    rows, excluded, settings=_rows(e)
    key=identifier(key or 'cycle-'+secrets.token_hex(12))
    binding=_binding(e)
    fingerprint=digest({'tenant':e.tenant,'key':key,'rows':rows,'binding':binding})
    public={'service':'google-ads','operation':'closed-loop-upload','event_ids':[r['event_id'] for r in rows], 'payload_digest':digest(rows),'config_binding':binding}
    with e.transaction():
        subscriptions.check(e)
        old=e.db.execute('SELECT hash FROM plans WHERE tenant=? AND key=?',(e.tenant,key)).fetchone()
        if old and old['hash']!=fingerprint: raise VerdugoError('Plan cambiado; usa otra clave y aprobación')
        e.db.execute('INSERT OR IGNORE INTO plans(tenant,key,hash,document) VALUES(?,?,?,?)',(e.tenant,key,fingerprint,encode(public)))
        e.db.execute('INSERT OR IGNORE INTO cycle_batches VALUES(?,?,?,?)',(e.tenant,key,binding,encode(rows)))
    return {'state':'planned','key':key,'fingerprint':fingerprint,'requires_approval':True,'rows':rows,'excluded':excluded,'external_calls_made':False}


def _reserve(e, rows, key, state):
    for r in rows:
        old=e.db.execute('SELECT state FROM cycle_uploads WHERE tenant=? AND event_id=?',(e.tenant,r['event_id'])).fetchone()
        if old and old['state']!='not_uploaded': raise VerdugoError('Evento ya reservado; conciliación requerida')
        e.db.execute('INSERT OR REPLACE INTO cycle_uploads VALUES(?,?,?,?,?,?,?,?)',(e.tenant,r['event_id'],key,state,r['amount_minor'],r['currency'],r['paid_at'],time.time()))


def _outcomes(response, rows):
    if not isinstance(response,dict) or not isinstance(response.get('results'),list) or len(response['results'])!=len(rows): raise VerdugoError('Respuesta de carga inválida')
    failure=response.get('partialFailureError',{}); failed=set()
    if failure.get('code',0):
        for detail in failure.get('details',[]):
            for error in detail.get('errors',[]):
                loc=error.get('location',{}).get('fieldPathElements',[])
                if not loc or loc[0].get('fieldName')!='conversions' or type(loc[0].get('index')) is not int: raise VerdugoError('Fallo parcial sin índice válido')
                index=loc[0]['index']
                if not 0<=index<len(rows): raise VerdugoError('Índice de fallo fuera de lote')
                failed.add(index)
        if not failed: raise VerdugoError('Fallo parcial sin detalle verificable')
    outcomes=[]
    for i,(row,result) in enumerate(zip(rows,response['results'])):
        if i in failed:
            outcomes.append('uncertain');continue
        if not isinstance(result,dict) or any(result.get(k)!=row['wire'][k] for k in ('gclid','conversionAction','conversionDateTime')):
            raise VerdugoError('Resultado de conversión no coincide')
        outcomes.append('uploaded')
    return outcomes


def run(e, key, execute=False):
    if e.role!='operator': raise VerdugoError('Operator role required')
    identifier(key);cfg,settings=_settings(e,True)
    if settings.get('upload_access_reviewed') is not True: raise VerdugoError('Confirma acceso permitido por Google a UploadClickConversions')
    with e.guards.hold(e.tenant,key):
        with e.transaction():
            subscriptions.check(e)
            batch=e.db.execute('SELECT * FROM cycle_batches WHERE tenant=? AND key=?',(e.tenant,key)).fetchone()
            approval=e.db.execute('SELECT * FROM plans WHERE tenant=? AND key=?',(e.tenant,key)).fetchone()
            if not batch or not approval: raise VerdugoError('Plan de ciclo inexistente')
            existing=e.db.execute('SELECT state,result FROM runs WHERE tenant=? AND key=?',(e.tenant,key)).fetchone()
            if existing:return {'state':existing['state'],'replayed':True,'result':json.loads(existing['result']) if existing['result'] else None}
            rows=json.loads(batch['rows_json']);current,_,_=_rows(e)
            current={r['event_id']:r for r in current}
            fingerprint=digest({'tenant':e.tenant,'key':key,'rows':rows,'binding':batch['binding']})
            if approval['hash']!=fingerprint: raise VerdugoError('Plan alterado; aprobación inválida')
            if not rows or batch['binding']!=_binding(e) or any(current.get(r['event_id'])!=r for r in rows): raise VerdugoError('Plan vacío, vencido o cambiado; vuelve a planear')
            if not execute:return {'state':'planned','key':key,'rows':rows,'requires_approval':True}
            if not approval['approved_by'] or approval['used'] or not approval['expires'] or approval['expires']<time.time():
                return {'state':'awaiting_approval','key':key,'fingerprint':approval['hash']}
            _reserve(e,rows,key,'running')
            e.db.execute('UPDATE plans SET used=1 WHERE tenant=? AND key=?',(e.tenant,key))
            e.db.execute('INSERT INTO runs(tenant,key,hash,state,started) VALUES(?,?,?,?,?)',(e.tenant,key,approval['hash'],'running',time.time()))
            e.guards.record(e,key)
        try:
            req,cfg=_request(e,':uploadClickConversions',{'conversions':[r['wire'] for r in rows],'partialFailure':True},True)
            outcomes=_outcomes(e.transport(req,cfg),rows)
        except Exception: outcomes=['uncertain']*len(rows)
        with e.transaction():
            for row,state in zip(rows,outcomes): e.db.execute('UPDATE cycle_uploads SET state=?,updated=? WHERE tenant=? AND event_id=?',(state,time.time(),e.tenant,row['event_id']))
            state='uncertain' if 'uncertain' in outcomes else 'succeeded'
            result={'uploaded':outcomes.count('uploaded'),'reconciliation_required':outcomes.count('uncertain'),'provider_payload_stored':False}
            e.finish(key,state,result)
        return {'state':state,'result':result,'external_calls_made':True}


def export(e, destination):
    if e.role!='operator': raise VerdugoError('Operator role required')
    rows,excluded,settings=_rows(e)
    if not rows: raise VerdugoError('No hay ventas elegibles para exportar')
    path=Path(destination).expanduser().absolute()
    from .backups import _private_dir
    _private_dir(path.parent)
    stream=io.StringIO();writer=csv.writer(stream,lineterminator='\n')
    writer.writerow(['Google Click ID','Conversion Name','Conversion Time','Conversion Value','Conversion Currency'])
    for r in rows:
        if r['wire']['gclid'].startswith(('=','+','-','@')): raise VerdugoError('GCLID incompatible con exportación CSV segura')
        writer.writerow([r['wire']['gclid'],settings['conversion_name'],r['wire']['conversionDateTime'],f"{r['amount_minor']/100:.2f}",r['currency']])
    key='export-'+secrets.token_hex(12)
    with e.transaction():
        subscriptions.check(e);_reserve(e,rows,key,'exporting')
    try:
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:f.write(stream.getvalue());f.flush();os.fsync(f.fileno())
        with e.transaction():
            e.db.execute("UPDATE cycle_uploads SET state='exported' WHERE tenant=? AND key=?",(e.tenant,key))
            e.event(key,'closed_loop.exported',{'rows':len(rows),'uploaded':False})
    except BaseException:
        with e.transaction():
            e.db.execute("UPDATE cycle_uploads SET state='uncertain' WHERE tenant=? AND key=?",(e.tenant,key))
        raise
    return {'state':'exported','rows':len(rows),'uploaded':False,'reconciliation_required':True,'saved_file':str(path),'excluded':excluded}


def reconcile(e,event_id,outcome,evidence,execute=False):
    subscriptions.check(e)
    if e.role!='approver': raise VerdugoError('Separate approver role required')
    identifier(event_id)
    from .commercial import EVIDENCE
    if not isinstance(evidence,str) or not EVIDENCE.fullmatch(evidence): raise VerdugoError('Referencia privada de evidencia inválida')
    if outcome not in ('uploaded','not_uploaded'):raise VerdugoError('Resultado de conciliación inválido')
    if not execute:return {'state':'planned','external_calls_made':False}
    with e.transaction():
        subscriptions.check(e)
        row=e.db.execute('SELECT * FROM cycle_uploads WHERE tenant=? AND event_id=?',(e.tenant,event_id)).fetchone()
        if not row or row['state'] not in ('uncertain','exported','exporting','running'):raise VerdugoError('Evento sin conciliación pendiente')
        # A live worker must not be released for retry while still uploading.
        with e.guards.hold(e.tenant,row['key']):
            e.db.execute('UPDATE cycle_uploads SET state=?,updated=? WHERE tenant=? AND event_id=?',(outcome,time.time(),e.tenant,event_id))
            e.event(event_id,'closed_loop.reconciled',{'outcome':outcome,'evidence_ref':evidence,'actor':e.actor})
            pending=e.db.execute("SELECT COUNT(*) FROM cycle_uploads WHERE tenant=? AND key=? AND state IN ('uncertain','running')",(e.tenant,row['key'])).fetchone()[0]
            if not pending and e.db.execute('SELECT 1 FROM runs WHERE tenant=? AND key=?',(e.tenant,row['key'])).fetchone():
                e.finish(row['key'],'reconciled',{'operator_declared':True,'automatic_retry':False})
    return {'state':outcome,'operator_declared':True,'external_calls_made':False}


def report(e,start=None,end=None):
    subscriptions.check(e)
    start=start or (date.today()-timedelta(days=30)).isoformat();end=end or date.today().isoformat()
    try:
        a=date.fromisoformat(start);b=date.fromisoformat(end)
        if a>b or (b-a).days>=366:raise ValueError()
    except (ValueError,TypeError):raise VerdugoError('Periodo ISO inválido, máximo 366 días') from None
    lo=datetime.combine(a,datetime.min.time(),timezone.utc).timestamp();hi=datetime.combine(b+timedelta(days=1),datetime.min.time(),timezone.utc).timestamp()
    leads=e.db.execute("SELECT l.* FROM cycle_leads l JOIN records r ON r.tenant=l.tenant AND r.id=l.lead_id AND r.kind='lead' WHERE l.tenant=? AND r.dataset='real' AND l.created>=? AND l.created<? AND l.ref_code IS NOT NULL",(e.tenant,lo,hi)).fetchall()
    matched=0
    for l in leads:
        m=e.db.execute('SELECT gclid,ambiguous FROM cycle_matches WHERE tenant=? AND ref_code=?',(e.tenant,l['ref_code'])).fetchall()
        if m and not any(x['ambiguous'] for x in m) and len({x['gclid'] for x in m})==1:matched+=1
    paid=e.db.execute("SELECT c.*,l.ref_code FROM commercial_events c JOIN cycle_payments p ON p.tenant=c.tenant AND p.event_id=c.event_id LEFT JOIN cycle_leads l ON l.tenant=c.tenant AND l.lead_id=c.lead_id WHERE c.tenant=? AND c.kind='won' AND c.dataset='real' AND p.paid_at>=? AND p.paid_at<?",(e.tenant,a.isoformat(),(b+timedelta(days=1)).isoformat())).fetchall()
    won=len({r['lead_id'] for r in paid if r['ref_code']})
    clients={}
    for r in paid:
        payment=e.record('payment',r['payment_id'])
        if payment and r['channel']=='paid':clients.setdefault(payment['currency'],set()).add(r['lead_id'])
    uploads=e.db.execute('SELECT * FROM cycle_uploads WHERE tenant=? AND paid_at>=? AND paid_at<?',(e.tenant,a.isoformat(),(b+timedelta(days=1)).isoformat())).fetchall()
    totals={}
    for r in uploads:
        if r['state']=='uploaded':totals[r['currency']]=totals.get(r['currency'],0)+r['amount_minor']
    spent={r['currency']:r['spend']/1000000 for r in e.db.execute("SELECT currency,SUM(spend_micros) AS spend FROM ads_daily WHERE tenant=? AND dataset='real' AND day BETWEEN ? AND ? GROUP BY currency",(e.tenant,start,end))}
    costs={c:spent[c]/len(clients[c]) if c in spent and clients.get(c) else None for c in spent.keys()|clients.keys()}
    return {'state':'observed_local','tenant':e.tenant,'start_date':start,'end_date':end,
            'whatsapp_clicks_with_reference':None,'whatsapp_measurement':'not_collected_no_network_snippet',
            'leads_with_reference':len(leads),'matched_leads':matched,'won_leads_with_reference':won,
            'uploaded':sum(r['state']=='uploaded' for r in uploads),'uploaded_value_minor_by_currency':totals,
            'cost_per_paid_client_by_currency':costs,'paid_clients_with_payment_time_by_currency':{c:len(ids) for c,ids in clients.items()},
            'cost_scope':'imported_ads_all_platforms_divided_by_declared_paid_channel_clients_same_currency_and_payment_period','reconciliation':[{'event_id':r['event_id'],'state':r['state']} for r in uploads if r['state'] in ('uncertain','running','exporting','exported')],
            'bank_reconciled':False,'external_calls_made':False}
