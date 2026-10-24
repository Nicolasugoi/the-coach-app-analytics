"""Rebuild the native, editable Power BI project. No data values are embedded."""
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / 'TheCoach.Report'
MODEL = ROOT / 'TheCoach.SemanticModel'
SCHEMA = 'https://developer.microsoft.com/json-schemas/'
NAVY, TEAL, GOLD, MUTED, LIGHT = '#163344', '#007F7A', '#D79B35', '#5C6F7B', '#F2F5F7'

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def sid(path): return SCHEMA + path + '/schema.json'
def rs(name, version='2.0.0'): return sid('fabric/item/report/definition/' + name + '/' + version)
def uid(name): return hashlib.sha256(name.encode()).hexdigest()[:20]

TABLES = {
    'Cohort': ('cohort', [('cohort','string')]),
    'Plan': ('plan', [('plan','string')]),
    'Period': ('period', [('period_days','int64'), ('period_label','string'), ('target_hours','double')]),
    'Week': ('week', [('week_index','int64'), ('week_label','string')]),
    'Module': ('module', [('module','string'), ('module_label','string')]),
    'Goals': ('goals', [('cohort','string'), ('plan','string'), ('period_days','int64'), ('target_hours','double'), ('eligible_users','int64'), ('study_users','int64'), ('goal_users','int64'), ('study_hours','double'), ('app_hours','double'), ('study_days','int64')]),
    'Retention': ('retention', [('cohort','string'), ('plan','string'), ('week_index','int64'), ('eligible_users','int64'), ('checkin_users','int64'), ('study_users','int64'), ('study_days','int64'), ('study_hours','double'), ('app_hours','double'), ('checkin_days','int64')]),
    'Modules': ('modules', [('cohort','string'), ('plan','string'), ('module','string'), ('eligible_users','int64'), ('module_users','int64'), ('repeat_users','int64'), ('module_hours','double'), ('module_days','int64')]),
}
MEASURES = {'Goals': [], 'Retention': [], 'Modules': []}
def measure(table, name, dax, fmt='#,0', description=''):
    MEASURES[table].append({'name':name,'expression':dax,'formatString':fmt,'description':description})

for name, col in [('Eligible learners','eligible_users'),('Learners with study','study_users'),('Goal achievers','goal_users'),('Recorded study hours','study_hours'),('App hours','app_hours'),('Recorded study days','study_days')]:
    measure('Goals',name,f"IF ( HASONEVALUE ( 'Period'[period_days] ), SUM ( Goals[{col}] ) )", '#,0.0' if 'hours' in col else '#,0', 'Complete selected window only. Blank when multiple periods are combined; cohort and plan cells are disjoint.')
measure('Goals','Goal attainment','DIVIDE ( [Goal achievers], [Eligible learners] )','0.0%','Ratio of summed achievers to summed eligible users, including observed zero-activity users under the tracking assumption.')
measure('Goals','Learning participation','DIVIDE ( [Learners with study], [Eligible learners] )','0.0%')
measure('Goals','Mean study hours','DIVIDE ( [Recorded study hours], [Eligible learners] )','0.00 "h"','Mean per eligible user. Five module counters summed; possible overlap remains in raw results.')
measure('Goals','Mean study days','DIVIDE ( [Recorded study days], [Eligible learners] )','0.0')
measure('Goals','Target hours',"SELECTEDVALUE ( 'Period'[target_hours] )",'0 "h"','20 hours over 30 days; 100 hours over 120 or 150 days.')
for name, base in [('30d eligible learners','Eligible learners'),('30d learning participation','Learning participation'),('30d mean study hours','Mean study hours'),('30d mean study days','Mean study days')]:
    fmt = '0.0%' if 'participation' in name else '0.00 "h"' if 'hours' in name else '0.0' if 'days' in name else '#,0'
    measure('Goals',name,f"CALCULATE ( [{base}], REMOVEFILTERS ( 'Period' ), 'Period'[period_days] = 30 )",fmt,'Fixed first 30 days. Filters on cohort and plan remain in effect.')
for name, col in [('Weekly eligible learners','eligible_users'),('Weekly check-in learners','checkin_users'),('Weekly learning learners','study_users'),('Weekly study hours','study_hours')]:
    measure('Retention',name,f"IF ( HASONEVALUE ( 'Week'[week_index] ), SUM ( Retention[{col}] ) )",'#,0.0' if 'hours' in col else '#,0','Complete 7-day observation window only; grand totals across weeks are intentionally blank.')
