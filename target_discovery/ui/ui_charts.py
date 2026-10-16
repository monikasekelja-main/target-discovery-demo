"""Charts consume saved facts. No biological calculation or policy evaluation."""
import plotly.graph_objects as go
from target_discovery.ui.ui_service import interval_rows

TEAL='#17645B'

def functional_chart(brief,threshold):
    rows=interval_rows(brief)
    invalid=brief['prerequisites_passed'] is not True
    fig=go.Figure()
    for row in rows:
        fig.add_trace(go.Scatter(x=[row['mean']],y=[row['method']],mode='markers',
            marker={'size':13,'color':'#A34F35' if invalid else TEAL},
            error_x={'type':'data','symmetric':False,'array':[row['upper_95']-row['mean']],
                     'arrayminus':[row['mean']-row['lower_95']],'thickness':2},
            name=row['method'],hovertemplate=f"{row['method']}: {row['mean']:.1f}%<br>95% CI {row['lower_95']:.1f}–{row['upper_95']:.1f}%<extra></extra>"))
    lo=min([-5]+[r['lower_95']-3 for r in rows]);hi=max([50]+[r['upper_95']+3 for r in rows]+[threshold+5])
    fig.add_vline(x=threshold,line_dash='dash',line_color='#9A6B25')
    fig.add_annotation(x=threshold,y=1.08,yref='paper',text=f'{threshold:g}% provisional threshold',
                       showarrow=False,xanchor='left',yanchor='bottom')
    fig.update_layout(height=250,margin={'l':5,'r':15,'t':40,'b':20},showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font={'color':'#253933'},
        xaxis={'title':'Relative reduction in live-cell IL-17A-positive fraction (%)','range':[lo,hi],'gridcolor':'#E3E8E4'},
        yaxis={'categoryorder':'array','categoryarray':['KD-B','KD-A'],'fixedrange':True})
    return fig


def prediction_chart(prediction):
    points=prediction['predictions']
    fig=go.Figure(go.Scatter(x=[p['expression_change_pct'] for p in points],y=[p['signature_change'] for p in points],
        mode='lines+markers',line={'color':TEAL},marker={'size':9}))
    fig.update_layout(height=260,margin={'l':10,'r':10,'t':15,'b':20},
        xaxis_title='Expression change (%)',yaxis_title='Signature change (standardized units)',
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
    return fig
