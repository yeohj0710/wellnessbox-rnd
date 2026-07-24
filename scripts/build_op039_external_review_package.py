from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "data/original_plan/op039_external_review_cases_v1.json"
GUIDE = ROOT / "docs/original_plan/OP039_EXTERNAL_REVIEW_PACKAGE.md"
OUTPUT = ROOT / "data/original_plan/final_session/op039_external_review_package.zip"
FORM_OUTPUT = ROOT / "data/original_plan/final_session/op039_external_reviewer_form.html"


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    case_hash = hashlib.sha256(CASES.read_bytes()).hexdigest()
    cards = "".join(
        f'''<section><h2>{html.escape(item["case_id"])}</h2><p><b>{html.escape(item["hazard"])}</b> · {html.escape(item["input"])}</p><p>시스템 판정: <b>{html.escape(item["system_disposition"])}</b><br>규칙: {html.escape(", ".join(item["system_rule_ids"]))}<br>근거: <code>{html.escape(item["source_evidence"])}</code></p><p class="suggestion">AI 제안입니다. 약사가 판정과 근거를 수정하거나 그대로 제출할 수 있습니다.</p><label><input type="radio" name="{item["case_id"]}" value="valid" checked> 타당</label> <label><input type="radio" name="{item["case_id"]}" value="invalid"> 부적절</label><textarea id="comment-{item["case_id"]}" placeholder="판정 근거 또는 부적절 사유를 적으세요.">{html.escape(f'AI 제안: {item["system_disposition"]} 판정은 {", ".join(item["system_rule_ids"])} 규칙과 연결된 통합 증거에 부합하므로 타당으로 제안합니다. 최종 판단은 검토 약사가 확인합니다.')}</textarea></section>'''
        for item in cases["cases"]
    )
    form = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>OP-039 프로젝트 소속 약사 전문가 검토</title><style>body{{font-family:Pretendard,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;color:#191f28}}section{{padding:24px 0;border-top:1px solid #e5e8eb}}label.field{{display:block;font-weight:700;margin-top:12px}}input[type=text],textarea{{box-sizing:border-box;width:100%;padding:10px;margin:6px 0 14px}}button{{padding:14px 20px;background:#3182f6;color:white;border:0;border-radius:10px;font-weight:700}}.warn{{color:#d22030;font-weight:700}}.suggestion{{padding:10px 12px;background:#eef6ff;color:#1b64da;border-radius:8px}}</style></head><body><h1>OP-039 프로젝트 소속 약사 전문가 안전 검토</h1><p class="warn">기존 오너의 판정은 자기검토로만 보존되며 이 화면에 복사되지 않았습니다. 아래 선택과 근거는 시스템 판정·규칙·통합 증거를 바탕으로 새로 만든 AI 제안입니다. 권혁찬 약사가 수정하거나 그대로 제출해야 등록됩니다.</p><label class="field">검토자 성명</label><input id="name" type="text" value="권혁찬"><label class="field">소속</label><input id="org" type="text">{cards}<section><p>검토자는 과제 공동연구원이므로 구현팀 독립 여부는 false로 기록됩니다.</p><button onclick="submitReview()">검토 결과 제출</button><p id="error" class="warn"></p></section><script>const cases={json.dumps(cases["cases"], ensure_ascii=False)};const packageId={json.dumps(cases["package_id"])};const caseHash={json.dumps(case_hash)};function buildResult(){{const name=document.getElementById('name').value.trim(),organization=document.getElementById('org').value.trim();const decisions=cases.map(c=>{{const checked=document.querySelector(`input[name="${{c.case_id}}"]:checked`);return{{case_id:c.case_id,decision:checked?checked.value:null,comment:document.getElementById('comment-'+c.case_id).value.trim()}}}});if(name!=='권혁찬'||!organization||decisions.some(d=>!d.decision))throw new Error('권혁찬 약사가 이름·소속과 10개 판정을 확인해야 합니다.');return{{schema_version:'op039_external_review_result_v1',package_id:packageId,cases_sha256:caseHash,reviewer:{{name,organization,pharmacist_license_id:'not_collected',credential_verification_method:'project_owner_attestation',contact:'',reviewer_role:'project_pharmacist',relationship_to_project:'project_co_researcher',implemented_system:false,independent_of_implementation_team:false,was_ai_draft_reviewer:false}},ai_prefill:{{source:'system_disposition_rule_and_integration_evidence',editable:true,accepted_by_human_on_submit:true}},decisions,reviewed_at:new Date().toISOString(),signature_name:name}}}}async function submitReview(){{try{{const result=buildResult();const response=await fetch('/api/action',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{action:'external_upload',document:result}})}});const data=await response.json();if(!response.ok)throw new Error(data.message||'등록하지 못했습니다.');document.getElementById('error').style.color='#087f5b';document.getElementById('error').textContent='전문가 안전 검토 결과를 등록했습니다.'}}catch(error){{document.getElementById('error').textContent=error.message}}}}</script></body></html>'''
    form = form.replace(
        '<input id="org" type="text">',
        '<input id="org" type="text" value="웰니스박스 TIPS 과제 참여연구원">',
    )
    FORM_OUTPUT.write_text(form, encoding="utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", GUIDE.read_text(encoding="utf-8"))
        archive.writestr("project_pharmacist_reviewer_form.html", form)
        archive.write(CASES, "op039_external_review_cases_v1.json")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
