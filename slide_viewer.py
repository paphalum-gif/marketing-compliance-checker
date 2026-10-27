import base64, csv, io, os, subprocess, tempfile
import fitz
from PIL import Image
from fastapi import HTTPException

MAX_SIZE=10_000_000
MAX_PAGES=6

def words_from_image(image):
    image=image.convert("RGB")
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        image.save(tmp.name)
        proc=subprocess.run(["tesseract",tmp.name,"stdout","-l","tha+eng","--psm","11","tsv"],capture_output=True,text=True,timeout=40)
    if proc.returncode:
        raise ValueError("OCR extraction failed")
    words=[]
    for row in csv.DictReader(io.StringIO(proc.stdout),delimiter="\t"):
        t=(row.get("text") or "").strip()
        if not t: continue
        try:
            x,y,w,h=(int(row[k]) for k in ("left","top","width","height"))
            if w>0 and h>0:
                words.append({"text":t,"x":round(x/image.width,6),"y":round(y/image.height,6),"w":round(w/image.width,6),"h":round(h/image.height,6)})
        except (ValueError, KeyError, ZeroDivisionError): pass
    return words[:1200]

def png_data(image):
    b=io.BytesIO()
    image.save(b,format="PNG")
    return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode("ascii")

def page_data(image,page):
    words=words_from_image(image)
    return {"page":page,"image":png_data(image),"words":words,"ocr_text":" ".join(w["text"] for w in words)}

def read_document(filename,content):
    if not content or len(content)>MAX_SIZE:
        raise HTTPException(413,"File must be 1 byte to 10 MB")
    ext=os.path.splitext(filename.lower())[1]
    notices=[]
    if ext in (".png",".jpg",".jpeg",".webp"):
        try:
            im=Image.open(io.BytesIO(content))
            im.load()
            if im.width*im.height>22_000_000:raise ValueError("Image too large")
            return {"pages":[page_data(im,1)],"warnings":[]}
        except Exception as e:
            raise HTTPException(422,"Image could not be read") from e
    if ext not in (".pptx",".pdf"):
        raise HTTPException(415,"Slide preview supports PPTX, PDF or images; DOCX is text-only and not supported in this viewer")
    try:
        with tempfile.TemporaryDirectory() as d:
            if ext==".pptx":
                original=os.path.join(d,"uploaded.pptx")
                with open(original,"wb") as f:f.write(content)
                res=subprocess.run(["libreoffice","-env:UserInstallation=file://"+os.path.join(d,"lo_profile"),"--headless","--convert-to","pdf","--outdir",d,original],capture_output=True,text=True,timeout=105)
                pdfpath=os.path.join(d,"uploaded.pdf")
                if res.returncode!=0 or not os.path.isfile(pdfpath):
                    raise ValueError("PPTX slide conversion failed")
                document=fitz.open(pdfpath)
            else:
                document=fitz.open(stream=content,filetype="pdf")
            if document.is_encrypted: raise ValueError("Password-protected PDF not supported")
            if len(document)>MAX_PAGES:
                notices.append("ตรวจตัวอย่างได้สูงสุด 6 สไลด์/หน้าแรก; หน้าที่เหลือยังไม่ได้ตรวจ")
            pages=[]
            for n in range(min(len(document),MAX_PAGES)):
                pix=document[n].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
                im=Image.open(io.BytesIO(pix.tobytes("png")))
                p=page_data(im,n+1)
                native=document[n].get_text().strip()
                p["text"]=native if len(native)>len(p["ocr_text"]) else p["ocr_text"]
                pages.append(p)
            document.close()
            return {"pages":pages,"warnings":notices}
    except HTTPException:raise
    except Exception as e:raise HTTPException(422,"Could not convert or read document") from e
