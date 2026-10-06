import argparse,json
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--out',required=True);a=p.parse_args()
with (root/'tool-actions.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'id':a.id,'out':a.out})+'\n')
Path(a.out).write_bytes(b'<html><title>Sign in</title><body>Expired download link</body></html>')
print(json.dumps({'http_status':200,'written':True,'attachment_id':a.id}))
