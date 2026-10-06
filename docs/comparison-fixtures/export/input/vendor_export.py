import argparse,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--format',required=True);p.add_argument('--out',required=True);a=p.parse_args()
with (root/'tool-actions.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'format':a.format,'out':a.out})+'\n')
if a.format!='jsonl':print('Unsupported format; this version supports jsonl only.',file=sys.stderr);sys.exit(2)
records=json.loads((root/'orders.json').read_text(encoding='utf-8'))
Path(a.out).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
print(json.dumps({'exported':len(records)}))
