import os,base64,secrets,io,subprocess,tempfile
from fastapi import FastAPI,UploadFile,File,Request
from fastapi.responses import HTMLResponse,JSONResponse
from pydantic import BaseModel
from PIL import Image
app=FastAPI(title="Marketing Compliance Checker - Public Demo")
@app.middleware("http")
async def auth(req:Request,nxt):
 u,p=os.getenv("DEMO_USER"),os.getenv("DEMO_PASSWORD")
 if not u or not p:return JSONResponse({"error":"Demo auth unconfigured"},503)
 try:
  scheme,encoded=req.headers.get("authorization","").split(" ",1)
  a,b=base64.b64decode(encoded,validate=True).decode().split(":",1)
  ok=scheme.lower()=="basic" and secrets.compare_digest(a,u) and secrets.compare_digest(b,p)
 except Exception:ok=False
 if not ok:return HTMLResponse("Authentication required",401,headers={"WWW-Authenticate":'Basic realm="Marketing Compliance Demo"'})
 return await nxt(req)
class Check(BaseModel):
 brand:str="KFC"
 product:str="credit_card"
 campaign:str="cashback"
 channel:str="facebook"
 caption:str=""
 artwork_text:str=""
 campaign_terms:str=""
@app.get("/api/health")
def health():return {"status":"ok","mode":"demo","ai_enabled":False}
@app.post("/api/ocr")
async def ocr(file:UploadFile=File(...)):
 from extractor import extract_file
 raw=await file.read(10_000_001)
 try:
  return extract_file(file.filename or "",raw)
 except Exception as e:
  return JSONResponse({"error":str(e)},422)
@app.post("/api/screen")
def screen(req:Check):
 findings=[]
 def add(rule,loc,evidence,why,fix,level="High",status="potential_issue"):
  findings.append({"rule_id":rule,"material":loc,"evidence":evidence,"message":why,"suggestion":fix,"severity":level,"status":status,"source":"Illustrative demo checks; not approved policy"})
 for loc,txt in (("artwork",req.artwork_text),("caption",req.caption)):
  low=txt.lower()
  for phrase in ("อนุมัติ 100%","อนุมัติแน่นอน","ไม่ตรวจเครดิต","กู้ได้ทุกคน","guaranteed approval","100% approved"):
   if phrase in low:add("AD-DEMO-001",loc,phrase,"Potential misleading or unverified loan claim","Review claim and provide verifiable support")
  for phrase in ("xxx","[insert]","tbd"):
   if phrase in low:add("TC-DEMO-001",loc,phrase,"Unfilled campaign term placeholder","Replace with confirmed campaign terms","Medium")
  if ("0%" in low or "ฟรี" in low or "free" in low) and not req.campaign_terms.strip():
   add("TC-DEMO-002",loc,"0% / free","Terms were not provided, so the claim cannot be verified","Enter approved offer terms","Medium","needs_human_review")
 if not req.artwork_text.strip():add("OCR-DEMO-001","artwork","","Artwork text not available for evaluation","Upload image and verify OCR output","Medium","not_evaluated")
 if req.product in ("credit_card","personal_loan","nano_finance") and req.channel in ("facebook","instagram","tiktok"):
  for loc,txt in (("artwork",req.artwork_text),("caption",req.caption)):
   if not any(x in txt.lower() for x in ("คำเตือน","ใช้เท่าที่จำเป็น","ชำระคืน","borrow responsibly")):
    add("RL-DEMO-001",loc,"","Possible product warning not detected","Verify correct warning with Compliance; this check is illustrative","High","needs_human_review")
 return {"mode":"DEMO ONLY — NOT APPROVAL","rule_version":"illustrative-0.1","counts":{"issues":sum(x["status"]=="potential_issue" for x in findings),"needs_review":sum(x["status"]=="needs_human_review" for x in findings),"not_evaluated":sum(x["status"]=="not_evaluated" for x in findings)},"findings":findings,"coverage":{"ai":False,"policy_approved":False,"full_rule_catalog":False,"ocr":True}}
