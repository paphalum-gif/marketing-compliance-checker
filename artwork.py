"""Demo document-to-slide preview conversion; no data persistence."""
import base64
import csv
import io
import os
import subprocess
import tempfile
import zipfile
from PIL import Image, ImageOps, UnidentifiedImageError
import fitz

MAX_FILE_SIZE = 10_000_000
MAX_PAGES = 8
MAX_PX = 18_000_000
Image.MAX_IMAGE_PIXELS = MAX_PX

def _preview(img):
    b = io.BytesIO()
    img.convert("RGB").save(b, format="JPEG", quality=78, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")

def _ocr_words(img):
    img = img.convert("RGB")
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        img.save(f.name)
        proc = subprocess.run(
            ["tesseract", f.name, "stdout", "-l", "tha+eng", "--psm", "11", "tsv"],
            capture_output=True, text=True, timeout=50
        )
    if proc.returncode:
        raise ValueError("OCR engine could not read the artwork")
    words=[]
    for r in csv.DictReader(io.StringIO(proc.stdout), delimiter="\t"):
        txt=(r.get("text") or "").strip()
        if not txt:
            continue
        try:
            x,y,w,h=(int(r[k]) for k in ("left","top","width","height"))
        except (KeyError,ValueError):
            continue
        if w<=0 or h<=0:
            continue
        words.append({"text":txt[:120],
                      "x":round(x/img.width,6),"y":round(y/img.height,6),
                      "w":round(w/img.width,6),"h":round(h/img.height,6)})
    return words[:1800]

def _native_words(page):
    words=[]
    for w in page.get_text("words")[:2000]:
        x0,y0,x1,y1,token,*_=w
        if token.strip():
            words.append({"text":token[:120],
                          "x":round(x0/page.rect.width,6),"y":round(y0/page.rect.height,6),
                          "w":round((x1-x0)/page.rect.width,6),
                          "h":round((y1-y0)/page.rect.height,6)})
    return words

def _convert(src,td):
    # Private LibreOffice user profile avoids concurrent conversion lock contention.
    profile=os.path.join(td,"lo-profile")
    proc=subprocess.run(["libreoffice","-env:UserInstallation=file://"+profile,"--headless",
                         "--convert-to","pdf","--outdir",td,src],
                        capture_output=True,text=True,timeout=100,env={**os.environ,"HOME":td})
    out=os.path.join(td,"upload.pdf")
    if proc.returncode != 0 or not os.path.isfile(out):
        raise ValueError("Unable to render this document as slide images")
    return out

def extract_upload(filename,data):
    filename=filename or "unnamed"
    ext=os.path.splitext(filename.lower())[1]
    if ext not in (".png",".jpg",".jpeg",".webp",".pptx",".pdf",".docx"):
        raise ValueError("รองรับ PNG, JPG, WEBP, PPTX, PDF, DOCX; โปรดบันทึก PPT รุ่นเก่าเป็น PPTX")
    if not data or len(data)>MAX_FILE_SIZE:
        raise ValueError("ไฟล์ต้องมีขนาดไม่เกิน 10 MB")
    if ext in (".pptx",".docx"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            info=z.infolist()
            if len(info)>3000 or sum(x.file_size for x in info)>100_000_000:
                raise ValueError("Document expansion limit exceeded")
    previews=[]
    warnings=[]
    if ext in (".png",".jpg",".jpeg",".webp"):
        try:
            img=ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
            img.load()
            if img.width*img.height>MAX_PX:
                raise ValueError("Image dimension limit exceeded")
            img.thumbnail((1400,1400))
        except (UnidentifiedImageError,OSError):
            raise ValueError("File is not a supported image")
        words=_ocr_words(img)
        previews.append({"page":1,"label":"Artwork","image_data_url":_preview(img),
                         "text":" ".join(w["text"] for w in words),"words":words})
    else:
        with tempfile.TemporaryDirectory() as td:
            if ext==".pdf":
                pdf_path=os.path.join(td,"upload.pdf")
                with open(pdf_path,"wb") as f:f.write(data)
            else:
                src=os.path.join(td,"upload"+ext)
                with open(src,"wb") as f:f.write(data)
                pdf_path=_convert(src,td)
            with fitz.open(pdf_path) as pdf:
                if pdf.is_encrypted:
                    raise ValueError("Password protected documents are unsupported")
                total=len(pdf)
                if total>MAX_PAGES:
                    warnings.append("อ่านเพียง %d หน้าแรก จาก %d หน้า; ส่วนที่เหลือยังไม่ได้ตรวจ"%(MAX_PAGES,total))
                for i in range(min(total,MAX_PAGES)):
                    page=pdf[i]
                    scale=min(1.6,1500/max(page.rect.width,page.rect.height))
                    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
                    img=Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr=_ocr_words(img)
                    native=_native_words(page)
                    native_text=page.get_text().strip()
                    ocr_text=" ".join(w["text"] for w in ocr)
                    # Preserve text layer where available, but display real OCR coordinates.
                    text=native_text if len(native_text)>len(ocr_text)*1.3 else ocr_text
                    if native and not ocr:
                        ocr=native
                    previews.append({
                      "page":i+1,"label":("Slide" if ext==".pptx" else "Page")+" "+str(i+1),
                      "image_data_url":_preview(img),"text":text[:10000],
                      "words":ocr[:1800]
                    })
    combined="\n\n".join("[%s]\n%s"%(p["label"],p["text"]) for p in previews)
    if not combined.strip() or not any(p["text"].strip() for p in previews):
        warnings.append("ไม่สามารถอ่านข้อความบน Artwork ได้ กรุณาตรวจด้วยตนเอง")
    return {"status":"extracted" if any(p["text"].strip() for p in previews) else "not_evaluated",
            "file_type":ext,"text":combined[:60000], "previews":previews,
            "warnings":warnings, "processed_pages":len(previews)}
