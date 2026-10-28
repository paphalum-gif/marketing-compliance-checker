"""Public-demo compliance pre-screening heuristics.
This module intentionally does NOT contain confidential company policy or approved terms.
These checks are illustrative; official rule approval and product master are required.
"""
import re

VERSION="public-demo-rules-0.7"
FINANCIAL={"credit_card","personal_loan","nano_finance","digital_loan","installment"}
SOCIAL={"facebook","instagram","tiktok"}
PLATFORM_INTENTS={"platform_awareness","evergreen_benefit"}
VALID_INTENTS=PLATFORM_INTENTS|{"campaign_promotion","product_acquisition","unspecified"}

def context_type(context):
    """Prefer explicit user intent; otherwise infer from the whole creative, not a single OCR fragment."""
    intent=context.get("communication_intent","unspecified")
    if intent in VALID_INTENTS and intent!="unspecified":
        return intent
    combined=normalized(" ".join([
       context.get("document_context",""), context.get("artwork_text",""), context.get("caption","")
    ]))
    explicit_time=any(token in combined for token in (
        "ระหว่างวันที่","ตั้งแต่วันที่","หมดเขต","สิ้นสุดโปร","เฉพาะวันที่",
        "วันนี้เท่านั้น","ดีลจำกัดเวลา","limitedtime","endson","flashsale"
    ))
    platform_signals=sum(token in combined for token in (
        "ฟีเจอร์","แพลตฟอร์ม","บนแอป","ผ่านแอป","0%outlet",
        "platform","feature","ใช้บริการผ่าน","ใช้งานบนแอป","การใช้งาน"
    ))
    promotional_signals=sum(token in combined for token in (
        "รับเครดิตเงินคืน","สะสมยอดรับ","ลุ้นรางวัล","ลงทะเบียนรับสิทธิ์",
        "โปรเฉพาะ","โปรโมชันพิเศษ","promotionperiod","campaignperiod"
    ))
    if explicit_time or promotional_signals>=2:
        return "campaign_promotion"
    if platform_signals>=2 and promotional_signals==0:
        return "platform_awareness"
    return "unspecified"

def is_explicit_campaign(context):
    return context_type(context)=="campaign_promotion"

def clear_installment_claim(text):
    """Do not mistake the feature name '0% Outlet' for a 0% offer claim."""
    n=normalized(text)
    return bool(re.search(r"ผ่อน.{0,34}0%|0%.{0,18}ผ่อน|แบ่งชำระ.{0,20}0%|ดอกเบี้ย0%",n))

def timeline_in_text(text):
    return bool(re.search(r"(ระหว่างวันที่|ตั้งแต่วันที่|ถึงวันที่|หมดเขต|เฉพาะวันที่|เฉพาะช่วง|วันนี้เท่านั้น|limited.time|until\s+\d)",text,re.I))


def normalized(text):
    return re.sub(r"\s+","",(text or "").lower())

def pick(text,terms):
    n=normalized(text)
    for term in terms:
        if normalized(term) in n:
            return term
    return None

