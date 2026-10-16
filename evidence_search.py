"""Bounded public literature retrieval. Search hits are discovery, never read evidence."""
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from html.parser import HTMLParser
from agent_provider import NoRedirect

LOCK=threading.Lock()
LAST=0.0
OFFICIAL=('www.ncbi.nlm.nih.gov','www.nlm.nih.gov','www.niaid.nih.gov','www.fda.gov','www.ebi.ac.uk')


def fetch(url,headers=None):
    global LAST
    with LOCK:
        time.sleep(max(0,.4-(time.monotonic()-LAST)));LAST=time.monotonic()
        req=urllib.request.Request(url,headers={'User-Agent':'EvidenceWorkbench/1.0',**(headers or {})})
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=20) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('Source exceeds retrieval size limit.')
        return raw


def eutils(name,**params):
    params.update(tool='EvidenceWorkbench')
    if os.getenv('NCBI_EMAIL'):params['email']=os.environ['NCBI_EMAIL']
    return fetch('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'+name+'.fcgi?'+urllib.parse.urlencode(params))


def clean_query(query):
    if not query.strip() or len(query)>500:raise ValueError('Search needs a question of at most 500 characters.')
    if re.search(r'demo[\s_-]*r[1i]',query,re.I):raise ValueError('DEMO-R1 is fictional. Search real biological concepts or methods instead.')
    return query.strip()


def text(node):return ' '.join(''.join(node.itertext()).split()) if node is not None else ''


class PageText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)


