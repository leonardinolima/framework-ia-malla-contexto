"""Context mesh MVP: standard-library Python, SQLite, optional OpenAI-compatible LLM."""
import json, os, re, sqlite3, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
DB = Path(os.environ.get('MESH_DB', str(BASE/'mesh.sqlite3')))

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),kind TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,source_id TEXT REFERENCES artifacts(id),created_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);''')
    return c

def now(): return datetime.now(timezone.utc).isoformat()
def insert_artifact(c,pid,kind,title,body,source=None):
    aid=str(uuid.uuid4()); c.execute('INSERT INTO artifacts VALUES (?,?,?,?,?,?,?)',(aid,pid,kind,title,body,source,now())); return aid

def extract_requirements(text):
    lines=[x.strip(' \t-*•') for x in text.splitlines() if x.strip()]
    found=[x for x in lines if re.search(r'\b(debe|deberá|necesita|requiere|permitir|registrar|consultar|generar|validar|must|should)\b',x,re.I)]
    return found[:30] if found else [x for x in lines if len(x)>25][:10]

def llm_generate(kind,context):
    key=os.getenv('LLM_API_KEY',''); base=os.getenv('LLM_BASE_URL','https://api.openai.com/v1').rstrip('/'); model=os.getenv('LLM_MODEL','gpt-4o-mini')
    if not key: return None
    prompt={'story':'Redacta una historia de usuario con criterios de aceptación verificables.', 'architecture':'Propón componentes, responsabilidades y decisiones técnicas.', 'test':'Redacta casos de prueba con pasos y resultados esperados.'}[kind]
    payload=json.dumps({'model':model,'messages':[{'role':'system','content':'Eres un asistente de ingeniería de software. Usa SOLO el contexto recibido. Señala supuestos.'},{'role':'user','content':prompt+'\nCONTEXTO:\n'+context}],'temperature':0.2}).encode()
    req=Request(base+'/chat/completions',payload,{'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urlopen(req,timeout=35) as resp: data=json.load(resp)
    return data['choices'][0]['message']['content']

def generate(kind,source):
    generated=llm_generate(kind,source['body'])
    if generated: return generated, 'LLM'
    # Explicitly labeled templates; these are NOT AI-generated outputs.
    templates={
    'story':f"PLANTILLA (sin LLM)\nComo usuario, quiero {source['body'].rstrip('.')} para cumplir la necesidad descrita.\nCriterios: 1. Se registra la operación. 2. Se valida la entrada. 3. Se muestra el resultado.",
    'architecture':f"PLANTILLA (sin LLM)\nInterfaz web → API → almacenamiento SQLite.\nDecisión pendiente: definir componentes específicos para: {source['body']}",
    'test':f"PLANTILLA (sin LLM)\nCaso: validar {source['body']}\nPaso 1: preparar datos válidos. Paso 2: ejecutar operación. Esperado: respuesta correcta y trazable.\nCaso negativo: entrada inválida; esperado: error controlado."}
    return templates[kind], 'TEMPLATE'

def project_exists(c,pid): return c.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone() is not None

def route(method,path,data=None):
    c=connect()
    try:
        if method=='POST' and path=='/api/projects':
            name=(data or {}).get('name','').strip()
            if not name: return 400,{'error':'name requerido'}
            pid=str(uuid.uuid4()); c.execute('INSERT INTO projects VALUES (?,?,?)',(pid,name,now())); c.commit(); return 201,{'id':pid,'name':name}
        if method=='GET' and path=='/api/projects': return 200,{'projects':[dict(r) for r in c.execute('SELECT * FROM projects ORDER BY created_at DESC')]}
        m=re.fullmatch(r'/api/projects/([a-f0-9-]+)/artifacts',path)
        if m and method=='GET':
            pid=m.group(1)
            if not project_exists(c,pid): return 404,{'error':'proyecto no encontrado'}
            return 200,{'artifacts':[dict(r) for r in c.execute('SELECT * FROM artifacts WHERE project_id=? ORDER BY created_at',(pid,))]}
        if m and method=='POST':
            pid=m.group(1)
            if not project_exists(c,pid): return 404,{'error':'proyecto no encontrado'}
            body=(data or {}).get('text','').strip()
            if not body: return 400,{'error':'text requerido'}
            root=insert_artifact(c,pid,'transcript','Transcripción inception',body)
            reqs=extract_requirements(body)
            ids=[insert_artifact(c,pid,'requirement',f'Requisito {i}',r,root) for i,r in enumerate(reqs,1)]
            c.commit(); return 201,{'transcript_id':root,'requirement_ids':ids,'requirements':reqs}
        m=re.fullmatch(r'/api/artifacts/([a-f0-9-]+)/generate',path)
        if m and method=='POST':
            src=c.execute('SELECT * FROM artifacts WHERE id=?',(m.group(1),)).fetchone()
            if not src: return 404,{'error':'artefacto no encontrado'}
            kind=(data or {}).get('kind')
            if kind not in ('story','architecture','test'): return 400,{'error':'kind debe ser story, architecture o test'}
            try: body,mode=generate(kind,src)
            except Exception as e: return 502,{'error':'Error del proveedor LLM: '+str(e)}
            aid=insert_artifact(c,src['project_id'],kind,kind.capitalize()+' de '+src['title'],body,src['id']); c.commit()
            return 201,{'id':aid,'mode':mode,'body':body,'source_id':src['id']}
        return 404,{'error':'ruta no encontrada'}
    finally: c.close()

class Handler(BaseHTTPRequestHandler):
    def respond(self,status,obj):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/':
            raw=(BASE/'index.html').read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        else: self.respond(*route('GET',self.path))
    def do_POST(self):
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>100000: return self.respond(413,{'error':'cuerpo demasiado grande'})
            data=json.loads(self.rfile.read(n))
            self.respond(*route('POST',self.path,data))
        except (ValueError,json.JSONDecodeError) as e: self.respond(400,{'error':str(e)})

if __name__=='__main__':
    port=int(os.environ.get('PORT','8000')); print(f'http://127.0.0.1:{port}',flush=True); ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
