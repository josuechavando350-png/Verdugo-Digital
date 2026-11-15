"""Bounded original-library transforms and evaluation; no retrieval or model calls."""
from .common import VerdugoError, fields, identifier, integer

SPECS = {
    'chronos': ('series.quantize', 'chronos-forecasting', '2.3.2'),
    'gliner': ('entities.evaluate', 'gliner', '0.2.30'),
    'graphiti': ('pairs.batch', 'graphiti-core', '0.31.2'),
    'openbb': ('prices.validate', 'openbb-core', '2.0.1'),
    'people-also-ask': ('questions.extract', 'people-also-ask', '0.0.6'),
    'jobspy': ('description.clean', 'python-jobspy', '1.4.1'),
}
EXTRA = {'graphiti': {'httpx': '0.28.1'}}
PROFILES = {s: ('ENTITIES021' if s in ('chronos','gliner') else 'CONTENT021') for s in SPECS}


def validate(service, operation, p):
    from .local_runtime import finite, string, validate as base
    if service not in SPECS or operation != SPECS[service][0]: raise VerdugoError('Unsupported content operation')
    required = {'chronos':('values',),'gliner':('expected','predicted'),'graphiti':('items','max_group'),
                'openbb':('currency','rows'),'people-also-ask':('html',),'jobspy':('html',)}[service]
    fields(p,('dataset',*required))
    if p['dataset'] not in ('demo','real'):raise VerdugoError('An explicit dataset is required')
    if service in ('people-also-ask','jobspy'):return base('trafilatura','html.extract',p)
    if service == 'chronos':
        if not isinstance(p['values'],list) or not 1 <= len(p['values']) <= 500:raise VerdugoError('Provide 1..500 observations')
        for v in p['values']:finite(v,-1e6,1e6)
    elif service == 'gliner':
        expected,predicted=p['expected'],p['predicted']
        if (not isinstance(expected,list) or not isinstance(predicted,list) or not 1 <= len(expected) <= 20
                or len(expected)!=len(predicted)):raise VerdugoError('Provide 1..20 matched annotation documents')
        for rows in (expected,predicted):
            for entities in rows:
                if not isinstance(entities,list) or len(entities)>30:raise VerdugoError('At most 30 entities per document')
                seen=set()
                for entity in entities:
                    fields(entity,('label','start','end'));identifier(entity['label'])
                    integer(entity['start'],0,10000);integer(entity['end'],entity['start']+1,10001)
                    key=(entity['label'],entity['start'],entity['end'])
                    if key in seen:raise VerdugoError('Duplicate annotation')
                    seen.add(key)
        if not any(expected):raise VerdugoError('Reference annotations cannot all be empty')
    elif service == 'graphiti':
        items=p['items']
        if not isinstance(items,list) or not 2 <= len(items) <= 12:raise VerdugoError('Provide 2..12 item identifiers')
        for item in items:identifier(item)
        if len(set(items))!=len(items):raise VerdugoError('Duplicate item')
        integer(p['max_group'],2,min(4,len(items)))
    elif service == 'openbb':
        from datetime import date
        if p['currency'] not in ('MXN','USD','EUR'):raise VerdugoError('Explicit supported currency required')
        if not isinstance(p['rows'],list) or not 1<=len(p['rows'])<=100:raise VerdugoError('Provide 1..100 price rows')
        dates=[]
        for row in p['rows']:
            fields(row,('date','open','high','low','close','volume'))
            try:
                if not isinstance(row['date'],str) or date.fromisoformat(row['date']).isoformat()!=row['date']:raise ValueError()
            except ValueError as exc:raise VerdugoError('ISO calendar dates required') from exc
            dates.append(row['date'])
            for key in ('open','high','low','close'):finite(row[key],0,1e9)
            integer(row['volume'],0,10**12)
            if not row['low']<=min(row['open'],row['close'])<=max(row['open'],row['close'])<=row['high']:
                raise VerdugoError('OHLC range mismatch')
        if dates != sorted(set(dates)):raise VerdugoError('Prices require distinct ascending dates')


def run(service,p):
    if service == 'chronos':
        import torch
        from chronos import ChronosConfig, MeanScaleUniformBins
        config=ChronosConfig(tokenizer_class='MeanScaleUniformBins',tokenizer_kwargs={},context_length=500,
            prediction_length=1,n_tokens=4096,n_special_tokens=2,pad_token_id=0,eos_token_id=1,
            use_eos_token=False,model_type='seq2seq',num_samples=1,temperature=1.0,top_k=1,top_p=1.0)
        codec=MeanScaleUniformBins(-15,15,config)
        data=torch.tensor([p['values']],dtype=torch.float32)
        bins,mask,scale=codec.context_input_transform(data)
        recovered=codec.output_transform(bins.unsqueeze(1),scale).reshape(-1)
        return {'bins':bins[0].tolist(),'reconstructed':recovered.tolist(),
                'maximum_absolute_error':float((recovered-data[0]).abs().max()),'scale':float(scale[0]),
                'model_loaded':False,'forecast_generated':False}
    if service == 'gliner':
        from gliner.evaluation.evaluator import BaseEvaluator
        def entities(rows):return [[(e['label'],(e['start'],e['end'])) for e in doc] for doc in rows]
        scores=BaseEvaluator.compute_prf(entities(p['expected']),entities(p['predicted']))
        return {**{k:float(v) for k,v in scores.items()},'documents':len(p['expected']),
                'scope':'supplied span annotations; micro averaging','model_loaded':False,'entities_predicted':False}
    if service == 'graphiti':
        from itertools import combinations
        from graphiti_core.utils.content_chunking import generate_covering_chunks
        groups=generate_covering_chunks(p['items'],p['max_group'])
        covered=set()
        for items,indices in groups:
            if items != [p['items'][i] for i in indices] or len(items)>p['max_group']:raise ValueError('Invalid native group')
            covered.update(tuple(sorted(pair)) for pair in combinations(indices,2))
        if len(covered)!=len(p['items'])*(len(p['items'])-1)//2:raise ValueError('Native groups missed pairs')
        return {'groups':[items for items,_ in groups],'covered_pairs':len(covered),'coverage_verified':True,
                'graph_written':False,'llm_calls':0}
    if service == 'openbb':
        from openbb_core.provider.standard_models.equity_historical import EquityHistoricalData
        rows=[EquityHistoricalData.model_validate(row).model_dump(mode='json',exclude_none=True) for row in p['rows']]
        return {'rows':rows,'currency':p['currency'],'row_count':len(rows),'native_schema_valid':True,
                'market_data_fetched':False,'prices_independently_verified':False}
    if service == 'people-also-ask':
        from bs4 import BeautifulSoup
        from people_also_ask.parser import extract_related_questions
        questions=extract_related_questions(BeautifulSoup(p['html'],'html.parser'))
        if len(questions)>100:raise ValueError('Question output budget')
        return {'questions':questions,'count':len(questions),'search_executed':False}
    if service == 'jobspy':
        from jobspy.util import plain_converter
        text=plain_converter(p['html'])
        return {'text':text,'characters':len(text),'jobs_scraped':False,'contacts_extracted':False}
    raise ValueError('Unsupported content operation')
