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


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    case_hash = hashlib.sha256(CASES.read_bytes()).hexdigest()
    cards = "".join(
        f'''<section><h2>{html.escape(item["case_id"])}</h2><p><b>{html.escape(item["hazard"])}</b> · {html.escape(item["input"])}</p><p>시스템 판정: <b>{html.escape(item["system_disposition"])}</b><br>규칙: {html.escape(", ".join(item["system_rule_ids"]))}<br>근거: <code>{html.escape(item["source_evidence"])}</code></p><label><input type="radio" name="{item["case_id"]}" value="valid"> 타당</label> <label><input type="radio" name="{item["case_id"]}" value="invalid"> 부적절</label><textarea id="comment-{item["case_id"]}" placeholder="의견"></textarea></section>'''
        for item in cases["cases"]
    )
    form = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>OP-039 외부 약사 검토</title><style>body{{font-family:Pretendard,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;color:#191f28}}section{{padding:24px 0;border-top:1px solid #e5e8eb}}input[type=text],textarea{{width:100%;padding:10px;margin:6px 0 14px}}button{{padding:14px 20px;background:#3182f6;color:white;border:0;border-radius:10px;font-weight:700}}code{{word-break:break-all}}.warn{{color:#d22030;font-weight:700}}</style></head><body><h1>OP-039 독립 외부 고위험 검증</h1><p class="warn">AI 초안 검토 약사와 다른 외부 약사만 작성할 수 있습니다.</p><input id="name" type="text" placeholder="검토자 성명"><input id="org" type="text" placeholder="소속"><input id="license" type="text" placeholder="약사 면허 식별정보"><input id="email" type="text" placeholder="연락처 또는 이메일">{cards}<section><label><input id="independent" type="checkbox"> 웰니스박스 구현팀과 독립되어 있고 AI 초안 검토자가 아닙니다.</label><input id="signature" type="text" placeholder="서명: 검토자 성명을 다시 입력"><button onclick="download()">결과 JSON 내려받기</button><p id="error" class="warn"></p></section><script>const cases={json.dumps(cases["cases"], ensure_ascii=False)};const packageId={json.dumps(cases["package_id"])};const caseHash={json.dumps(case_hash)};function download(){{const name=document.getElementById('name').value.trim(),signature=document.getElementById('signature').value.trim();const decisions=cases.map(c=>{{const checked=document.querySelector(`input[name="${{c.case_id}}"]:checked`);return{{case_id:c.case_id,decision:checked?checked.value:null,comment:document.getElementById('comment-'+c.case_id).value.trim()}}}});if(!name||!document.getElementById('org').value.trim()||!document.getElementById('license').value.trim()||!document.getElementById('independent').checked||signature!==name||decisions.some(d=>!d.decision||(d.decision==='invalid'&&!d.comment))){{document.getElementById('error').textContent='검토자 정보, 독립성, 모든 사례 판정, 서명을 확인하세요.';return}}const result={{schema_version:'op039_external_review_result_v1',package_id:packageId,cases_sha256:caseHash,reviewer:{{name,organization:document.getElementById('org').value.trim(),pharmacist_license_id:document.getElementById('license').value.trim(),contact:document.getElementById('email').value.trim(),independent_of_implementation_team:true,was_ai_draft_reviewer:false}},decisions,reviewed_at:new Date().toISOString(),signature_name:signature}};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{{type:'application/json'}}));a.download='op039_completed_external_review.json';a.click()}}</script></body></html>'''
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", GUIDE.read_text(encoding="utf-8"))
        archive.writestr("external_reviewer_form.html", form)
        archive.write(CASES, "op039_external_review_cases_v1.json")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
