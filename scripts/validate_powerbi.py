"""Validate native report JSON against a local Microsoft json-schemas checkout."""
import argparse
import json
from pathlib import Path
from jsonschema import validators, RefResolver

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://developer.microsoft.com/json-schemas/'

def validate(schema_root):
    store = {}
    for path in schema_root.rglob('*.json'):
        try:
            obj = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, UnicodeError):
            continue
        if isinstance(obj, dict):
            store[BASE + path.relative_to(schema_root).as_posix()] = obj
            if '$id' in obj:
                store[obj['$id']] = obj
    count = 0
    pbi = ROOT / 'powerbi'
    paths = [pbi/'TheCoach.pbip', pbi/'TheCoach.Report/definition.pbir', pbi/'TheCoach.SemanticModel/definition.pbism']
    paths += list((pbi/'TheCoach.Report/definition').rglob('*.json'))
    for path in paths:
        obj = json.loads(path.read_text(encoding='utf-8'))
        url = obj['$schema']
        schema = store[url]
        resolver = RefResolver(base_uri=url, referrer=schema, store=store)
        validator = validators.validator_for(schema)(schema, resolver=resolver)
        errors = list(validator.iter_errors(obj))
        if errors:
            raise ValueError(f'{path.relative_to(pbi)}: ' + '; '.join(e.message for e in errors[:5]))
        count += 1
    model = json.loads((pbi/'TheCoach.SemanticModel/model.bim').read_text(encoding='utf-8'))['model']
    tables = {t['name']:t for t in model['tables']}
    def inspect(obj, aliases=None):
        aliases = dict(aliases or {})
        if isinstance(obj, dict):
            for source in obj.get('From', []):
                if 'Name' in source and 'Entity' in source:
                    aliases[source['Name']] = source['Entity']
            for kind, member in [('Column','columns'),('Measure','measures')]:
                if kind in obj and 'Expression' in obj[kind] and 'SourceRef' in obj[kind]['Expression']:
                    f = obj[kind]
                    source = f['Expression']['SourceRef']
                    entity = source.get('Entity') or aliases[source['Source']]
                    assert f['Property'] in {x['name'] for x in tables[entity].get(member,[])}, (entity, f['Property'])
            for v in obj.values(): inspect(v, aliases)
        elif isinstance(obj,list):
            for v in obj: inspect(v, aliases)
    for path in paths: inspect(json.loads(path.read_text(encoding='utf-8')))
    for rel in model['relationships']:
        for side in ['from','to']:
            assert rel[side+'Column'] in {c['name'] for c in tables[rel[side+'Table']]['columns']}
    result = {'json_schema_files_passed':count,'visual_bindings':'passed','relationship_bindings':'passed','desktop_open_refresh_render':'not performed','DAX_execution':'not performed'}
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/powerbi_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema-root',type=Path,required=True)
    validate(parser.parse_args().schema_root)
