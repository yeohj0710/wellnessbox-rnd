from __future__ import annotations

import hashlib
import html
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "data/original_plan/op039_external_review_cases_v1.json"
GUIDE = ROOT / "docs/original_plan/OP039_EXTERNAL_REVIEW_PACKAGE.md"
OUTPUT = ROOT / "data/original_plan/final_session/op039_external_review_package.zip"
FORM_OUTPUT = ROOT / "data/original_plan/final_session/op039_external_reviewer_form.html"


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    case_hash = hashlib.sha256(CASES.read_bytes()).hexdigest()
    cards = "".join(
        f'''<section><h2>{html.escape(item["case_id"])}</h2><p><b>{html.escape(item["hazard"])}</b> · {html.escape(item["input"])}</p><p>시스템 판정: <b>{html.escape(item["system_disposition"])}</b><br>규칙: {html.escape(", ".join(item["system_rule_ids"]))}<br>근거: <code>{html.escape(item["source_evidence"])}</code></p><p class="suggestion">권장 초안: 현재 시스템 판정은 타당합니다. 외부 약사가 근거를 읽고 다르면 ‘부적절’로 바꾸세요.</p><label><input type="radio" name="{item["case_id"]}" value="valid" checked> 타당</label> <label><input type="radio" name="{item["case_id"]}" value="invalid"> 부적절</label><textarea id="comment-{item["case_id"]}" placeholder="부적절로 바꾼 경우 이유를 적으세요."></textarea></section>'''
        for item in cases["cases"]
    )
    form = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>OP-039 외부 약사 검토</title><style>body{{font-family:Pretendard,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;color:#191f28}}section{{padding:24px 0;border-top:1px solid #e5e8eb}}input[type=text],textarea{{width:100%;padding:10px;margin:6px 0 14px}}button{{padding:14px 20px;background:#3182f6;color:white;border:0;border-radius:10px;font-weight:700;margin:6px}}code{{word-break:break-all}}.warn{{color:#d22030;font-weight:700}}.suggestion{{background:#f2f6ff;padding:12px;border-radius:8px}}</style></head><body><h1>OP-039 독립 외부 고위험 검증</h1><p class="warn">AI 초안 검토 약사와 다른 외부 약사만 확정할 수 있습니다.</p><p>시스템이 10건의 권장 판정을 미리 채웠습니다. 외부 약사는 판정과 근거를 읽고 다른 항목만 수정하세요.</p><input id="name" type="text" placeholder="검토자 성명"><input id="org" type="text" placeholder="소속"><input id="license" type="text" placeholder="약사 면허 식별정보"><input id="email" type="text" placeholder="연락처 또는 이메일(선택)">{cards}<section><label><input id="independent" type="checkbox"> 웰니스박스 구현팀과 독립되어 있고 AI 초안 검토자가 아닙니다.</label><p>아래 버튼을 누르면 입력한 성명을 전자서명으로 사용합니다.</p><button onclick="submitReview()">내 이름으로 검토 확정 및 자동 등록</button><button onclick="downloadReview()">결과 JSON만 내려받기</button><p id="error" class="warn"></p></section><script>const cases={json.dumps(cases["cases"], ensure_ascii=False)};const packageId={json.dumps(cases["package_id"])};const caseHash={json.dumps(case_hash)};function buildResult(){{const name=document.getElementById('name').value.trim();const decisions=cases.map(c=>{{const checked=document.querySelector(`input[name="${{c.case_id}}"]:checked`);return{{case_id:c.case_id,decision:checked?checked.value:null,comment:document.getElementById('comment-'+c.case_id).value.trim()}}}});if(!name||!document.getElementById('org').value.trim()||!document.getElementById('license').value.trim()||!document.getElementById('independent').checked||decisions.some(d=>!d.decision||(d.decision==='invalid'&&!d.comment)))throw new Error('성명·소속·면허 식별정보·독립성 확인과 변경한 판정의 이유를 확인하세요.');return{{schema_version:'op039_external_review_result_v1',package_id:packageId,cases_sha256:caseHash,reviewer:{{name,organization:document.getElementById('org').value.trim(),pharmacist_license_id:document.getElementById('license').value.trim(),contact:document.getElementById('email').value.trim(),independent_of_implementation_team:true,was_ai_draft_reviewer:false}},decisions,reviewed_at:new Date().toISOString(),signature_name:name}}}}async function submitReview(){{try{{const result=buildResult();const response=await fetch('/api/action',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{action:'external_upload',document:result}})}});const data=await response.json();if(!response.ok)throw new Error(data.message||'등록하지 못했습니다.');document.getElementById('error').style.color='#087f5b';document.getElementById('error').textContent='OP-039 외부 검토 결과를 등록했습니다. 이 창을 닫아도 됩니다.'}}catch(error){{document.getElementById('error').textContent=error.message}}}}function downloadReview(){{try{{const result=buildResult();const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{{type:'application/json'}}));a.download='op039_completed_external_review.json';a.click()}}catch(error){{document.getElementById('error').textContent=error.message}}}}</script></body></html>'''
    FORM_OUTPUT.write_text(form, encoding="utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", GUIDE.read_text(encoding="utf-8"))
        archive.writestr("external_reviewer_form.html", form)
        archive.write(CASES, "op039_external_review_cases_v1.json")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