def evaluate_text(text,material,context):
    if not text.strip():
        return []
    product=context.get("product","other")
    campaign=context.get("campaign","other")
    channel=context.get("channel","other")
    brief=context.get("campaign_terms","")
    intent=context_type(context)
    is_platform=intent in PLATFORM_INTENTS
    campaign_mode=is_explicit_campaign(context)
    n=normalized(text)
    results=[]
    def emit(rule,principle,status,message,suggestion,evidence="",severity="medium",priority="must_fix",alternative=""):
        results.append({
          "rule_id":rule,"material":material,"evidence":evidence,"message":message,
          "suggestion":suggestion,"severity":severity,"status":status,"priority":priority,
          "principle":principle,"alternative_wording":alternative,
          "source":"Illustrative public demo guideline — not approved Compliance policy"
        })
    # These examples are linguistic pre-screen signals, not exhaustive prohibited phrase lists.
    # Only explicitly matched wording is reported as evidence. Screening is
    # independent of Platform Awareness vs Campaign Promotion.
    debt=pick(text,[
      "ของมันต้องมี อยากได้ต้องได้","ช็อปหนักแค่ไหนก็รวยเหมือนเดิม",
      "หรูก่อน ค่อยผ่อนทีหลัง","ไฮโซก่อน ค่อยผ่อนทีหลัง",
      "ไม่ต้องรอเก็บเงินครบ","ช้อปให้สุดแบบไม่สะดุด",
      "รับของไปก่อน","ของมันต้องมี"
    ])
    if debt and (product in FINANCIAL or clear_installment_claim(text) or "ผ่อน" in normalized(text)):
        emit("RL-DEMO-004","Responsible Lending / Avoid encouraging excessive debt","potential_issue",
          "⚠ พบถ้อยคำที่อาจเร่งให้ซื้อหรือใช้เครดิตก่อนพิจารณาความสามารถในการชำระ",
          "ทบทวนข้อความนี้โดยคำนึงถึงบริบทของการผ่อนชำระ หากต้องการสื่อสารฟีเจอร์ ให้เน้นรายละเอียดการใช้งานและการวางแผนชำระแทนการกระตุ้นให้รีบซื้อ แล้วส่งให้ Compliance พิจารณา",
          debt,"high",alternative="เลือกซื้อและแบ่งชำระตามเงื่อนไขที่กำหนด โดยคำนึงถึงความสามารถในการชำระคืน")
    approvals=pick(text,["ใครๆ ก็กู้ได้","ใคร ๆ ก็กู้ได้","ไม่เช็คเครดิตบูโร","ติดบูโรก็กู้ได้",
      "ไม่ตรวจเครดิต","อนุมัติ 100%","อนุมัติแน่นอน","guaranteed approval","100% approved","รับเงินสดได้ทันที"])
    if approvals:
        emit("RL-DEMO-005","Responsible lending / truthful advertising","potential_issue",
          "⚠ ห้ามใช้คำนี้โดยไม่มีข้อเท็จจริงและข้อกำหนดที่รองรับ: อาจทำให้เข้าใจว่าการอนุมัติเป็นเรื่องแน่นอน",
          "นำข้อความนี้ออกหรือปรับให้สอดคล้องกับขั้นตอนและเงื่อนไขพิจารณาสินเชื่อจริง พร้อมให้ Compliance ตรวจทาน",
          approvals,"high",alternative="การอนุมัติเป็นไปตามหลักเกณฑ์และเงื่อนไขของผู้ให้บริการ")
    superiority=pick(text,["ที่สุด","ดีที่สุด","ยอดเยี่ยม","ที่หนึ่ง","แห่งเดียว","เจ้าแรก","เห็นผล 100%"])
    if superiority:
        emit("AD-DEMO-002","Truthful and substantiated claims","needs_human_review",
          "คำกล่าวอ้างเชิงเปรียบเทียบหรือยืนยันผลต้องมีหลักฐานตรวจสอบได้",
          "ตรวจว่ามีข้อมูลหรือหลักฐานรองรับคำกล่าวอ้างนี้ก่อนเผยแพร่ หากไม่มีให้ปรับเป็นข้อเท็จจริงเฉพาะเจาะจง",
          superiority,"medium",alternative="แสดงคุณสมบัติหรือสิทธิประโยชน์ตามข้อเท็จจริงที่ตรวจสอบได้")
    unilateral=pick(text,["เปลี่ยนแปลงราคาและเงื่อนไขโดยไม่ต้องแจ้งให้ทราบล่วงหน้า",
      "ปัดเศษส่วนลดขึ้นโดยไม่ต้องแจ้งให้ทราบล่วงหน้า"])
    if unilateral:
        emit("AD-DEMO-003","Fair advertising conditions","potential_issue",
          "⚠ พบถ้อยคำสงวนสิทธิที่อาจไม่เป็นธรรมต่อผู้บริโภค",
          "หยุดใช้ข้อความนี้ในร่างโฆษณาและส่งให้ Legal/Compliance ตรวจถ้อยคำเงื่อนไขที่เหมาะสม",
          unilateral,"high")
    if product in FINANCIAL and campaign!="branding" and channel in SOCIAL:
        if not pick(text,["ใช้เท่าที่จำเป็น","กู้เท่าที่จำเป็น","ชำระคืนได้ตามกำหนด","ชำระคืนได้เต็มจำนวน"]):
            emit("RL-DEMO-002","Mandatory disclosure / channel separation","needs_human_review",
              "ยังตรวจไม่พบองค์ประกอบคำเตือนสินเชื่อในข้อความที่อ่านได้ของส่วนนี้",
              "ตรวจคำเตือนที่ต้องใช้ตามผลิตภัณฑ์และช่องทางกับ Rule Set ที่ผ่านการรับรอง โดย Artwork และ Caption ต้องประเมินแยกกัน; หากข้อความอยู่ในภาพเล็กมากให้ตรวจด้วยสายตา",
              "","medium")
    zero=clear_installment_claim(text)
    if zero and not brief.strip() and campaign_mode:
        emit("TC-DEMO-002","Limited-time campaign terms","needs_human_review",
          "พบข้อความผ่อน 0% ในแคมเปญที่มีระยะเวลา แต่ยังไม่มีข้อมูลเงื่อนไขที่ยืนยันแล้ว",
          "ตรวจและระบุระยะเวลาโปรโมชั่น รวมถึงสิทธิที่ร่วมรายการตาม Campaign Brief จริง",
          "0%","medium")
    # For platform/always-on or unspecified context, missing campaign dates
    # are NOT a finding. Absence of a Campaign Brief is not proof of a violation.
    if zero and campaign_mode and pick(text,["ทุกชิ้นทั้งร้าน","ทุกร้าน","ทุกสินค้า","ทุกชิ้น"]):
        broad=pick(text,["ทุกชิ้นทั้งร้าน","ทุกร้าน","ทุกสินค้า","ทุกชิ้น"])
        emit("AD-DEMO-004","Truthful feature or offer scope","needs_human_review",
          "ข้อความอาจทำให้เข้าใจว่าใช้สิทธิผ่อน 0% ได้กับสินค้าหรือร้านค้าทุกแห่ง",
          "ตรวจว่าฟีเจอร์หรือข้อเสนอครอบคลุมจริงตามคำกล่าวอ้างหรือไม่ หากมีร้านค้า สินค้า หรือบัตรที่ไม่ร่วมรายการ ให้ระบุข้อจำกัดตามจริง",
          broad,"medium")
    shipping=pick(text,["ส่งฟรี","จัดส่งฟรี","free shipping"])
    if shipping and not brief.strip() and campaign_mode:
        emit("PLATFORM-DEMO-005" if is_platform else "AD-DEMO-005",
          "Delivery benefit claim verification","needs_human_review",
          "มีคำกล่าวอ้างว่าจัดส่งฟรี ซึ่งต้องตรวจความถูกต้องของสิทธิการจัดส่ง",
          "ตรวจว่าการส่งฟรีใช้กับทุกคำสั่งซื้อจริงหรือไม่ มีขั้นต่ำ พื้นที่หรือสินค้ายกเว้นหรือไม่ หากเป็นสิทธิประจำของแพลตฟอร์ม ไม่ต้องใส่ช่วงเวลาแคมเปญ",
          shipping,"medium",priority="nice_to_improve" if is_platform else "must_fix")
    elif not shipping:
        free=pick(text,["ไม่มีค่าใช้จ่าย","free of charge","รับฟรี"])
        if free and not brief.strip() and campaign_mode:
            emit("AD-DEMO-005","No hidden fees / fair advertising","needs_human_review",
              "พบการกล่าวอ้างว่าไม่มีค่าใช้จ่าย ต้องตรวจว่าผู้ใช้ไม่ถูกเรียกเก็บค่าใช้จ่ายตามข้อความที่ระบุจริง",
              "ตรวจค่าใช้จ่ายและเงื่อนไขที่เกิดขึ้นจริง แล้วระบุข้อจำกัดที่มีผลต่อการตัดสินใจ โดยไม่เพิ่มข้อกำหนดเรื่องช่วงเวลาเมื่อไม่ใช่แคมเปญ",
              free,"medium")
    if campaign_mode and zero and not brief.strip() and not timeline_in_text(text):
        # Already included in TC-DEMO-002 as campaign-specific term guidance.
        pass
    gift=pick(text,["สมัครก็รับทันที","เพียงสมัครรับทันที","สมัครปุ๊บรับเลย"])
    if gift and product in FINANCIAL:
        emit("RL-DEMO-011","No pre-approval incentive","potential_issue",
          "⚠ ข้อความอาจสื่อว่าได้รับของแถมก่อนอนุมัติผลิตภัณฑ์เครดิต",
          "ตรวจเงื่อนไขการได้รับของแถมและลำดับการอนุมัติ อย่าสื่อว่าได้รับสิทธิทันทีเพียงสมัครหากยังต้องผ่านเกณฑ์อนุมัติ",
          gift,"high")
    if pick(text,["รับของแถม","ลุ้นรับ","ชิงโชค","ของสมนาคุณ"]) and not brief.strip():
        emit("PROMO-DEMO-001","Promotion transparency","needs_human_review",
          "ยังไม่มีข้อมูลหลักเกณฑ์ของแถม/รางวัลเพื่อตรวจความครบถ้วน",
          "เพิ่มหลักเกณฑ์รับสิทธิ ระยะเวลา ประเภทและมูลค่าของรางวัล วิธีและสถานที่รับสิทธิ และข้อจำกัดจาก Campaign Brief",
          "","medium")
    if pick(text,["รับประกันความพึงพอใจ","ไม่เห็นผลยินดีคืนเงิน"]) and not brief.strip():
        emit("AD-DEMO-007","Guarantee conditions","needs_human_review",
          "คำรับประกันยังไม่มีข้อมูลเงื่อนไขประกอบ",
          "ยืนยันผู้รับประกัน ระยะเวลา ขอบเขต วิธีการเรียกร้องสิทธิ และข้อยกเว้นก่อนใช้คำกล่าวอ้าง",
          "","medium")
    if campaign=="cashback" and pick(text,["เครดิตเงินคืน","cashback"]) and not brief.strip():
        emit("TC-DEMO-001","Cashback terms","needs_human_review",
          "ยังไม่มี Campaign Brief สำหรับตรวจเงื่อนไขเครดิตเงินคืน",
          "กรอกยอดใช้จ่ายขั้นต่ำ เพดานเครดิตเงินคืน ระยะเวลา คุณสมบัติผู้มีสิทธิ และรายการยกเว้นจากข้อมูลแคมเปญจริง",
          "","medium")
    if ("ลงทะเบียน" in text or "register" in n) and ("ก่อนทำรายการ" not in text) and not brief.strip():
        emit("PROMO-DEMO-002","Registration timing","needs_human_review",
          "ข้อความกล่าวถึงการลงทะเบียน แต่ยังไม่ทราบว่าต้องลงทะเบียนก่อนทำรายการหรือไม่",
          "ตรวจเงื่อนไข Campaign Brief ว่าต้องลงทะเบียนและได้รับการยืนยันก่อนทำรายการหรือไม่ หากใช่ให้ระบุขั้นตอนและเวลาที่ชัดเจน",
          "","medium")
    if "เงื่อนไขเป็นไปตามที่บริษัท" in n and not brief.strip():
        emit("AD-DEMO-008","Material terms visibility","needs_human_review",
          "มีข้อความอ้างเงื่อนไขทั่วไป แต่ยังไม่มีเงื่อนไขสำคัญให้ตรวจ",
          "เพิ่มข้อมูลสำคัญที่มีผลต่อการตัดสินใจ เช่น ผู้มีสิทธิ ระยะเวลาและข้อยกเว้น ไม่ใช้ประโยคสงวนสิทธิทั่วไปแทนสาระสำคัญ",
          "","medium")
    if re.search(r"\b\d{13}\b",text):
        emit("PRIVACY-DEMO-001","Privacy / data minimization","needs_human_review",
          "อาจมีเลขประจำตัวบุคคลในข้อความที่อัปโหลด",
          "หยุดใช้ไฟล์จริงใน Public Demo และลบ/ปิดข้อมูลส่วนบุคคลก่อนส่งตรวจ",
          "","high")
    return results