measure('Retention','Check-in retention','DIVIDE ( [Weekly check-in learners], [Weekly eligible learners] )','0.0%','At least one logged day in the week. Eligible population changes as observation windows mature.')
measure('Retention','Learning retention','DIVIDE ( [Weekly learning learners], [Weekly eligible learners] )','0.0%','Positive recorded study hours on at least one day in the week; not the same as a login.')
measure('Retention','Check-in learning gap','[Check-in retention] - [Learning retention]','0.0%')
for week in [0,4,8,12]:
    measure('Retention',f'Week {week} learning',f"CALCULATE ( [Learning retention], REMOVEFILTERS ( 'Week' ), 'Week'[week_index] = {week} )",'0.0%',f'Fixed week {week} since first Pro activation; keeps cohort and plan filters.')
for name,col in [('Module eligible learners','eligible_users'),('Module learners','module_users'),('Module repeat learners','repeat_users'),('Module hours','module_hours'),('Module days','module_days')]:
    measure('Modules',name,f"IF ( HASONEVALUE ( 'Module'[module] ), SUM ( Modules[{col}] ) )",'#,0.0' if 'hours' in col else '#,0','Only meaningful for one module. Blank total across modules prevents duplicate user counts and overlapping time totals.')
measure('Modules','Module adoption','DIVIDE ( [Module learners], [Module eligible learners] )','0.0%')
measure('Modules','Repeat among adopters','DIVIDE ( [Module repeat learners], [Module learners] )','0.0%','At least two distinct days using the module among module adopters during first 30 days.')
measure('Modules','Hours per adopter','DIVIDE ( [Module hours], [Module learners] )','0.00 "h"')
measure('Modules','Days per adopter','DIVIDE ( [Module days], [Module learners] )','0.0')

def model():
    tables=[]
    for name,(file,cols) in TABLES.items():
        columns=[]
        for col, typ in cols:
            obj={'name':col,'dataType':typ,'sourceColumn':col,'summarizeBy':'none'}
            if name in MEASURES: obj['isHidden']=True
            if name == 'Week' and col == 'week_label': obj['sortByColumn']='week_index'
            if name == 'Period' and col == 'period_label': obj['sortByColumn']='period_days'
            columns.append(obj)
        types=', '.join('{"%s", %s}' % (c,{'string':'type text','int64':'Int64.Type','double':'type number'}[t]) for c,t in cols)
        expression=[
            'let',
            '    Folder = if Text.EndsWith(DataFolder, "/") or Text.EndsWith(DataFolder, "\\") then DataFolder else DataFolder & "/",',
            f'    Source = Csv.Document(File.Contents(Folder & "{file}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
            '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
            '    Typed = Table.TransformColumnTypes(Headers, {' + types + '}, "en-US")',
            'in', '    Typed']
        table={'name':name,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]}
        if name in MEASURES: table['measures']=MEASURES[name]
        tables.append(table)
    rels=[]
    for fact, dims in [('Goals',[('Cohort','cohort'),('Plan','plan'),('Period','period_days')]),('Retention',[('Cohort','cohort'),('Plan','plan'),('Week','week_index')]),('Modules',[('Cohort','cohort'),('Plan','plan'),('Module','module')])]:
        for dim,col in dims:
            rels.append({'name':f'{fact}_{dim}','fromTable':fact,'fromColumn':col,'fromCardinality':'many','toTable':dim,'toColumn':col,'toCardinality':'one','crossFilteringBehavior':'oneDirection','isActive':True})
    obj={'name':'TheCoach','compatibilityLevel':1567,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-US','tables':tables,'relationships':rels,'expressions':[{'name':'DataFolder','kind':'m','expression':'"SET_DATA_FOLDER" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]','description':'Set this to the full local folder containing public aggregate CSVs: data/processed. Do not select the private source directory.'}],'annotations':[{'name':'PBI_QueryOrder','value':json.dumps(['DataFolder']+list(TABLES))}]}}
    write(MODEL/'model.bim',obj)
    write(MODEL/'definition.pbism',{'$schema':sid('fabric/item/semanticModel/definitionProperties/1.0.0'),'version':'4.0','settings':{'qnaEnabled':False}})
    return obj

