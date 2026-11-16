"""One fixed Meta v26.0 account insights GET; token serialized only by transport."""
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit
from .common import VerdugoError, fields, encode
from .marketing_reads import period

SPECS = {'meta-ads': {'insights.summary': ('GET', '/v26.0/{account_id}/insights')}}
API_VERSION = 'v26.0'
FIELDS = 'spend,clicks,impressions,date_start,date_stop,account_currency'


def authorization(cfg, origin):
    if origin != 'https://graph.facebook.com':
        # Explicit loopback fixtures only; never alternate production origins.
        u = urlsplit(origin)
        if not (cfg.get('allow_local_http') is True and u.scheme == 'http' and u.hostname in ('127.0.0.1','localhost','::1')):
            raise VerdugoError('Meta requires the official Graph origin')
    if cfg.get('api_version') != API_VERSION or cfg.get('account_scope_reviewed') is not True:
        raise VerdugoError('Meta requires v26.0 and reviewed account read scope')
    if not isinstance(cfg.get('account_id'),str) or not re.fullmatch(r'act_[1-9][0-9]{0,29}',cfg['account_id']):
        raise VerdugoError('Reviewed Meta act_ account required')
    period({},cfg)
    return {}


def build(service, operation, params, cfg, origin, token, headers):
    fields(params)
    if operation != 'insights.summary': raise VerdugoError('Unsupported Meta read')
    start,end=period({},cfg)
    query={'fields':FIELDS,'level':'account','time_range':encode({'since':start,'until':end}),'limit':1}
    public={'service':service,'operation':operation,'method':'GET',
        'url':origin+'/v26.0/'+cfg['account_id']+'/insights?'+urlencode(query),
        'body':None,'version':cfg.get('version'),'read_only':True,
        # Token contents do not participate in plans or fingerprints.
        'credential_reference':cfg['token_env'],
        'implementation_binding':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'report_start_date':start,'report_end_date':end,
        'network_policy':{'private':False,'loopback':cfg.get('allow_local_http') is True}}
    return {'public':public,'headers':headers,'mutates':False,'private_query':{'access_token':token},
            'secret_values':[token, urlencode({'access_token':token}).split('=',1)[1]]}


def wire_path(request):
    p=request['public']
    if (p['service'],p['operation'],p['method']) != ('meta-ads','insights.summary','GET'):
        raise VerdugoError('Unsupported private query')
    fields(request['private_query'],('access_token',))
    u=urlsplit(p['url'])
    return u.path+'?'+u.query+'&'+urlencode(request['private_query'])


def _metric(value, integer=False):
    if not isinstance(value,str) or not re.fullmatch(r'\d+(?:\.\d{1,6})?',value):
        raise VerdugoError('Meta metric schema mismatch')
    try: n=Decimal(value)
    except InvalidOperation: raise VerdugoError('Meta metric schema mismatch') from None
    if not n.is_finite() or not 0<=n<=10**15 or (integer and n!=n.to_integral_value()):
        raise VerdugoError('Meta metric outside bounds')
    return int(n) if integer else float(n)


def check(service, operation, response, request):
    if operation!='insights.summary' or not isinstance(response,dict) or 'error' in response:
        raise VerdugoError('Meta insight response rejected')
    rows=response.get('data')
    if not isinstance(rows,list) or len(rows)>1 or any(not isinstance(r,dict) for r in rows):
        raise VerdugoError('Meta account insight collection mismatch')
    paging=response.get('paging',{})
    if not isinstance(paging,dict) or paging.get('next'):
        raise VerdugoError('Meta result is incomplete; pagination is not followed')
    out={'service':service,'operation':operation,'records_in_response':len(rows),'live_verified':False,
         'raw_provider_payload_retained':False,'scope':'one_account_period_aggregate'}
    if not rows: return out | {'spend':0,'clicks':0,'impressions':0}
    row=rows[0]
    if row.get('date_start')!=request['report_start_date'] or row.get('date_stop')!=request['report_end_date']:
        raise VerdugoError('Meta returned a different period')
    currency=row.get('account_currency')
    if not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency):
        raise VerdugoError('Meta account currency missing')
    return out | {'spend':_metric(row.get('spend')),'clicks':_metric(row.get('clicks'),True),
                  'impressions':_metric(row.get('impressions'),True),'currency':currency}
