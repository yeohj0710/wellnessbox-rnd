# ruff: noqa: E402,E501,I001
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.governance.final_session_console import FinalSessionConsole, run_rehearsal


HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>최종 연구 세션</title><style>
:root{--blue:#3182f6;--text:#191f28;--muted:#6b7684;--soft:#f9fafb;--line:#e5e8eb}
*{box-sizing:border-box}body{font-family:Pretendard,-apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif;max-width:1049px;margin:0 auto;padding:72px 24px;color:var(--text);line-height:1.55}h1{font-size:42px;margin:0 0 12px}h2{font-size:26px;margin:0 0 8px}.intro,.help{color:var(--muted)}section{border-top:1px solid var(--line);padding:48px 0}.done h2{color:var(--blue)}.status{font-weight:700}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0}input,select,textarea,button{font:inherit;border:1px solid #d1d6db;border-radius:10px;padding:11px 13px}input,textarea,select{min-width:220px;background:white}textarea{width:100%;min-height:90px}button{cursor:pointer;background:var(--blue);color:white;border-color:var(--blue);font-weight:700}button.secondary{background:white;color:#4e5968;border-color:#d1d6db}.draft{background:var(--soft);padding:20px;border-radius:14px;margin-top:16px}.risk{color:#d22030;font-weight:700}.rule{padding:10px 0;border-bottom:1px solid var(--line)}pre{white-space:pre-wrap;word-break:break-word;background:var(--soft);padding:14px;border-radius:10px}.evidence-list{max-height:440px;overflow:auto;padding:12px;background:var(--soft);border-radius:12px}.evidence-row{display:grid;grid-template-columns:110px 1fr;gap:8px;align-items:center;margin:7px 0}.progress{position:sticky;top:0;background:rgba(255,255,255,.96);padding:12px 0;z-index:2}
@media(max-width:640px){body{padding:40px 20px}h1{font-size:30px}.grid{grid-template-columns:1fr}.evidence-row{grid-template-columns:1fr}input,select{width:100%}}
</style></head><body><h1>최종 연구 세션</h1><p class="intro">사람의 판단과 실제 운영 증거를 H-001부터 H-007까지 순서대로 기록합니다. 준비되지 않은 단계는 보류하고 나중에 이어갈 수 있습니다.</p><div id="steps"></div><section><h2>마지막 감사</h2><p class="help">완료된 단계의 실제 산출물을 Git에 고정한 뒤 최종 감사 결과를 표시합니다.</p><button onclick="act('audit',{})">최종 감사 실행</button><pre id="result">아직 실행하지 않았습니다.</pre></section><script>
let state={},activeDraft=null,generatedKeyPath='',draftReviewerId='';
const labels={"H-001":"정렬 감사 확인","H-002":"정책 규칙 승인","H-003":"AI 초안 검토","H-004":"보고서 문체 확인","H-005":"외부 검증 등록","H-006":"Ed25519 영수증","H-007":"운영 환경 확인"};
const statusLabel={pending:'대기',completed:'완료',deferred:'보류'};
const operationLabels={rnd_api:'R&D API 배포',wellnessbox_environment:'WellnessBox 환경변수',health_check:'health 응답',browser_roundtrip:'브라우저 왕복'};
const $=id=>document.getElementById(id);const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(action,payload){const response=await fetch('/api/action',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,...payload})});const data=await response.json();$('result').textContent=JSON.stringify(data,null,2);if(!response.ok)throw new Error(data.message||'요청을 처리하지 못했습니다.');return data}
async function act(action,payload){try{await api(action,payload);await load()}catch(error){console.error(error)}}
async function load(){state=await(await fetch('/api/state')).json();$('steps').innerHTML=`<p class="progress"><strong>${state.progress.completed}/${state.progress.total}단계 완료</strong></p>`+Object.entries(state.steps).map(([id,value])=>`<section class="${value.status==='completed'?'done':''}"><h2>${id} ${labels[id]}</h2><p class="status">${statusLabel[value.status]}</p>${controls(id)}</section>`).join('')}
function controls(id){
 if(id==='H-001')return `<p class="help">정렬 감사의 중대 어긋남 4건은 명시적 상태기계와 130개 평가 사례로 처리했습니다.</p><div class="row"><input id="owner" aria-label="확인자 ID" placeholder="확인자 ID"><button onclick="act('alignment',{reviewer_id:$('owner').value})">처리 방침 확인</button></div>`;
 if(id==='H-002')return `<p class="help">각 규칙을 읽고 승인하거나 바꿀 내용을 남겨 주세요.</p>${state.policy_rules.map(rule=>`<div class="rule"><strong>${rule.rule_id}</strong> ${esc(rule.plain_language)}</div>`).join('')}<div class="row"><input id="pharm" placeholder="약사 ID"><select id="rule">${state.policy_rules.map(rule=>`<option>${rule.rule_id}</option>`).join('')}</select><button onclick="reviewRule('approved')">이 규칙 승인</button></div><textarea id="proposal" placeholder="수정 의견"></textarea><button class="secondary" onclick="reviewRule('change_requested')">수정 의견 저장</button>`;
 if(id==='H-003')return `<p class="help">초안과 판단 근거를 읽고 한 번 클릭해 결정합니다. 결정 직후 다음 대기 건이 자동으로 열립니다.</p><div class="row"><input id="draftDb" value="${esc(state.draft_database_path)}" aria-label="AI 초안 SQLite 경로"><input id="draftReviewer" placeholder="약사 ID"><button onclick="loadDraftQueue()">검토 시작</button></div><div id="draftCard" class="draft">검토 시작을 누르면 첫 대기 건을 표시합니다.</div>`;
 if(id==='H-004')return `<p class="help">이번 세션에서 무작위로 고른 세 편입니다.</p>${state.report_samples.map(report=>`<details><summary>${report.report_id} 읽기</summary><pre>${esc(report.excerpt)}</pre></details>`).join('')}<input id="toneOwner" placeholder="오너 ID"><textarea id="toneComment" placeholder="문체 의견"></textarea><div class="row"><button onclick="tone(true)">보고서 문체 승인</button><button class="secondary" onclick="tone(false)">의견 저장 후 보류</button></div>`;
 if(id==='H-005')return `<p class="help">OP-039 신뢰 원장에 고정된 외부 평가 결과만 등록됩니다.</p><div class="row"><input id="external" placeholder="외부 평가 결과 JSON 경로"><button onclick="act('external',{source_path:$('external').value})">검증하고 등록</button><button class="secondary" onclick="act('external',{source_path:null})">나중에 등록</button></div>`;
 if(id==='H-006'){const saved=state.steps['H-006'];return `<p class="help">기존 Ed25519 키를 선택하거나 새 키를 만든 뒤 영수증 두 종류를 서명합니다.</p><div class="grid"><input id="keyPath" value="${esc(generatedKeyPath||saved.key_path||'')}" placeholder="Ed25519 키 파일 경로"><input id="issuer" value="${esc(saved.issuer_id||'')}" placeholder="발급자 ID"></div><div class="row"><button class="secondary" onclick="generateKey()">이 경로에 키 생성</button><button onclick="signReceipts()">영수증 2종 서명</button></div>`}
 return operationControls();
}
function reviewRule(decision){act('policy',{reviewer_id:$('pharm').value,rule_id:$('rule').value,decision,comment:$('proposal').value})}
function tone(approved){act('tone',{owner_id:$('toneOwner').value,approved,comment:$('toneComment').value})}
function riskLines(value,path=''){let found=[];if(value&&typeof value==='object')for(const [key,item] of Object.entries(value)){const next=path?`${path}.${key}`:key;if(/contra|interaction|emergency|risk|adverse|금기|상호작용|응급|위험/i.test(key))found.push(`${next}: ${JSON.stringify(item)}`);found=found.concat(riskLines(item,next))}return found}
function renderDraft(draft){activeDraft=draft;const target=$('draftCard');if(!draft){target.innerHTML='<strong>대기 초안을 모두 검토했습니다.</strong>';return}const risks=riskLines({...draft.content,...draft.rationale});target.innerHTML=`<h3>${esc(draft.draft_id)} · ${esc(draft.record_type)}</h3>${risks.length?`<p class="risk">${risks.map(esc).join('<br>')}</p>`:''}<h4>초안</h4><pre>${esc(JSON.stringify(draft.content,null,2))}</pre><h4>판단 근거</h4><pre>${esc(JSON.stringify(draft.rationale,null,2))}</pre><textarea id="edited" aria-label="수정한 초안 JSON">${esc(JSON.stringify(draft.content,null,2))}</textarea><input id="rejectReason" placeholder="반려 사유"><div class="row"><button onclick="decideDraft('approved')">승인</button><button onclick="decideDraft('approved_with_edits')">수정 승인</button><button class="secondary" onclick="decideDraft('rejected')">반려</button></div>`}
async function loadDraftQueue(){try{draftReviewerId=$('draftReviewer').value;const data=await api('draft_queue',{database_path:$('draftDb').value});renderDraft(data.items[0]||null)}catch(error){console.error(error)}}
async function decideDraft(decision){if(!activeDraft)return;draftReviewerId=$('draftReviewer').value||draftReviewerId;const payload={database_path:$('draftDb').value,draft_id:activeDraft.draft_id,reviewer_id:draftReviewerId,decision};if(decision==='approved_with_edits')payload.edited_content=JSON.parse($('edited').value);if(decision==='rejected')payload.rejection_reason=$('rejectReason').value;try{const data=await api('draft_decision',payload);await load();$('draftReviewer').value=draftReviewerId;renderDraft(data.next_draft)}catch(error){console.error(error)}}
async function generateKey(){try{const data=await api('key',{key_path:$('keyPath').value});generatedKeyPath=data.key_path;$('keyPath').value=data.key_path}catch(error){console.error(error)}}
function signReceipts(){act('receipts',{key_path:$('keyPath').value,issuer_id:$('issuer').value})}
function operationControls(){const saved=state.steps['H-007'];const checks=saved.checks||{};const registered=saved.registered_requirement_evidence||{};const environment=Object.entries(operationLabels).map(([key,label])=>{const item=checks[key]||{};return `<div class="evidence-row"><label><input type="checkbox" id="check-${key}" ${item.status==='PASS'?'checked':''}> ${label}</label><input id="evidence-${key}" value="${esc(item.evidence||'')}" placeholder="확인 증거 파일 경로"></div>`}).join('');const requirements=state.stage_gap_ids.map(id=>`<div class="evidence-row"><label><input type="checkbox" id="check-${id}" ${registered[id]?'checked':''}> ${id}</label><input id="evidence-${id}" value="${esc(registered[id]||'')}" placeholder="${id} PASS 증거 JSON 경로"></div>`).join('');return `<p class="help">체크한 항목의 증거 파일만 검증합니다. 단계 미달 요구는 각 요구 ID와 PASS 상태가 들어 있는 JSON이 필요합니다.</p><input id="operator" value="${esc(saved.operator_id||'')}" placeholder="운영 확인자 ID"><h3>운영 환경</h3>${environment}<details><summary>단계 미달 요구 ${state.stage_gap_ids.length}개 증거 입력</summary><div class="evidence-list">${requirements}</div></details><button onclick="saveOperations()">운영 증거 검증하고 저장</button>`}
function saveOperations(){const checks={};for(const key of Object.keys(operationLabels)){const evidence=$(`evidence-${key}`).value;if($(`check-${key}`).checked||evidence)checks[key]={status:$(`check-${key}`).checked?'PASS':'PENDING',evidence}}checks.requirement_evidence={};for(const id of state.stage_gap_ids)if($(`check-${id}`).checked)checks.requirement_evidence[id]=$(`evidence-${id}`).value;act('operations',{operator_id:$('operator').value,checks})}
load();</script></body></html>"""


def handler(console: FinalSessionConsole):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status: int, value: object, content_type: str = "application/json") -> None:
            raw = (
                value.encode()
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False).encode()
            )
            self.send_response(status)
            self.send_header("content-type", f"{content_type}; charset=utf-8")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            if self.path == "/":
                self.reply(200, HTML, "text/html")
            elif self.path == "/favicon.ico":
                self.reply(204, "", "image/x-icon")
            elif self.path == "/api/state":
                self.reply(200, console.view_state())
            else:
                self.reply(404, {"error": "not_found"})

        def do_POST(self) -> None:
            try:
                size = int(self.headers.get("content-length", "0"))
                body = json.loads(self.rfile.read(size))
                action = body.pop("action")
                actions = {
                    "alignment": console.confirm_alignment,
                    "policy": console.review_policy_rule,
                    "draft_queue": console.draft_queue,
                    "draft_decision": console.decide_draft,
                    "tone": console.record_report_tone,
                    "external": console.register_external_validation,
                    "key": console.generate_key,
                    "receipts": console.sign_receipts,
                    "operations": console.record_operations,
                    "audit": console.finalize_and_audit,
                }
                self.reply(200, actions[action](**body))
            except Exception as exc:
                self.reply(400, {"error": type(exc).__name__, "message": str(exc)})

        def log_message(self, *_: object) -> None:
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--state-root")
    args = parser.parse_args()
    if args.rehearsal:
        with tempfile.TemporaryDirectory(prefix="wellnessbox-final-session-") as temp:
            print(json.dumps(run_rehearsal(ROOT, Path(temp)), ensure_ascii=False))
            return 0
    console = FinalSessionConsole(
        ROOT, state_root=Path(args.state_root) if args.state_root else None
    )
    server = ThreadingHTTPServer((args.host, args.port), handler(console))
    url = f"http://{args.host}:{server.server_port}/"
    if not args.no_browser:
        webbrowser.open(url)
    print(url, flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