HTML='''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Marketing Compliance Checker</title><style>body{font:15px system-ui;background:#f3f6fa;color:#21304a;margin:0}header{background:#182e53;color:white;padding:22px max(20px,calc((100vw - 1000px)/2))}main{max-width:1000px;margin:22px auto;padding:0 15px}.box{background:white;padding:23px;border-radius:14px;margin:16px 0;box-shadow:0 2px 10px #2231}h1{font-size:25px}label{display:block;font-weight:600;margin:14px 0 5px}select,textarea,input{box-sizing:border-box;width:100%;border:1px solid #c6d0de;border-radius:7px;padding:10px;font:inherit}textarea{min-height:100px}button{background:#1768d5;color:white;border:0;border-radius:8px;padding:11px 18px;font:inherit;font-weight:650;cursor:pointer;margin:10px 7px 0 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}.warn{color:#a54d12}.item{border-left:4px solid #e49c1e;padding:13px;background:#fbfcfe;margin:13px 0}.muted{color:#626f80;font-size:13px}img{max-width:100%;max-height:230px;display:none;margin:12px 0}#result{display:none}@media(max-width:650px){.grid{grid-template-columns:1fr}}.canvaswrap{position:relative;display:inline-block;max-width:100%}.artimage{display:block!important;max-height:460px;max-width:100%}.hl{position:absolute;border:2px solid #ef9200;background:#f3ba174d;pointer-events:none}.schematic{position:relative;width:100%;aspect-ratio:16/9;background:#fff;border:1px solid #b7c5d9;overflow:hidden}.region{position:absolute;overflow:hidden;font-size:10px;color:#2e3847;white-space:pre-wrap}.region.hit{background:#ffdd83;border:2px solid #e49c1e}pre.readable{white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto;background:#f8fafc;padding:12px}mark{background:#ffdb82}#evidenceview{margin-top:22px;padding:15px;border:1px solid #dce2ea;border-radius:10px}</style><header><h1>Marketing Compliance Checker</h1><div>Public Demo · Thai / English OCR · Draft Pre-Screening</div></header><main><div class="box"><strong class="warn">DEMO ONLY — NOT COMPLIANCE APPROVAL</strong><p class="muted">Use synthetic content only. Do not upload confidential documents, customer data, or unreleased campaigns. AI analysis is disabled; findings are illustrative.</p></div><div class="box"><h2>01 — Campaign Setup</h2><div class="grid"><div><label>Brand</label><select id="brand"><option>KFC</option><option>KIT</option><option>Other</option></select></div><div><label>Product</label><select id="product"><option value="credit_card">Credit Card</option><option value="personal_loan">Personal Loan</option><option value="nano_finance">Nano Finance</option><option value="other">Other</option></select></div><div><label>Campaign Type</label><select id="campaign"><option value="cashback">Cashback</option><option value="installment">Installment / 0%</option><option value="premium">Premium / Voucher</option><option value="branding">Branding</option><option value="other">Other</option></select></div><div><label>Channel</label><select id="channel"><option>facebook</option><option>instagram</option><option>tiktok</option><option>line</option><option>banner</option></select></div></div><label>Confirmed Campaign Terms (optional)</label><textarea id="campaign_terms" placeholder="Add synthetic campaign terms for demo testing"></textarea></div><div class="box"><h2>02 — Artwork & Caption</h2><label>Artwork PNG/JPG/WEBP/PPTX/PDF/DOCX (max 10MB)</label><input type="file" accept=".png,.jpg,.jpeg,.webp,.pptx,.pdf,.docx" id="art"><img id="preview"><button onclick="extract()">Extract Artwork Text (OCR)</button><span id="ocrstatus" class="muted"></span><label>Artwork OCR Text (editable)</label><textarea id="artwork_text" placeholder="Upload and extract text or enter it manually"></textarea><label>Caption</label><textarea id="caption" placeholder="Enter marketing caption"></textarea><button onclick="screen()">Run Pre-Screening</button></div><div class="box" id="result"><h2>03 — Screening Results</h2><div id="summary"></div><div id="evidenceview"></div><div id="items"></div><button onclick="screen()">04 — Re-Screen</button><button onclick="exportReport()">Download JSON Report</button></div></main><script>let report=null;const el=id=>document.getElementById(id);el("art").onchange=()=>{let f=el("art").files[0];if(f){if(f.type.startsWith("image/")){el("preview").src=URL.createObjectURL(f);el("preview").style.display="block"}else{el("preview").style.display="none"}el("ocrstatus").textContent=f.name}};async function extract(){let f=el("art").files[0];if(!f)return alert("Please select artwork");let d=new FormData();d.append("file",f);el("ocrstatus").textContent="Extracting...";try{let r=await fetch("/api/ocr",{method:"POST",body:d});let x=await r.json();if(!r.ok)throw Error(x.error||"OCR failed");extraction=x;el("artwork_text").value=x.text;el("ocrstatus").textContent=x.status+" — "+(x.warnings||[]).join("; ")+" — verify extracted text"}catch(e){el("ocrstatus").textContent="OCR error: "+e.message}}function safe(t){return String(t??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}async function screen(){let d={};for(let k of ["brand","product","campaign","channel","caption","artwork_text","campaign_terms"])d[k]=el(k).value;try{let r=await fetch("/api/screen",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});if(!r.ok)throw Error(await r.text());report=await r.json();evidenceView();el("result").style.display="block";el("summary").textContent=report.mode+" · Issues: "+report.counts.issues+" · Human review: "+report.counts.needs_review+" · Not evaluated: "+report.counts.not_evaluated;el("items").innerHTML=report.findings.map(f=>'<div class="item"><b>'+safe(f.rule_id)+' · '+safe(f.material)+' · '+safe(f.status)+'</b><p>'+safe(f.message)+'</p><p><b>Evidence:</b> '+safe(f.evidence||"Not identified")+'</p><p><b>Suggested action:</b> '+safe(f.suggestion)+'</p><div class="muted">'+safe(f.source)+'</div></div>').join("")||"<p>No issues detected by limited demo rules. This is not a compliance approval.</p>";el("result").scrollIntoView({behavior:"smooth"})}catch(e){alert("Screening failed: "+e.message)}}
let extraction=null;
function evidenceView(){
 let result=el("evidenceview");if(!result)return;
 let hits=(report?.findings||[]).filter(x=>x.material==="artwork"&&x.evidence).map(x=>x.evidence.toLowerCase());
 let regs=extraction?.regions||[];
 let matched=regs.filter(r=>hits.some(h=>h&&((r.text||"").toLowerCase().includes(h)||h.includes((r.text||"").toLowerCase()) && (r.text||"").length>3)));
 let src=el("preview").src, isImg=el("preview").style.display!=="none" && el("art").files[0]?.type.startsWith("image/");
 let html="<h3>Artwork Evidence Viewer</h3><p class='muted'>กรอบสีส้ม = ข้อความที่ตรงกับ Finding เท่านั้น · ไม่พบคำเตือนจึงไม่มีตำแหน่งให้ Highlight</p>";
 if(isImg){
   html+="<div class='canvaswrap'><img alt='Uploaded artwork' src='"+safe(src)+"' class='artimage'>";
   html+=matched.filter(r=>r.page===1).map(r=>"<div title='"+safe(r.text)+"' class='hl' style='left:"+(r.x*100)+"%;top:"+(r.y*100)+"%;width:"+(r.w*100)+"%;height:"+(r.h*100)+"%'></div>").join("");
   html+="</div>";
 } else if(extraction?.file_type===".pptx"||extraction?.file_type===".pdf"){
   let max=Math.min((extraction.pages||[]).length,20);
   html+="<p class='muted'>ตำแหน่งจากโครงสร้างเอกสารโดยประมาณ ไม่ใช่ภาพ Render สไลด์จริง</p>";
   for(let page=1;page<=max;page++){
     html+="<h4>"+safe(extraction.file_type.toUpperCase())+" · "+page+"</h4><div class='schematic'>";
     html+=regs.filter(r=>r.page===page).slice(0,250).map(r=>"<div class='region "+(matched.includes(r)?"hit":"")+"' title='"+safe(r.text)+"' style='left:"+(Math.max(0,r.x)*100)+"%;top:"+(Math.max(0,r.y)*100)+"%;width:"+(Math.min(1,r.w)*100)+"%;height:"+(Math.max(.015,r.h)*100)+"%'>"+safe(r.text)+"</div>").join("");
     html+="</div>";
   }
 } else html+="<p>ดูข้อความที่ Extract ได้ด้านล่าง</p>";
 let raw=el("artwork_text").value;
 let escaped=safe(raw);
 for(let h of hits.filter(Boolean).sort((a,b)=>b.length-a.length).slice(0,12)){
   let needle=safe(h);if(needle)escaped=escaped.replaceAll(needle,"<mark>"+needle+"</mark>");
 }
 html+="<details><summary>ข้อความที่อ่านจากไฟล์ (คลิกเพื่อดูพร้อม Highlight)</summary><pre class='readable'>"+escaped+"</pre></details>";
 result.innerHTML=html;
}
function exportReport(){if(!report)return;let b=new Blob([JSON.stringify(report,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="screening-demo-report.json";a.click();URL.revokeObjectURL(a.href)}</script></html>'''
@app.get("/",response_class=HTMLResponse)
def home():
 from fastapi.responses import RedirectResponse
 return RedirectResponse(url="/review",status_code=302)

@app.post("/api/preview")
async def preview_slides(file:UploadFile=File(...)):
 from slide_viewer import read_document
 data=await file.read(10_000_001)
 return read_document(file.filename or "upload",data)

@app.get("/review",response_class=HTMLResponse)
def review_home():
 with open("ui.html",encoding="utf-8") as f:
  return HTMLResponse(f.read(),headers={"Cache-Control":"no-store"})