class Literature:
    def __init__(self):self.discovered={};self.read={}
    def search(self,query,start_year=None,end_year=None):
        query=clean_query(query)
        groups=[g.strip() for g in query.split('|')]
        if not 1<=len(groups)<=3 or any(not g or len(g.split())>6 for g in groups):
            raise ValueError('Use 1–3 short concept groups, up to six words each, separated by |. Put the most important concept first.')
        if re.search(r'\b(?:19|20)\d{2}\b',query):
            raise ValueError('Supply publication years through start_year/end_year, not query keywords.')
        if any(re.search(r'[\[\]()"{}]|\b(?:AND|OR|NOT)\b',g) for g in groups):
            raise ValueError('Use plain concept groups; the service constructs the Boolean query.')
        year=datetime.now(timezone.utc).year
        if (start_year is None)!=(end_year is None) or (start_year is not None and
                (type(start_year) is not int or type(end_year) is not int or not 1900<=start_year<=end_year<=year)):
            raise ValueError('Supply both publication years, between 1900 and the current year, or neither.')
        dates={} if start_year is None else {'datetype':'pdat','mindate':str(start_year),'maxdate':str(end_year)}
        trace=[];notice=None
        terms=[' AND '.join('('+g+')' for g in groups)]
        if len(groups)>1:terms.append(' AND '.join('('+g+')' for g in groups[:-1]))

        try:
            for term in terms:
                found=json.loads(eutils('esearch',db='pubmed',term=term,retmode='json',retmax=5,sort='relevance',**dates))
                ids=found['esearchresult']['idlist']
                trace.append({'provider':'PubMed','query':term,'date_filter':dates,'returned':len(ids)})
                if ids:break
            if len(trace)>1:notice='PubMed search broadened once by removing the last concept; publication dates unchanged.'
            if not ids:notice='PubMed returned no results for the bounded queries; Crossref metadata fallback used with the same publication-date window. This does not establish absence of relevant literature.' 
            else:
                summaries=json.loads(eutils('esummary',db='pubmed',id=','.join(ids),retmode='json'))['result']
                hits=[]
                for pmid in ids:
                    s=summaries[pmid];sid='PMID:'+pmid
                    hits.append({'source_id':sid,'title':s.get('title'),'authors':[a['name'] for a in s.get('authors',[])],
                        'year':s.get('pubdate'),'pmid':pmid,'doi':next((a['value'] for a in s.get('articleids',[]) if a['idtype']=='doi'),None),
                        'url':'https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/'})
                return self.register(hits,term,'PubMed',notice,trace,dates)
        except Exception:notice='PubMed retrieval failed; Crossref metadata fallback used. No PubMed evidence inferred.'
        try:
            parameters={'query.bibliographic':' '.join(groups),'rows':5}
            if start_year is not None:parameters['filter']=f'from-pub-date:{start_year}-01-01,until-pub-date:{end_year}-12-31'
            params=urllib.parse.urlencode(parameters)
            items=json.loads(fetch('https://api.crossref.org/works?'+params))['message']['items']
            hits=[]
            for s in items:
                doi=s.get('DOI')
                if not doi:continue
                publication_dates=s.get('published',{}).get('date-parts',[])
                hits.append({'source_id':'DOI:'+doi,'title':next(iter(s.get('title',[])),None),
                    'authors':[' '.join(filter(None,[a.get('given'),a.get('family')])) for a in s.get('author',[])],
                    'year':publication_dates[0][0] if publication_dates else None,'doi':doi,'pmid':None,'url':'https://doi.org/'+doi})
            trace.append({'provider':'Crossref','query':parameters['query.bibliographic'],'date_filter':parameters.get('filter'),'returned':len(hits)})
            return self.register(hits,parameters['query.bibliographic'],'Crossref',notice,trace,dates)
        except Exception as exc:raise ValueError('Literature retrieval failed for PubMed and Crossref. No sources were read.') from exc
    def register(self,hits,query,provider,notice=None,trace=None,dates=None):
        for h in hits:
            h.update(query=query,retrieved_at=datetime.now(timezone.utc).isoformat(),provider=provider,access='discovery only',search_trace=trace or [],date_filter=dates or {})
            self.discovered[h['source_id']]=h
        return {'notice':notice,'search_trace':trace or [],'results':hits,'boundary':'Discovery metadata only. Call read_publication before citing findings.'}
    def publication(self,sid):
        if sid not in self.discovered:raise ValueError('Read only a source discovered in this question.')
        source=dict(self.discovered[sid]);study_type=[]
        if sid.startswith('PMID:'):
            root=ET.fromstring(eutils('efetch',db='pubmed',id=source['pmid'],retmode='xml',rettype='abstract'))
            article=root.find('.//PubmedArticle')
            if article is None or text(article.find('.//MedlineCitation/PMID'))!=source['pmid']:raise ValueError('Publication identity mismatch.')
            abstract=' '.join(text(n) for n in article.findall('.//Abstract/AbstractText'))
            study_type=[text(n) for n in article.findall('.//PublicationType')]
        elif sid.startswith('DOI:'):
            value=json.loads(fetch('https://api.crossref.org/works/'+urllib.parse.quote(source['doi'],safe='')))['message']
            if value.get('DOI','').lower()!=source['doi'].lower():raise ValueError('Publication identity mismatch.')
            parser=PageText();parser.feed(value.get('abstract',''));abstract=' '.join(' '.join(parser.parts).split())
            study_type=[value['type']] if value.get('type') else []
        else:raise ValueError('Not a publication ID.')
        source.update(content=abstract[:18000],access='abstract only' if abstract else 'metadata only — no abstract available',
            study_type=study_type or ['Not supplied by provider'],
            applicability_limits='External methods/context only; fictional target not studied. Full text was not retrieved. Abstract cannot establish systemic safety or applicability to this assay.')
        self.read[sid]=source;return source
    def web(self,query):
        query=clean_query(query)
        key=os.getenv('BRAVE_SEARCH_API_KEY')
        if not key:raise ValueError('Official web search is unavailable: BRAVE_SEARCH_API_KEY is not configured. PubMed and Crossref remain available.')
        scoped=query+' ('+' OR '.join('site:'+d for d in OFFICIAL)+')'
        params=urllib.parse.urlencode({'q':scoped,'count':5})
        value=json.loads(fetch('https://api.search.brave.com/res/v1/web/search?'+params,{'X-Subscription-Token':key}))
        sources=[]
        for hit in value.get('web',{}).get('results',[])[:5]:
            url=hit['url'];parsed=urllib.parse.urlsplit(url)
            if parsed.scheme!='https' or parsed.hostname not in OFFICIAL or parsed.port not in (None,443) or parsed.username:continue
            try:
                raw=fetch(url).decode('utf-8');parser=PageText();parser.feed(raw)
                content=' '.join(' '.join(parser.parts).split())[:12000]
            except Exception:continue
            sid='WEB:'+str(len(self.read)+1)
            s={'source_id':sid,'url':url,'title':hit.get('title'),'authors':[],'year':None,'doi':None,'pmid':None,
               'query':query,'retrieved_at':datetime.now(timezone.utc).isoformat(),'provider':'Brave / official page',
               'access':'web page excerpt','content':content,'study_type':['Official context, not a research publication'],
               'applicability_limits':'Retrieved page excerpt only; not target evidence or systemic safety validation.'}
            self.read[sid]=s;sources.append(s)
        return {'sources':sources,'notice':'Official contextual pages only; no search snippets accepted as scientific evidence.'}
