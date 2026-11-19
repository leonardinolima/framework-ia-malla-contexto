import os, tempfile, unittest
from pathlib import Path
import app
class MVPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); app.DB=Path(self.tmp.name)/'test.sqlite3'; os.environ.pop('LLM_API_KEY',None)
    def tearDown(self): self.tmp.cleanup()
    def test_flow_and_traceability(self):
        status,p=app.route('POST','/api/projects',{'name':'Demo'}); self.assertEqual(status,201)
        pid=p['id']; status,r=app.route('POST',f'/api/projects/{pid}/artifacts',{'text':'El sistema debe registrar tickets.\nEl usuario necesita consultar tickets.'})
        self.assertEqual(status,201); self.assertEqual(len(r['requirement_ids']),2)
        rid=r['requirement_ids'][0]
        status,g=app.route('POST',f'/api/artifacts/{rid}/generate',{'kind':'story'}); self.assertEqual(status,201)
        self.assertEqual(g['source_id'],rid); self.assertEqual(g['mode'],'TEMPLATE')
        status,listing=app.route('GET',f'/api/projects/{pid}/artifacts'); self.assertEqual(len(listing['artifacts']),4)
    def test_validation(self):
        self.assertEqual(app.route('POST','/api/projects',{'name':''})[0],400)
        self.assertEqual(app.route('POST','/api/projects/x/artifacts',{'text':'x'})[0],404)
if __name__=='__main__': unittest.main()
