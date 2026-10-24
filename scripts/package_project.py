"""Package reviewable source and aggregates without local validation dependencies."""
from pathlib import Path
import hashlib,json,re,zipfile
ROOT=Path(__file__).resolve().parents[1]
def included(path):
    rel=path.relative_to(ROOT)
    if any(part in {'.validation-deps','__pycache__','.pbi','.venv','raw','private','schemas'} for part in rel.parts):return False
    return path.suffix.lower() not in {'.pbix','.duckdb','.dll','.zip','.nupkg','.pyc'} and path.name!='package_manifest.json'
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and included(p))
def public_content(p):
    content=p.read_bytes()
    if p.relative_to(ROOT).as_posix()=='powerbi/TheCoach.SemanticModel/model.bim':
        model=json.loads(content.decode('utf-8-sig'))
        for expression in model['model'].get('expressions',[]):
            if expression['name']=='DataFolder':
                expression['expression']='"SET_DATA_FOLDER" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
        content=(json.dumps(model,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    return content
for p in files:
    if p.suffix.lower() in {'.md','.py','.sql','.json','.csv','.bim','.pbip','.pbir','.pbism','.txt'}:
        text=public_content(p).decode('utf-8-sig')
        assert not re.search(r'C:[/\\]+Users[/\\]',text,re.I),p
        if p.suffix=='.csv': assert 'user_id' not in text.splitlines()[0].lower(),p
        if p.suffix=='.md':
            for link in re.findall(r'\]\(([^)]+)\)',text):
                if '://' not in link and not link.startswith('#'):
                    assert (p.parent/link.split('#')[0]).exists(),(p,link)
manifest={'status':'Portfolio package; native opening, data loading and three-page display verified by author','files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(public_content(p)).hexdigest()} for p in files]}
dest=ROOT.parent/'the-coach-analytics-github.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.writestr('the-coach-analytics/'+p.relative_to(ROOT).as_posix(),public_content(p))
    z.writestr('the-coach-analytics/package_manifest.json',json.dumps(manifest,indent=2))
print(json.dumps({'archive':dest.name,'files':len(files),'bytes':dest.stat().st_size,'private_path_and_csv_id_scan':'passed','relative_markdown_links':'passed'}))
