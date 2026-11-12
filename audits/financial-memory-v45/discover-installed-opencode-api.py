#!/usr/bin/env python3
"""Actual installed native server API discovery, local read-only, zero model calls."""
import json,subprocess,sys,time,socket,hashlib,uuid,os,signal
from pathlib import Path
W=Path(__file__).resolve().parents[2];S=W/'experiments/finance-v45-study';sys.path[:0]=[str(S/'tools/runners'),str(S/'tools')]
from provider import clean_env
from common import kill_group
import run_opencode
work=Path(sys.argv[1]);root=work/'runner';out=W/('audits/financial-memory-v45/oc-api-discovery-'+uuid.uuid4().hex[:8]);out.mkdir()
env=clean_env(root/'home');env['PWD']=str(work/'ws');env['OPENCODE_SERVER_PASSWORD']='local-api-discovery-'+uuid.uuid4().hex
with socket.socket()as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
url='http://127.0.0.1:'+str(port)
with(out/'server.log').open('w')as log:
 server=subprocess.Popen([run_opencode.OPENCODE_BIN,'serve','--hostname','127.0.0.1','--port',str(port)],cwd=work/'ws',env=env,stdout=log,stderr=log,start_new_session=True)
 try:
  got=None
  for i in range(20):
   if server.poll()is not None:raise RuntimeError('server exited; see log')
   check=subprocess.run([run_opencode.OPENCODE_BIN,'api','--server',url,'GET','/openapi.json'],cwd=work/'ws',env=env,capture_output=True,text=True,timeout=8)
   (out/'openapi-cli.stderr').write_text(check.stderr)
   try:got=json.loads(check.stdout)
   except ValueError:got=None
   if check.returncode==0 and isinstance(got,dict)and'paths'in got:break
   time.sleep(.5)
  (out/'actual-openapi.json').write_text(json.dumps(got,ensure_ascii=False,indent=2))
  if not got or'paths'not in got:raise RuntimeError('actual server did not advertise OpenAPI')
  matches=[]
  for path,methods in got['paths'].items():
   for method,spec in methods.items():
    if not isinstance(spec,dict):continue
    if any(x in(path+' '+str(spec.get('operationId',''))).lower()for x in('session','message','history','mcp')):matches.append({'method':method,'path':path,'operationId':spec.get('operationId'),'parameters':spec.get('parameters'),'responses':spec.get('responses')})
  checks=[]
  state=json.loads((root/'memory-controller.json').read_text())
  known=next(iter(state.get('native_sessions',{}).values()),None)
  if known:
   unknown=known[:-1]+('x'if known[-1]!='x'else'y')
   for label,sid in [('known',known),('unknown',unknown)]:
    result=subprocess.run([run_opencode.OPENCODE_BIN,'api','--server',url,'session.message.list','--param','sessionID='+sid],cwd=work/'ws',env=env,capture_output=True,text=True,timeout=8)
    try:answer=json.loads(result.stdout)
    except ValueError:answer=None
    (out/(label+'-session-response.json')).write_text(json.dumps({'returncode':result.returncode,'response':answer,'stderr':result.stderr},ensure_ascii=False,indent=2))
    populated=isinstance(answer,dict)and isinstance(answer.get('data'),list)and bool(answer['data'])
    checks.append({'case':label,'session_id':sid,'nonempty_history':populated})
    if populated!=(label=='known'):raise RuntimeError('Actual known/unknown history guard failed for '+label)
  receipt={'binary':run_opencode.OPENCODE_BIN,'binary_sha256':hashlib.sha256(Path(run_opencode.OPENCODE_BIN).read_bytes()).hexdigest(),'advertised_schema_sha256':hashlib.sha256((out/'actual-openapi.json').read_bytes()).hexdigest(),'read_only_local':True,'external_model_calls':0,'matches':matches,'known_unknown_checks':checks}
  (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps({'out':str(out),'matches':[{'method':m['method'],'path':m['path'],'operationId':m['operationId']}for m in matches]},ensure_ascii=False),flush=True)
 finally:kill_group(server);server.wait(timeout=3)
