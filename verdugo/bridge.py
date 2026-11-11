"""One declared contact operation across CRM, inbox and canonical identity."""
from .common import VerdugoError, fields, identifier, text, digest
from . import workflow


def contact_bridge(engine, profile, execute=False):
    fields(profile, ('lead_id', 'first_name', 'email', 'dataset'), ('last_name',))
    identifier(profile['lead_id'])
    first = text(profile['first_name'], 100)
    if 'last_name' in profile and not isinstance(profile['last_name'], str):
        raise VerdugoError('last_name must be text')
    last = text(profile['last_name'], 100) if profile.get('last_name') else ''
    email = text(profile['email'], 254)
    if email.count('@') != 1 or ' ' in email:
        raise VerdugoError('Invalid email')
    if profile['dataset'] not in ('demo', 'real'):
        raise VerdugoError('Explicit demo or real dataset required')
    wid = 'contact-' + digest([engine.tenant, profile['lead_id'], profile['dataset']])[:24]
    person = {'first_name': first, 'last_name': last, 'email': email}
    base = {'lead_id': profile['lead_id'], 'dataset': profile['dataset']}
    spec = {'id': wid, 'steps': [
        {'id': 'capture', 'service': 'core', 'operation': 'lead.capture',
         'params': base | {'name': (first+' '+last).strip(), 'email': email}},
        {'id': 'crm', 'service': 'twenty', 'operation': 'people.create',
         'params': person, 'depends_on': ['capture']},
        {'id': 'crm-link', 'service': 'core', 'operation': 'identity.bind',
         'params': base | {'service': 'twenty', 'source_key': wid+'-crm'},
         'depends_on': ['crm']},
        {'id': 'inbox', 'service': 'chatwoot', 'operation': 'contacts.create',
         'params': person, 'depends_on': ['crm-link']},
        {'id': 'inbox-link', 'service': 'core', 'operation': 'identity.bind',
         'params': base | {'service': 'chatwoot', 'source_key': wid+'-inbox'},
         'depends_on': ['inbox']},
        {'id': 'summary', 'service': 'core', 'operation': 'identity.summary',
         'params': base, 'depends_on': ['inbox-link']}]}
    return workflow.run(engine, spec, execute)