def literal(v):
    if isinstance(v,bool): value=str(v).lower()
    elif isinstance(v,(int,float)): value=f'{v}D'
    else: value="'" + str(v).replace("'","''") + "'"
    return {'expr':{'Literal':{'Value':value}}}
def color(c): return {'solid':{'color':literal(c)}}
def props(**kw): return [{'properties':kw}]
def field(table,col,kind='Column'): return {kind:{'Expression':{'SourceRef':{'Entity':table}},'Property':col}}
def projection(table,col,kind='Column',label=None):
    p={'field':field(table,col,kind),'queryRef':f'{table}.{col}','nativeQueryRef':label or col}
    if kind=='Column': p['active']=True
    return p
def c(table,col,label=None): return projection(table,col,'Column',label)
def m(table,name,label=None): return projection(table,name,'Measure',label)

def container(title='', bg='#FFFFFF', border=True):
    return {'title':props(show=literal(bool(title)),text=literal(title),fontColor=color(NAVY),fontSize=literal(12),fontFamily=literal('Segoe UI'),alignment=literal('left')),
            'background':props(show=literal(True),color=color(bg),transparency=literal(0)),
            'border':props(show=literal(border),color=color('#DCE4E8'),radius=literal(8)),
            'visualHeader':props(show=literal(False))}

class Page:
    def __init__(self, key, title, subtitle):
        self.name=uid(key); self.path=REPORT/'definition/pages'/self.name; self.count=0
        self.meta={'$schema':rs('page'),'name':self.name,'displayName':title,'displayOption':'FitToPage','height':900,'width':1600,'objects':{'background':props(color=color(LIGHT),transparency=literal(0))}}
        self.text('header','THE COACH  /  LEARNING ANALYTICS',40,20,1100,28,13,TEAL)
        self.text('title',title,40,54,1510,54,29,NAVY)
        self.text('subtitle',subtitle,40,114,1520,38,12,MUTED)
    def add(self,key,typ,x,y,w,h,roles=None,title='',objects=None,sort=None,filter_config=None):
        self.count+=1; n=uid(self.name+key)
        v={'visualType':typ,'visualContainerObjects':container(title),'drillFilterOtherVisuals':True}
        if roles: v['query']={'queryState':{r:{'projections':ps} for r,ps in roles.items()}}
        if sort: v['query']['sortDefinition']={'sort':[{'field':sort[0]['field'],'direction':sort[1]}],'isDefaultSort':False}
        if objects: v['objects']=objects
        obj={'$schema':rs('visualContainer'),'name':n,'position':{'x':x,'y':y,'z':self.count,'width':w,'height':h,'tabOrder':self.count},'visual':v}
        if filter_config: obj['filterConfig']=filter_config
        write(self.path/'visuals'/n/'visual.json',obj)
        return obj,self.path/'visuals'/n/'visual.json'
    def text(self,key,text,x,y,w,h,size=11,ink=MUTED):
        obj,path=self.add(key,'textbox',x,y,w,h,objects={'general':props(paragraphs=[{'textRuns':[{'value':text,'textStyle':{'fontFamily':'Segoe UI','fontSize':f'{size}pt','color':ink}}]}])})
        obj['visual']['visualContainerObjects']=container(bg=LIGHT,border=False); write(path,obj)
    def slicer(self,key,table,col,x,w=240,title=None,selected=None,single=False):
        objects={'data':props(mode=literal('Dropdown')),'selection':props(singleSelect=literal(single),selectAllCheckboxEnabled=literal(not single)),'header':props(show=literal(False)),'items':props(fontColor=color(NAVY),textSize=literal(11))}
        if selected is not None:
            value=f'{selected}L' if isinstance(selected,int) else "'"+selected+"'"
            sf={'Version':2,'From':[{'Name':'s','Entity':table,'Type':0}],'Where':[{'Condition':{'In':{'Expressions':[{'Column':{'Expression':{'SourceRef':{'Source':'s'}},'Property':col}}],'Values':[[{'Literal':{'Value':value}}]]}}}]}
            objects['general']=props(filter={'filter':sf})
        self.add(key,'slicer',x,164,w,72,{'Values':[c(table,col)]},title or col,objects)
    def card(self,key,table,metric,x,title):
        self.add(key,'card',x,254,365,108,{'Values':[m(table,metric)]},title,{'labels':props(color=color(TEAL),fontSize=literal(30),labelDisplayUnits=literal(1)),'categoryLabels':props(show=literal(False))})
    def finish(self,footer):
        self.text('footer',footer,40,853,1520,34,9,MUTED)
        write(self.path/'page.json',self.meta)

