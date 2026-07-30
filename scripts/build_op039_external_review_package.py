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

STYLE = (
    "body{font-family:Pretendard,sans-serif;max-width:900px;margin:40px auto;"
    "padding:0 20px;color:#191f28}"
    "section{padding:24px 0;border-top:1px solid #e5e8eb}"
    "label.field{display:block;font-weight:700;margin-top:12px}"
    "input[type=text],textarea{box-sizing:border-box;width:100%;padding:10px;margin:6px 0 14px}"
    "button{padding:14px 20px;background:#3182f6;color:white;border:0;border-radius:10px;"
    "font-weight:700}"
    ".warn{color:#d22030;font-weight:700}"
    ".readonly{padding:10px 12px;background:#f2f4f6;color:#4e5968;border-radius:8px}"
)

NEUTRALITY_NOTICE = (
    "이 화면은 어떤 판정도 미리 고르지 않습니다. 의견란, 면허 번호, 자격 확인 방법, "
    "서명도 비어 있습니다. 기존 오너 판정과 과거 검토 결과는 이 화면에 복사되지 않았습니다. "
    "10건의 판정과 근거는 검토 약사가 직접 입력해야 등록됩니다."
)


def _case_card(item: dict[str, object]) -> str:
    case_id = html.escape(str(item["case_id"]))
    hazard = html.escape(str(item["hazard"]))
    case_input = html.escape(str(item["input"]))
    disposition = html.escape(str(item["system_disposition"]))
    rules = html.escape(", ".join(str(rule) for rule in item["system_rule_ids"]))
    evidence = html.escape(str(item["source_evidence"]))
    return (
        f"<section><h2>{case_id}</h2>"
        f"<p><b>{hazard}</b> · {case_input}</p>"
        f'<p class="readonly">아래는 시스템이 낸 신호이며 검토 결론이 아닙니다.<br>'
        f"시스템 판정: <b>{disposition}</b><br>규칙: {rules}<br>"
        f"근거: <code>{evidence}</code></p>"
        f'<label><input type="radio" name="{case_id}" value="valid"> 타당</label> '
        f'<label><input type="radio" name="{case_id}" value="invalid"> 부적절</label>'
        f'<textarea id="comment-{case_id}" '
        f'placeholder="판정 근거 또는 부적절 사유를 직접 적으세요."></textarea>'
        f"</section>"
    )


def _script(cases: dict[str, object], case_hash: str) -> str:
    case_json = json.dumps(cases["cases"], ensure_ascii=False)
    package_json = json.dumps(cases["package_id"])
    hash_json = json.dumps(case_hash)
    return (
        "<script>"
        f"const cases={case_json};"
        f"const packageId={package_json};"
        f"const caseHash={hash_json};"
        "function value(id){return document.getElementById(id).value.trim()}"
        "function buildResult(){"
        "const name=value('name'),organization=value('org'),license=value('license'),"
        "credential=value('credential'),contact=value('contact'),signature=value('signature');"
        "const draftReviewer=document.getElementById('draftReviewer').checked;"
        "const decisions=cases.map(c=>{"
        "const checked=document.querySelector(`input[name=\"${c.case_id}\"]:checked`);"
        "return{case_id:c.case_id,decision:checked?checked.value:null,"
        "comment:document.getElementById('comment-'+c.case_id).value.trim()}});"
        "if(!name||!organization)throw new Error('검토자 성명과 소속을 입력하세요.');"
        "if(!license)throw new Error('실제 약사 면허 번호를 입력하세요.');"
        "if(!credential)throw new Error('자격을 어떻게 확인했는지 입력하세요.');"
        "if(decisions.some(d=>!d.decision))"
        "throw new Error('10건의 판정을 모두 직접 선택해야 합니다.');"
        "if(decisions.some(d=>!d.comment))"
        "throw new Error('10건의 판정 근거를 모두 직접 적어야 합니다.');"
        "if(!signature)throw new Error('제출 직전에 서명란에 본인 이름을 입력하세요.');"
        "if(signature!==name)throw new Error('서명은 검토자 성명과 같아야 합니다.');"
        "return{schema_version:'op039_external_review_result_v1',package_id:packageId,"
        "cases_sha256:caseHash,reviewer:{name,organization,pharmacist_license_id:license,"
        "credential_verification_method:credential,contact,"
        "reviewer_role:'project_pharmacist',"
        "relationship_to_project:'project_co_researcher',implemented_system:false,"
        "independent_of_implementation_team:false,was_ai_draft_reviewer:draftReviewer},"
        "prefilled_by_system:false,decisions,reviewed_at:new Date().toISOString(),"
        "signature_name:signature}}"
        "async function submitReview(){try{const result=buildResult();"
        "const response=await fetch('/api/action',{method:'POST',"
        "headers:{'content-type':'application/json'},"
        "body:JSON.stringify({action:'external_upload',document:result})});"
        "const data=await response.json();"
        "if(!response.ok)throw new Error(data.message||'등록하지 못했습니다.');"
        "document.getElementById('error').style.color='#087f5b';"
        "document.getElementById('error').textContent='전문가 안전 검토 결과를 등록했습니다.'}"
        "catch(error){document.getElementById('error').textContent=error.message}}"
        "</script>"
    )


def build_form(cases: dict[str, object], case_hash: str) -> str:
    cards = "".join(_case_card(item) for item in cases["cases"])
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        "<title>OP-039 프로젝트 소속 약사 전문가 검토</title>"
        f"<style>{STYLE}</style></head><body>"
        "<h1>OP-039 프로젝트 소속 약사 전문가 안전 검토</h1>"
        f'<p class="warn">{NEUTRALITY_NOTICE}</p>'
        '<label class="field">검토자 성명</label><input id="name" type="text">'
        '<label class="field">소속</label><input id="org" type="text">'
        '<label class="field">약사 면허 번호</label><input id="license" type="text">'
        '<label class="field">자격 확인 방법</label><input id="credential" type="text">'
        '<label class="field">연락처</label><input id="contact" type="text">'
        f"{cards}"
        "<section>"
        "<p>검토자는 과제 공동연구원이므로 구현팀 독립 여부는 false로 기록됩니다.</p>"
        '<label><input id="draftReviewer" type="checkbox"> '
        "이 검토자가 H-003 AI 초안도 검토했습니다.</label>"
        '<label class="field">서명(제출 직전에 본인이 입력)</label>'
        '<input id="signature" type="text">'
        '<button onclick="submitReview()">검토 결과 제출</button>'
        '<p id="error" class="warn"></p>'
        "</section>"
        f"{_script(cases, case_hash)}"
        "</body></html>"
    )


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    case_hash = hashlib.sha256(CASES.read_bytes()).hexdigest()
    form = build_form(cases, case_hash)
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