def evaluate_submission(req):
    findings=[]
    context=req.model_dump() if hasattr(req,"model_dump") else (req.dict() if hasattr(req,"dict") else req)
    for material, text in (("artwork",req.artwork_text),("caption",req.caption)):
        findings.extend(evaluate_text(text,material,context))
    total={"potential_issue":sum(f["status"]=="potential_issue" for f in findings),
           "needs_human_review":sum(f["status"]=="needs_human_review" for f in findings),
           "not_evaluated":sum(f["status"]=="not_evaluated" for f in findings)}
    risk="high" if any(f["severity"]=="high" for f in findings) else ("medium" if findings else "not_assessed")
    soft_notes=[]
    if context_type(context) in PLATFORM_INTENTS:
        whole=normalized(context.get("document_context","")+" "+context.get("artwork_text","")+" "+context.get("caption",""))
        if any(x in whole for x in ("ทุกชิ้นทั้งร้าน","ทุกร้าน","ทุกสินค้า")):
            soft_notes.append("ยืนยันกับทีมเจ้าของฟีเจอร์ว่าข้อความครอบคลุมทุกสินค้า/ร้านค้าตรงตามบริการจริง (ไม่ใช่ข้อผิดพลาดที่ตรวจพบ)")
        if "ส่งฟรี" in whole:
            soft_notes.append("ยืนยันกับทีมเจ้าของฟีเจอร์ว่าสิทธิส่งฟรีและข้อจำกัดตรงตามบริการจริง (ไม่ใช่ข้อผิดพลาดที่ตรวจพบ)")
    return {"mode":"DEMO ONLY — NOT APPROVAL","rule_version":VERSION,"risk_level":risk,
        "non_blocking_verifications":soft_notes,
        "counts":{"issues":total["potential_issue"],"needs_review":total["needs_human_review"],"not_evaluated":total["not_evaluated"]},
        "communication_context":{"intent":context_type(context),"is_time_limited_campaign":is_explicit_campaign(context),
            "reason":"ใช้วัตถุประสงค์การสื่อสารที่เลือกเพื่อระบุว่ากฎเรื่องช่วงเวลาแคมเปญมีผลหรือไม่"},
        "findings":findings,
        "summary_assessment":"เป็นการตรวจเบื้องต้นตามกฎตัวอย่าง ไม่สามารถยืนยันว่าโฆษณาผ่าน Compliance",
        "assumptions":["ตรวจตามประเภทผลิตภัณฑ์/วัตถุประสงค์การสื่อสาร/ช่องทางที่ผู้ใช้เลือก","OCR อาจไม่อ่านข้อความบนภาพได้ครบ"],
        "disclaimer":"This assessment is a preliminary compliance screening based on general principles and does not replace formal Compliance or Legal approval.",
        "coverage":{"ai":False,"policy_approved":False,"full_rule_catalog":False,"ocr":True}}
