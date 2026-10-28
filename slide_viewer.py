import base64, csv, io, os, subprocess, tempfile, logging
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
    stage='validate'
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
                stage="libreoffice_conversion"
                cmd=["libreoffice","-env:UserInstallation=file://"+os.path.join(d,"lo_profile"),"--headless","--convert-to","pdf","--outdir",d,original]
                res=subprocess.run(cmd,capture_output=True,text=True,timeout=105,env={**os.environ,"HOME":d,"XDG_CONFIG_HOME":d})
                pdfpath=os.path.join(d,"uploaded.pdf")
                if res.returncode!=0 or not os.path.isfile(pdfpath):
                    logging.warning("Slide conversion failed: rc=%s stdout=%s stderr=%s",res.returncode,res.stdout[:700],res.stderr[:700])
                    raise ValueError("LibreOffice failed to create PDF")
                stage="pdf_open"
                document=fitz.open(pdfpath)
            else:
                document=fitz.open(stream=content,filetype="pdf")
            if document.is_encrypted: raise ValueError("Password-protected PDF not supported")
            if len(document)>MAX_PAGES:
                notices.append("ตรวจตัวอย่างได้สูงสุด 6 สไลด์/หน้าแรก; หน้าที่เหลือยังไม่ได้ตรวจ")
            pages=[]
            for n in range(min(len(document),MAX_PAGES)):
                stage="render_page_"+str(n+1)
                pix=document[n].get_pixmap(matrix=fitz.Matrix(1.35,1.35),alpha=False)
                im=Image.open(io.BytesIO(pix.tobytes("png")))
                native=document[n].get_text().strip()
                stage="ocr_page_"+str(n+1)
                try:
                    p=page_data(im,n+1)
                except Exception as ocr_error:
                    logging.warning("OCR failed on page %s: %s",n+1,type(ocr_error).__name__)
                    p={"page":n+1,"image":png_data(im),"words":[],"ocr_text":""}
                    notices.append("OCR failed on slide "+str(n+1)+"; preview is still available")
                p["text"]=native + "\n" + p["ocr_text"] if native else p["ocr_text"]
                pages.append(p)
            document.close()
            return {"pages":pages,"warnings":notices}
    except HTTPException:raise
    except subprocess.TimeoutExpired as e:
        logging.exception("Slide processing timed out at %s",stage)
        raise HTTPException(422,"Slide converter timed out at "+stage) from e
    except Exception as e:
        logging.exception("Slide processing failed at %s: %s",stage,type(e).__name__)
        raise HTTPException(422,"Slide processing failed at "+stage+" ("+type(e).__name__+")") from e
