from public_rule_engine import evaluate_text

def check(text, intent="platform_awareness"):
    return evaluate_text(text,"artwork",{
        "product":"credit_card","campaign":"installment",
        "channel":"facebook","communication_intent":intent,
        "campaign_terms":"","document_context":"ฟีเจอร์บนแอป UCHOOSE 0% Outlet",
    })

def test_standalone_phrase():
    assert any(f["rule_id"]=="RL-DEMO-004" for f in check("ของมันต้องมี! ผ่อนชำระ 0%"))

def test_real_deck_caption():
    assert any(f["rule_id"]=="RL-DEMO-004" for f in check("ช้อปให้สุดแบบไม่สะดุดกับโปร ผ่อน 0% ทุกชิ้น ทั้งร้าน! สิทธิพิเศษสำหรับคนใจร้อน รับของไปก่อน"))

def test_platform_not_time_limited():
    ids={f["rule_id"] for f in check("ผ่อน 0% ทุกชิ้นทั้งร้าน ส่งฟรี ไม่มีขั้นต่ำ")}
    assert "TC-DEMO-002" not in ids and "AD-DEMO-004" not in ids and "AD-DEMO-005" not in ids

def test_campaign_0_percent():
    ids={f["rule_id"] for f in check("ผ่อน 0% ภายในโปรนี้",intent="campaign_promotion")}
    assert "TC-DEMO-002" in ids

def test_neutral_platform():
    assert "RL-DEMO-004" not in {f["rule_id"] for f in check("บริการฟีเจอร์ผ่อนชำระบนแอป")}
