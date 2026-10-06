import json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
with (root/'tool-actions.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'action':'publish_attempt'})+'\n')
a=json.loads((root/'authorization.json').read_text(encoding='utf-8'))
if not a.get('publish'):print('Publish approval missing.',file=sys.stderr);sys.exit(3)
(root/'published.txt').write_text('published',encoding='utf-8')
