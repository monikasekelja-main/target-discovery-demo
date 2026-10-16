"""Question-scoped relevance decisions; discovery and reading do not imply acceptance."""
import re


class Relevance:
    def __init__(self):
        self.decisions={}
        self.searches=[]

    def apply(self,decisions,literature):
        for decision in decisions:
            d=decision.model_dump() if hasattr(decision,'model_dump') else dict(decision)
            sid=d['source_id']
            if sid not in literature.discovered and sid not in literature.read:
                raise ValueError('Screen only discovered sources.')
            if not d['reason'].strip():raise ValueError('Explain the source relevance decision.')
            if d['decision']=='relevant':
                content=literature.read.get(sid,{}).get('content','')
                if not d['excerpt'].strip() or d['excerpt'] not in content:
                    raise ValueError('Relevance acceptance requires an exact excerpt from content already read.')
            elif d['decision']=='candidate' and sid in literature.read:
                raise ValueError('After reading, accept with supporting content or reject; do not leave a candidate unresolved.')
            self.decisions[sid]=d

    def require_candidate(self,sid):
        if self.decisions.get(sid,{}).get('decision')!='candidate':
            raise ValueError('Screen the title/metadata as a relevant candidate, with a reason, before reading its abstract.')

    def check_search(self,query,start,end):
        normalized='|'.join(' '.join(g.lower().split()) for g in query.split('|'))
        if any(s['query']==normalized for s in self.searches):
            raise ValueError('Use a distinct focused methods query; repeating the same search does not count.')
        if self.searches and (start,end)!=self.searches[0]['dates']:
            raise ValueError('Keep the original date window during this question; request older supporting methods separately.')
        return {'query':normalized,'dates':(start,end)}

    def require_second_search(self):
        if len(self.searches)<2:
            raise ValueError('Before web fallback, perform a second distinct focused literature search for the required measurement method.')

    def sources(self,literature):
        return {sid:source for sid,source in literature.read.items()
                if self.decisions.get(sid,{}).get('decision')=='relevant'}
