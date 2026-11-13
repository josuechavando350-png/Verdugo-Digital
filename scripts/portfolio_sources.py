#!/usr/bin/env python3
"""Resolve the EXACT 50 candidates against GitHub; never execute their code.

Produces a source/version/license-evidence lock, not an installation certificate.
The read-only workflow token is only sent to api.github.com, never in artifacts.
"""
from __future__ import annotations
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib import request, error, parse

ROOT=Path(__file__).resolve().parents[1]
class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class GitHubReader:
    def __init__(self, token=None):
        self.token=token
    def get(self, path):
        if not path.startswith('/repos/') or '..' in path:
            raise ValueError('repository_endpoint_required')
        url='https://api.github.com'+path
        headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Verdugo-Source-Lock/1.0'}
        if self.token:headers['Authorization']='Bearer '+self.token
        for retry in range(3):
            try:
                # Follow only explicit same-host GitHub API redirects, never leak token.
                opener=request.build_opener(NoRedirect())
                try:
                    with opener.open(request.Request(url,headers=headers),timeout=25) as r:
                        return json.loads(r.read(2_000_000))
                except error.HTTPError as exc:
                    if exc.code in (301,302,307,308):
                        dest=exc.headers.get('Location','');parts=parse.urlsplit(dest)
                        if parts.scheme!='https' or parts.hostname!='api.github.com' or parts.username or parts.password or parts.query or parts.fragment or not parts.path.startswith(('/repos/','/repositories/')):
                            raise RuntimeError('unsafe_redirect') from None
                        with opener.open(request.Request(dest,headers=headers),timeout=25) as r:
                            return json.loads(r.read(2_000_000))
                    raise
            except error.HTTPError as exc:
                if exc.code in (429,502,503,504) and retry<2:
                    time.sleep(2**retry);continue
                raise RuntimeError('github_http_'+str(exc.code)) from None
            except Exception as exc:
                raise RuntimeError(type(exc).__name__) from None
        raise RuntimeError('unreachable')

def resolve(module, reader):
    repo=module['repository'];out={'id':module['id'],'requested_repository':repo,'installed':False,'live_integration_verified':False}
    try:
        meta=reader.get('/repos/'+repo)
        canonical=meta['full_name']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',canonical):raise ValueError('unsafe_repository')
        if meta.get('private') is not False or meta.get('archived') is not False:raise ValueError('private_or_archived')
        branch=meta['default_branch']
        revision=reader.get('/repos/'+canonical+'/commits/'+parse.quote(branch,safe=''))
        sha=revision['sha']
        if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('invalid_commit')
        out.update(canonical_repository=canonical,repository_id=meta['id'],revision=sha,
            source_url='https://github.com/'+canonical+'/tree/'+sha,
            state='source_resolved',pushed_at=meta.get('pushed_at'),license_review='pending',
            license_spdx=(meta.get('license') or {}).get('spdx_id'),
            canonical_name_changed=(repo.lower()!=canonical.lower()))
        try:
            license=reader.get('/repos/'+canonical+'/license?ref='+sha)
            content=base64.b64decode(license['content'])
            out['license_file']={'path':license['path'],'git_blob':license['sha'],'sha256':hashlib.sha256(content).hexdigest()}
        except Exception:
            out['license_file']=None
        return out
    except Exception as exc:
        out.update(state='source_unresolved',error=str(exc)[:100]);return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='evidence/portfolio-sources.json');args=p.parse_args()
    catalog=json.loads((ROOT/'stack/portfolio50.json').read_text())
    if len(catalog['modules'])!=50 or len({m['repository'].lower() for m in catalog['modules']})!=50:raise RuntimeError('exactly_fifty_unique_sources_required')
    reader=GitHubReader(os.environ.get('GH_TOKEN'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        modules=list(pool.map(lambda m:resolve(m,reader),catalog['modules']))
    resolved=sum(m['state']=='source_resolved' for m in modules)
    report={'schema_version':1,'scope':'source_identity_not_installation',
      'commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),
      'selected':50,'source_resolved':resolved,'all_fifty_integrated':False,
      'licenses_approved':False,'production_ready':False,'modules':modules}
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'selected':50,'source_resolved':resolved,'all_fifty_integrated':False}))
    return 0 if resolved==50 else 2
if __name__=='__main__':raise SystemExit(main())
