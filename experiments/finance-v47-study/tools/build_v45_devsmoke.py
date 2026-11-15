#!/usr/bin/env python3
"""Deterministic NEW dev fixtures, never main-task copies. Not financial live truth.
Run only before seal; generated fixture gold/oracle are independent source transforms.
"""
import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from mcp_snapshot_server import load_entries,digest

DATE='2026-10-29';ASOF='2026-11-02T09:00:00+07:00'
def env(data,unit=None,availability='available',source='synthetic-dev'):
 return {'data':data,'availability':availability,'provenance':{'source':source,'as_of':ASOF,'data_time':DATE,'timezone':'Asia/Ho_Chi_Minh'},'units':unit or {},'warnings':['Synthetic engineering fixture; not independently captured market data.']}
def q(symbol,last):return {'tool':'vn_quote_history','params':{'symbol':symbol,'summary':True},'envelope':env({'symbol':symbol,'last':last,'last_t':DATE,'count':1},{'last':'nghìn đồng'})}
def fs(symbol,rows):return {'tool':'financial_statements','params':{'symbol':symbol,'period':'quarter','statement':'all','periods_n':15},'envelope':env({'symbol':symbol,'scope':'consolidated','periods':['Q2/2026','Q3/2026'],'rows':rows})}
def row(name,a,b,unit='tỷ đồng'):return {'name':name,'unit':unit,'scope':'consolidated','values':{'Q2/2026':a,'Q3/2026':b}}
def resolve(query,symbol=None):return {'tool':'symbol_resolve','params':{'query':query,'limit':5},'envelope':env({'query':query,'resolved':symbol,'ambiguous':False,'candidates':[{'symbol':symbol,'name':query,'asset_class':'vn_stock'}] if symbol else []},availability='available' if symbol else 'empty')}
CASES=[
 ('quote','Giá gần nhất KDH là bao nhiêu nghìn đồng? Nêu ngày dữ liệu.',{'q:KDH':q('KDH',37.25)},'data["q:KDH"]["data"]["last"]','nghìn đồng',DATE),
 ('resolve','Tra tên “Nhà Khang Điền” qua resolver rồi lấy giá gần nhất của mã được phân giải (nghìn đồng).',{'r:KDH':resolve('Nhà Khang Điền','KDH'),'q:KDH':q('KDH',37.25)},'data["q:KDH"]["data"]["last"]','nghìn đồng',DATE),
 ('growth','Doanh thu quý Q3/2026 của DGC tăng bao nhiêu phần trăm so Q2/2026? Dùng doanh thu hợp nhất.',{'fs:DGC':fs('DGC',[row('Doanh thu thuần',420,483)])},'(data["fs:DGC"]["data"]["rows"][0]["values"]["Q3/2026"]/data["fs:DGC"]["data"]["rows"][0]["values"]["Q2/2026"]-1)*100','%','Q2/2026 / Q3/2026'),
 ('margin','Biên lợi nhuận gộp hợp nhất của NLG quý Q3/2026 là bao nhiêu %?',{'fs:NLG':fs('NLG',[row('Doanh thu thuần',300,400),row('Lợi nhuận gộp',60,92)])},'data["fs:NLG"]["data"]["rows"][1]["values"]["Q3/2026"]/data["fs:NLG"]["data"]["rows"][0]["values"]["Q3/2026"]*100','%','Q3/2026'),
 ('scale','Quy đổi giá gần nhất FRT từ đơn vị nguồn sang đồng/cổ phiếu.',{'q:FRT':q('FRT',92.4)},'data["q:FRT"]["data"]["last"]*1000','đồng',DATE),
 ('ratio','Tỷ số LNST trên doanh thu hợp nhất DCM quý Q3/2026 (dạng tỷ lệ, không nhân100) là bao nhiêu?',{'fs:DCM':fs('DCM',[row('Doanh thu thuần',500,600),row('LNST',40,78)])},'data["fs:DCM"]["data"]["rows"][1]["values"]["Q3/2026"]/data["fs:DCM"]["data"]["rows"][0]["values"]["Q3/2026"]','tỷ lệ','Q3/2026'),
 ('aggregate','Trung bình cộng giá gần nhất của DGC, DCM, DPM (nghìn đồng), phải cùng ngày dữ liệu.',{'q:DGC':q('DGC',81.7),'q:DCM':q('DCM',34.8),'q:DPM':q('DPM',42.1)},'sum(data[k]["data"]["last"] for k in ["q:DGC","q:DCM","q:DPM"])/3','nghìn đồng',DATE),
 ('cross-source','Hai nguồn quote DGC và financial_statements (trường close_same_day) cùng ngày dữ liệu: chênh lệch tuyệt đối giữa hai giá bằng bao nhiêu nghìn đồng?',{'q:DGC':q('DGC',81.7),'fs:DGC':{'tool':'financial_statements','params':{'symbol':'DGC','period':'quarter','statement':'all','periods_n':15},'envelope':env({'symbol':'DGC','close_same_day':82.1,'date':DATE},{'close_same_day':'nghìn đồng'},source='synthetic-second-source')}},'abs(data["q:DGC"]["data"]["last"]-data["fs:DGC"]["data"]["close_same_day"])','nghìn đồng',DATE),
 ('chain','Tra resolver cho “Đạm Phú Mỹ”; lấy doanh thu thuần hợp nhất Q3/2026 đúng mã được phân giải, quy ra tỷ đồng.',{'r:DPM':resolve('Đạm Phú Mỹ','DPM'),'fs:DPM':fs('DPM',[row('Doanh thu thuần',810000000000,972000000000,'VND')])},'data["fs:DPM"]["data"]["rows"][0]["values"]["Q3/2026"]/1e9','tỷ đồng','Q3/2026'),
 ('trap-resolver','Phân giải mã không tồn tại ZZDEV45; chỉ lấy giá nếu resolver xác nhận tồn tại.',{'r:ZZDEV45':resolve('ZZDEV45')},None,None,None),
 ('trap-period','Doanh thu hợp nhất DGC Q4/2026 là bao nhiêu tỷ đồng? Chỉ dùng kỳ có trong snapshot.',{'fs:DGC':fs('DGC',[row('Doanh thu thuần',420,483)])},None,None,None),
 ('trap-empty','Giá gần nhất DEVEMPTY là bao nhiêu nghìn đồng?',{'q:DEVEMPTY':{'tool':'vn_quote_history','params':{'symbol':'DEVEMPTY','summary':True},'envelope':env({'symbol':'DEVEMPTY','count':0,'last':None},availability='empty')}},None,None,None),
]

