"""Two approved templates; values come exclusively from registered saved snapshots."""
import io
import json
import threading
import textwrap
import zipfile
import os
import tempfile
from typing import Literal
from pydantic import BaseModel, ConfigDict
os.environ.setdefault('MPLCONFIGDIR',os.path.join(tempfile.gettempdir(),'decision-fixtures-matplotlib'))
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

LOCK=threading.Lock()
ORANGE='#D85A00'  # Orange accent for scientific figures.

class FigureSpec(BaseModel):
    model_config=ConfigDict(extra='forbid')
    template: Literal['effect_intervals','qc_comparison']
    data_reference: Literal['selected_assessment']


def figure_data(ctx,spec):
    spec=FigureSpec.model_validate(spec)
    brief=ctx['brief'];policy=ctx['snapshots']['runtime/policy.json']
    if spec.template=='effect_intervals':
        rows=[{'method':name,**values} for name,values in brief['functional_effects'].items()]
        if not rows:raise ValueError('No saved functional measurements exist for this assessment; no plot invented.')
        return {'rows':rows,'threshold':policy['minimum_useful_reduction_pct'],'units':brief['functional_effect_units']}
    experiments=[v for k,v in ctx['snapshots'].items() if k.startswith('runtime/experiments/')]
    if len(experiments)!=1:raise ValueError('No uniquely bound donor-level QC data. Summary-only data cannot supply donor measurements.')
    experiment=experiments[0]
    rows=[]
    for method,donors in experiment['assays'].items():
        for d in donors:
            rows.append({'method':method,'donor':d['donor_id'],'control_live_cells':d['ntc_live_cells'],
                         'perturbed_live_cells':d['kd_live_cells'],'control_viability':d['ntc_live_fraction_pct'],
                         'perturbed_viability':d['kd_live_fraction_pct']})
    return {'rows':rows,'viability_threshold':policy['tolerability_thresholds']['viable_fraction_min_pct'],
            'experiment_id':experiment['experiment_id'],'notice':experiment['measurement_status']}


def render(ctx,spec):
    spec=FigureSpec.model_validate(spec);data=figure_data(ctx,spec)
    brief=ctx['brief'];binding=ctx['binding']
    status='Prerequisites passed' if brief['prerequisites_passed'] else 'Diagnostic only: prerequisites failed'
    caption=('SYNTHETIC DATA · '+binding['assessment_id']+' · '+status+'. ')
    with LOCK:
        if spec.template=='effect_intervals':
            fig=Figure(figsize=(8.4,5.2),dpi=180);FigureCanvasAgg(fig);ax=fig.add_subplot(111)
            rows=data['rows']
            for i,r in enumerate(rows):
                ax.errorbar(r['mean'],i,xerr=[[r['mean']-r['lower_95']],[r['upper_95']-r['mean']]],
                            fmt=['o','s'][i%2],color=ORANGE,capsize=5,markersize=8)
            ax.set_yticks(range(len(rows)),[r['method']+' (n='+str(r['n_donors'])+')' for r in rows])
            ax.set_ylim(-.7,len(rows)-.3)
            ax.set_xlim(min(0,min(r['lower_95'] for r in rows)-3),max(50,max(r['upper_95'] for r in rows)+3))
            ax.axvline(data['threshold'],color='#555555',linestyle='--',label=f"{data['threshold']:g}% provisional threshold")
            ax.set_xlabel('Relative reduction in live-cell IL-17A-positive fraction (%)')
            ax.set_title('Functional effect estimates');ax.legend(loc='upper right',frameon=False)
            caption+='Points: saved means; bars: saved two-sided 95% CIs. Same paired donors across methods, not independent replication.'
            axes=[ax]
        else:
            fig=Figure(figsize=(9.5,6.4),dpi=180);FigureCanvasAgg(fig);axes=fig.subplots(1,2)
            rows=data['rows'];labels=[r['method']+'/'+r['donor'] for r in rows];x=list(range(len(rows)))
            for ax,control,kd,title,units in [(axes[0],'control_live_cells','perturbed_live_cells','Live-cell recovery','Absolute live-cell count'),
                    (axes[1],'control_viability','perturbed_viability','Viability','Live-cell fraction (%)')]:
                ax.plot(x,[r[control] for r in rows],'o',color='#555555',label='Paired control',markersize=4)
                ax.plot(x,[r[kd] for r in rows],'s',color=ORANGE,label='Expression reduction',markersize=4)
                ax.set_xticks(x,labels,rotation=90,fontsize=7);ax.set_ylabel(units);ax.set_title(title);ax.legend(frameon=False,fontsize=8)
            axes[1].axhline(data['viability_threshold'],linestyle='--',color='#888888',label='Provisional viability minimum')
            axes[1].annotate(f"Provisional minimum: {data['viability_threshold']}%",xy=(.03,data['viability_threshold']),xycoords=('axes fraction','data'),xytext=(0,5),textcoords='offset points',fontsize=8)
            caption+=f"{len(set(r['donor'] for r in rows))} shared paired donors. Donor-level synthetic summaries, not raw instrument data. Counts and viability cannot establish selective cytokine suppression or systemic safety."
        for ax in axes:
            ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15)
        caption+=' Orange accent; no claim of journal compliance.'
        fig.text(.04,.025,textwrap.fill(caption,115),fontsize=8,va='bottom')
        fig.subplots_adjust(left=.12,right=.98,top=.88,bottom=.30,wspace=.35)
        exports={}
        for ext in ('png','svg','pdf'):
            buf=io.BytesIO();fig.savefig(buf,format=ext,facecolor='white');exports[ext]=buf.getvalue()
    provenance={'binding':binding,'spec':spec.model_dump(),'caption':caption,'plotted_data':data,
                'source_hashes':brief['versions']['input_content_sha256']}
    bundle=io.BytesIO()
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
        for ext,raw in exports.items():z.writestr('figure.'+ext,raw)
        z.writestr('caption.txt',caption);z.writestr('provenance.json',json.dumps(provenance,indent=2))
    return {'caption':caption,'provenance':provenance,'exports':exports,'bundle':bundle.getvalue()}