def chart_objects():
    return {'dataPoint':props(defaultColor=color(TEAL)),'categoryAxis':props(show=literal(True),fontSize=literal(10),labelColor=color(MUTED)), 'valueAxis':props(show=literal(True),fontSize=literal(10),labelColor=color(MUTED)),'legend':props(show=literal(True),position=literal('Top'),fontSize=literal(10)),'labels':props(show=literal(False))}
def table_objects():
    return {'grid':props(gridVertical=literal(False),gridHorizontal=literal(True),rowPadding=literal(7)),'columnHeaders':props(fontColor=color(NAVY),backColor=color('#E8F0F2'),fontSize=literal(10)),'values':props(fontColor=color(NAVY),fontSize=literal(10)),'total':props(totals=literal(False))}

def build_pages():
    goals=Page('goals','01  Goal attainment','Can eligible learners reach 20 hours in 30 days or 100 hours in 120 / 150 days? Raw recorded hours; complete windows only.')
    goals.slicer('cohort','Cohort','cohort',40,470,'Activation cohort')
    goals.slicer('plan','Plan','plan',540,470,'Pro plan')
    goals.slicer('period','Period','period_days',1040,520,'Window in days · select one',30,True)
    for i,(metric,title) in enumerate([('Eligible learners','Eligible learners'),('Goal attainment','Reached the target'),('Mean study hours','Mean recorded study hours'),('Target hours','Hours target per learner')]): goals.card('kpi'+str(i),'Goals',metric,40+i*385,title)
    goals.add('cohortattain','clusteredBarChart',40,386,740,280,{'Category':[c('Cohort','cohort','Cohort')],'Y':[m('Goals','Goal attainment')]},'Target attainment by activation cohort',chart_objects(),(c('Cohort','cohort'),'Ascending'))
    goals.add('planhours','clusteredColumnChart',810,386,750,280,{'Category':[c('Plan','plan','Plan')],'Y':[m('Goals','Mean study hours'),m('Goals','Target hours')]},'Mean study hours and target by plan',chart_objects())
    goals.add('goalaudit','tableEx',40,688,1520,145,{'Values':[c('Cohort','cohort','Cohort'),c('Plan','plan','Plan'),m('Goals','Eligible learners'),m('Goals','Learners with study'),m('Goals','Goal achievers'),m('Goals','Goal attainment'),m('Goals','Mean study hours'),m('Goals','Mean study days')]},'Audit the denominator · scroll for all cohort / plan groups',table_objects())
    goals.finish('First activation = earliest Pro activation. 30 / 120 / 150 days are operational windows. Cells with <10 eligible users omitted. Missing logs treated as inactivity only under complete tracking.')
    retention=Page('retention','02  Retention: showing up vs learning','A check-in does not necessarily contain learning. Each week uses its own fully observed population; compare the two rates within the same week.')
    retention.slicer('cohort','Cohort','cohort',40,470,'Activation cohort')
    retention.slicer('plan','Plan','plan',540,470,'Pro plan')
    retention.slicer('week','Week','week_label',1040,520,'Week · filters charts; cards are fixed milestones')
    for i,w in enumerate([0,4,8,12]): retention.card('kpi'+str(w),'Retention',f'Week {w} learning',40+i*385,f'Week {w} · recorded learning')
    retention.add('retentionline','lineChart',40,386,970,280,{'Category':[c('Week','week_label','Week since activation')],'Y':[m('Retention','Check-in retention'),m('Retention','Learning retention')]},'Weekly check-in and learning retention',chart_objects(),(c('Week','week_label'),'Ascending'))
    retention.add('retentiondenominators','tableEx',1040,386,520,280,{'Values':[c('Week','week_label','Week'),m('Retention','Weekly eligible learners','Eligible'),m('Retention','Check-in retention','Check-in'),m('Retention','Learning retention','Learning')]},'Eligible population changes by week',table_objects(),(c('Week','week_label'),'Ascending'))
    retention.add('cohortmatrix','pivotTable',40,688,1520,145,{'Rows':[c('Cohort','cohort','Cohort')],'Columns':[c('Week','week_label','Week')],'Values':[m('Retention','Learning retention')]},'Cohort comparison · learning retention',{'rowHeaders':props(fontSize=literal(10),fontColor=color(NAVY)),'columnHeaders':props(fontSize=literal(10),fontColor=color(NAVY)),'values':props(fontSize=literal(10),fontColor=color(TEAL)),'subTotals':props(rowSubtotals=literal(False),columnSubtotals=literal(False))})
    retention.finish('Week 0 = days 0–6 after activation. Complete weeks only. Totals across weeks are blank. Cohort differences and associations are descriptive; purchase history and tracking completeness are unknown.')
    modules=Page('modules','03  Module adoption and repeat learning','First 30 days after activation. Adoption means positive recorded module hours; repeat means activity on at least two distinct days.')
    modules.slicer('cohort','Cohort','cohort',40,470,'Activation cohort')
    modules.slicer('plan','Plan','plan',540,470,'Pro plan')
    modules.slicer('module','Module','module_label',1040,520,'Module · filters module charts')
    for i,(metric,title) in enumerate([('30d eligible learners','30-day eligible learners'),('30d learning participation','Any recorded study · 30 days'),('30d mean study hours','Mean recorded study hours · 30 days'),('30d mean study days','Mean study days · 30 days')]): modules.card('kpi'+str(i),'Goals',metric,40+i*385,title)
    modules.add('adoption','clusteredBarChart',40,386,740,280,{'Category':[c('Module','module_label','Module')],'Y':[m('Modules','Module adoption')]},'Module adoption · share of eligible learners',chart_objects(),(m('Modules','Module adoption'),'Descending'))
    modules.add('repeat','clusteredBarChart',810,386,750,280,{'Category':[c('Module','module_label','Module')],'Y':[m('Modules','Repeat among adopters')]},'Repeat learning · share of module adopters',chart_objects(),(m('Modules','Repeat among adopters'),'Descending'))
    modules.add('moduleaudit','tableEx',40,688,1520,145,{'Values':[c('Module','module_label','Module'),m('Modules','Module eligible learners','Eligible'),m('Modules','Module learners','Adopters'),m('Modules','Module repeat learners','Repeat learners'),m('Modules','Module adoption','Adoption'),m('Modules','Repeat among adopters','Repeat / adopters'),m('Modules','Hours per adopter'),m('Modules','Days per adopter')]},'Module depth · people can use more than one module',table_objects())
    modules.finish('The top cards summarize all learning, independent of module selection. Module totals are blank to avoid duplicate people / overlapping time. “Other” counts as learning. No causal impact is inferred.')
    names=[p.name for p in [goals,retention,modules]]
    write(REPORT/'definition/pages/pages.json',{'$schema':rs('pagesMetadata','1.0.0'),'pageOrder':names,'activePageName':names[0]})

def main():
    model()
    write(ROOT/'TheCoach.pbip',{'$schema':sid('fabric/pbip/pbipProperties/1.0.0'),'version':'1.0','artifacts':[{'report':{'path':'TheCoach.Report'}}],'settings':{'enableAutoRecovery':True}})
    write(REPORT/'definition.pbir',{'$schema':sid('fabric/item/report/definitionProperties/2.0.0'),'version':'4.0','datasetReference':{'byPath':{'path':'../TheCoach.SemanticModel'}}})
    write(REPORT/'definition/version.json',{'$schema':rs('versionMetadata','1.0.0'),'version':'4.0.0'})
    write(REPORT/'definition/report.json',{'$schema':rs('report'),'themeCollection':{},'settings':{'useStylableVisualContainerHeader':True,'defaultFilterActionIsDataFilter':True,'defaultDrillFilterOtherVisuals':True,'allowChangeFilterTypes':True,'allowInlineExploration':True,'useEnhancedTooltips':True},'objects':{'outspacePane':props(expanded=literal(False),visible=literal(True))}})
    build_pages()
    print('Wrote 3 native PBIR pages, 8 imported tables, 9 relationships, and '+str(sum(map(len,MEASURES.values())))+' DAX measures.')

if __name__=='__main__': main()