def main():
 target=ROOT/'tasks/devsmoke';target.mkdir(exist_ok=True)
 basegrader=next((ROOT/'tasks/main').glob('*/tests/grader.py')).read_bytes()
 tail=(ROOT/'tasks/smoke/smoke-quote-01/instruction.md').read_text().split('## Ràng buộc chung',1)[1].replace('2026-11-01','2026-11-02')
 for i,(family,question,tools,expr,unit,period) in enumerate(CASES,1):
  tid=f'v45-dev-{i:02d}-{family}';d=target/tid
  for sub in ['environment','solution','tests']:(d/sub).mkdir(parents=True,exist_ok=True)
  payload={'snapshot_date':'2026-11-02','source_review_status':'synthetic_engineering_fixture','note':'New pre-registered dev fixtures; no source/gold copied from main or holdout.','tools':tools}
  (d/'environment/payloads.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
  entries,_=load_entries(d/'environment/payloads.json')
  receipts=[{'tool':v['tool'],'source':v['envelope']['provenance']['source'],'as_of':ASOF,'matched_entry_id':k,'response_sha256':digest(v['envelope'])} for k,v in entries]
  data={k:v['envelope'] for k,v in entries};value=eval(expr,{'abs':abs,'sum':sum,'data':data}) if expr else None
  gold={'task_id':tid,'scoring':'value' if expr else 'refusal','solution':{'value':value},'provenance_contract':receipts,'provenance_catalog':receipts,'required_payload_keys':[k for k,v in entries],'payload_sha256':hashlib.sha256((d/'environment/payloads.json').read_bytes()).hexdigest(),'fixture_kind':'synthetic_engineering_fixture'}
  if expr:gold['expects']=[{'type':'value','path':'value','gold':value,'tol':{'abs':1e-6}},{'type':'unit','path':'unit','accept':[unit]},{'type':'period','path':'period','accept':[period]},{'type':'str_all','path':'source','accept':sorted({v['tool'] for k,v in entries})}]
  else:gold['refusal_tokens']=['không có dữ liệu','không tồn tại','chưa có','không đủ dữ liệu','không tìm thấy']
  (d/'solution/gold.json').write_text(json.dumps(gold,ensure_ascii=False,indent=2)+'\n')
  oracle='''import json,pathlib,sys
p=pathlib.Path(__file__).resolve().parent
gold=json.loads((p/'gold.json').read_text());payload=json.loads((p.parent/'environment/payloads.json').read_text())
data={k:v.get('envelope',v) for k,v in payload['tools'].items()}
'''
  oracle+=f'computed={expr}\nassert abs(computed-gold["solution"]["value"])<1e-8\n' if expr else 'assert gold["solution"]["value"] is None\nassert any(e["availability"]=="empty" for e in data.values()) or all("Q4/2026" not in str(e["data"]) for e in data.values())\n'
  oracle+='print("ORACLE OK")\n';(d/'solution/oracle.py').write_text(oracle)
  (d/'tests/grader.py').write_bytes(basegrader)
  (d/'instruction.md').write_text('# Dev fixture — '+family+'\n\n'+question+'\n\n```json\n{"value":0,"unit":"(đơn vị đề yêu cầu)","period":"(kỳ được hỏi)","source":"'+ ' + '.join(sorted({v['tool'] for k,v in entries}))+'","note":"(tuỳ chọn)"}\n```\n\nTrả đúng một object JSON. Nếu có dữ liệu dùng `value` (số), `unit`, `period`, `source`; nếu không có dữ liệu dùng `value` null và `reason`. Không giả định số trong đề là đáp án.\n\n## Ràng buộc chung'+tail)
  (d/'task.toml').write_text(f'id = "{tid}"\nlevel = "DEV"\nfamily = "{family}"\nversion = 45\nsplit = "devsmoke"\nconfirmatory_eligible = true\ntime_limit_min = 15\nsnapshot_date = "2026-11-02"\n')
 print(json.dumps({'tasks':12,'answerable':9,'traps':3,'trials_per_model':96}))
if __name__=='__main__':main()
