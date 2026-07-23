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
</style></head><body><h1>최종 연구 세션</h1><p class="intro">시스템이 준비한 결과를 읽고 확인만 누르세요. 외부 기관이나 운영 배포가 필요한 일은 사용자가 파일 경로를 찾지 않아도 됩니다.</p><div id="nextAction"></div><div id="steps"></div><section><h2>마지막 감사</h2><p class="help">모든 실제 증거가 준비되면 시스템이 산출물을 고정하고 최종 감사 결과를 표시합니다. 확인에는 약 30초가 걸릴 수 있습니다.</p><button id="auditButton" onclick="act('audit',{})">현재 완료 상태 확인</button><pre id="result" aria-live="polite">아직 실행하지 않았습니다.</pre></section><script>
let state={},activeDraft=null,generatedKeyPath='',draftReviewerId='';
const defaultActor='웰니스박스';
const labels={"H-001":"정렬 감사 확인","H-002":"정책 규칙 승인","H-003":"AI 초안 검토","H-004":"보고서 문체 확인","H-005":"외부 검증 등록","H-006":"Ed25519 영수증","H-007":"운영 환경 확인"};
const statusLabel={pending:'대기',completed:'완료',deferred:'보류'};
const operationLabels={rnd_api:'R&D API 배포',wellnessbox_environment:'WellnessBox 환경변수',health_check:'health 응답',browser_roundtrip:'브라우저 왕복'};
const $=id=>document.getElementById(id);const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(action,payload){$('result').textContent=action==='audit'?'완료 상태를 확인하고 있습니다. 약 30초만 기다려 주세요.':'처리하고 있습니다. 잠시만 기다려 주세요.';const response=await fetch('/api/action',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,...payload})});const data=await response.json();$('result').textContent=JSON.stringify(data,null,2);if(!response.ok)throw new Error(data.message||'요청을 처리하지 못했습니다.');return data}
async function act(action,payload){const auditButton=$('auditButton');if(action==='audit'){auditButton.disabled=true;auditButton.textContent='완료 상태 확인 중…'}try{await api(action,payload);await load()}catch(error){$('result').textContent=error.message;console.error(error)}finally{if(action==='audit'){auditButton.disabled=false;auditButton.textContent='현재 완료 상태 확인'}}}
async function load(){state=await(await fetch('/api/state')).json();const waiting=[];if(state.steps['H-005'].status!=='completed')waiting.push('외부 검증 기관의 OP-039 결과');if(state.steps['H-007'].status!=='completed')waiting.push('실제 운영 배포 증거');$('nextAction').innerHTML=waiting.length?`<section class="draft"><h2>지금 할 일</h2><p><strong>사용자가 준비할 파일이나 경로는 없습니다.</strong></p><p>${waiting.join(' 및 ')}가 아직 필요합니다. 아래 단계에서는 현재 상태만 확인하세요.</p></section>`:`<section class="draft"><h2>지금 할 일</h2><p>모든 증거가 준비됐습니다. 마지막 감사를 실행하세요.</p></section>`;$('steps').innerHTML=`<p class="progress"><strong>${state.progress.completed}/${state.progress.total}단계 완료</strong></p>`+Object.entries(state.steps).map(([id,value])=>`<section class="${value.status==='completed'?'done':''}"><h2>${id} ${labels[id]}</h2><p class="status">${statusLabel[value.status]}</p>${controls(id)}</section>`).join('')}
function controls(id){
 if(state.steps[id].status==='completed')return `<p class="help">처리 완료. 다시 누를 버튼이 없습니다.</p>`;
 if(id==='H-001')return `<p class="help">정렬 감사의 중대 어긋남 4건은 명시적 상태기계와 130개 평가 사례로 처리했습니다.</p><button onclick="act('alignment',{reviewer_id:defaultActor})">웰니스박스로 확인</button>`;
 if(id==='H-002')return `<p class="help">아래 정책 규칙 9개를 확인한 뒤 한 번만 누르세요.</p>${state.policy_rules.map(rule=>`<div class="rule"><strong>${rule.rule_id}</strong> ${esc(rule.plain_language)}</div>`).join('')}<button onclick="act('policy_all',{reviewer_id:defaultActor})">정책 전체 확인</button><details><summary>규칙 수정 의견 남기기</summary><select id="rule">${state.policy_rules.map(rule=>`<option>${rule.rule_id}</option>`).join('')}</select><textarea id="proposal" placeholder="수정 의견"></textarea><button class="secondary" onclick="reviewRule('change_requested')">수정 의견 저장</button></details>`;
 if(id==='H-003')return `<p class="help">내부 검토 원장은 자동으로 연결했습니다. 검토 시작을 누르면 첫 대기 건이 열립니다.</p><input id="draftDb" type="hidden" value="${esc(state.draft_database_path)}"><input id="draftReviewer" type="hidden" value="${defaultActor}"><button onclick="loadDraftQueue()">웰니스박스로 검토 시작</button><div id="draftCard" class="draft">검토 시작을 누르면 첫 대기 건을 표시합니다.</div>`;
 if(id==='H-004')return `<p class="help">이번 세션에서 무작위로 고른 세 편입니다.</p>${state.report_samples.map(report=>`<details><summary>${report.report_id} 읽기</summary><pre>${esc(report.excerpt)}</pre></details>`).join('')}<textarea id="toneComment" placeholder="문체 의견"></textarea><div class="row"><button onclick="tone(true)">웰니스박스로 문체 확인</button><button class="secondary" onclick="tone(false)">의견 저장 후 보류</button></div>`;
 if(id==='H-005'){const deferred=state.steps[id].status==='deferred';return `<p><strong>외부 검증 기관의 결과가 아직 없습니다.</strong> 지금 사용자가 준비하거나 선택할 파일은 없습니다.</p><p class="help">${deferred?'대기 상태 확인 완료. 더 누를 버튼이 없습니다.':'아래 버튼으로 현재 상태만 확인하세요.'}</p><button style="${deferred?'display:none':''}" onclick="act('external_upload',{document:null})">외부 결과 대기 상태 확인</button><details><summary>외부 결과를 이미 받은 경우</summary><p class="help">결과 JSON만 선택하세요. 저장 위치와 검증은 시스템이 처리합니다.</p><div class="row"><input id="externalFile" type="file" accept="application/json,.json"><button onclick="uploadExternal()">결과 확인 및 등록</button></div></details>`}
 if(id==='H-006'){const saved=state.steps['H-006'];return `<p class="help">서명 키 경로와 발급자는 자동으로 설정했습니다.</p><input id="keyPath" type="hidden" value="${esc(generatedKeyPath||saved.key_path||state.default_signing_key_path)}"><input id="issuer" type="hidden" value="${defaultActor}"><button onclick="prepareAndSignReceipts()">키 준비 및 영수증 2종 서명</button>`}
 return operationControls();
}
function reviewRule(decision){act('policy',{reviewer_id:defaultActor,rule_id:$('rule').value,decision,comment:$('proposal').value})}
function tone(approved){act('tone',{owner_id:defaultActor,approved,comment:$('toneComment').value})}
async function readJsonFile(file){if(!file)throw new Error('JSON 파일을 선택해 주세요.');return JSON.parse(await file.text())}
async function uploadExternal(){try{const document=await readJsonFile($('externalFile').files[0]);await api('external_upload',{document});await load()}catch(error){$('result').textContent=error.message;console.error(error)}}
function riskLines(value,path=''){let found=[];if(value&&typeof value==='object')for(const [key,item] of Object.entries(value)){const next=path?`${path}.${key}`:key;if(/contra|interaction|emergency|risk|adverse|금기|상호작용|응급|위험/i.test(key))found.push(`${next}: ${JSON.stringify(item)}`);found=found.concat(riskLines(item,next))}return found}
function renderDraft(draft){activeDraft=draft;const target=$('draftCard');if(!draft){target.innerHTML='<strong>대기 초안이 없습니다.</strong><p>0건 검토와 하류 차단 경계를 기록하려면 아래 버튼을 누르세요.</p><button onclick="confirmEmptyDraftQueue()">검토 대상 없음 확인</button>';return}const risks=riskLines({...draft.content,...draft.rationale});target.innerHTML=`<h3>${esc(draft.draft_id)} · ${esc(draft.record_type)}</h3>${risks.length?`<p class="risk">${risks.map(esc).join('<br>')}</p>`:''}<h4>초안</h4><pre>${esc(JSON.stringify(draft.content,null,2))}</pre><h4>판단 근거</h4><pre>${esc(JSON.stringify(draft.rationale,null,2))}</pre><textarea id="edited" aria-label="수정한 초안 JSON">${esc(JSON.stringify(draft.content,null,2))}</textarea><input id="rejectReason" placeholder="반려 사유"><div class="row"><button onclick="decideDraft('approved')">승인</button><button onclick="decideDraft('approved_with_edits')">수정 승인</button><button class="secondary" onclick="decideDraft('rejected')">반려</button></div>`}
async function loadDraftQueue(){try{draftReviewerId=$('draftReviewer').value;const data=await api('draft_queue',{database_path:$('draftDb').value});renderDraft(data.items[0]||null)}catch(error){console.error(error)}}
function confirmEmptyDraftQueue(){act('draft_empty',{database_path:$('draftDb').value,reviewer_id:defaultActor})}
async function decideDraft(decision){if(!activeDraft)return;draftReviewerId=$('draftReviewer').value||draftReviewerId;const payload={database_path:$('draftDb').value,draft_id:activeDraft.draft_id,reviewer_id:draftReviewerId,decision};if(decision==='approved_with_edits')payload.edited_content=JSON.parse($('edited').value);if(decision==='rejected')payload.rejection_reason=$('rejectReason').value;try{const data=await api('draft_decision',payload);await load();$('draftReviewer').value=draftReviewerId;renderDraft(data.next_draft)}catch(error){console.error(error)}}
async function generateKey(){try{const data=await api('key',{key_path:$('keyPath').value});generatedKeyPath=data.key_path;$('keyPath').value=data.key_path}catch(error){console.error(error)}}
function signReceipts(){act('receipts',{key_path:$('keyPath').value,issuer_id:$('issuer').value})}
async function prepareAndSignReceipts(){try{await api('receipts_prepare',{key_path:$('keyPath').value,issuer_id:defaultActor});await load()}catch(error){console.error(error)}}
function operationControls(){const saved=state.steps['H-007'];const registered=saved.registered_requirement_evidence||{};const deferred=saved.status==='deferred';return `<p><strong>실제 운영 배포가 아직 끝나지 않았습니다.</strong> 지금 사용자가 준비하거나 선택할 파일은 없습니다.</p><p>${Object.keys(registered).length}/${state.stage_gap_ids.length}개 운영 요구 증거 등록됨</p><p class="help">${deferred?'대기 상태 확인 완료. 더 누를 버튼이 없습니다.':'아래 버튼으로 현재 상태만 확인하세요.'}</p><button style="${deferred?'display:none':''}" onclick="act('operations_upload',{operator_id:defaultActor,documents:[]})">운영 증거 대기 상태 확인</button><details><summary>운영 증거 묶음을 이미 받은 경우</summary><p class="help">JSON 파일을 모두 선택하세요. 분류·저장·검증은 시스템이 처리합니다.</p><input id="operationFiles" type="file" accept="application/json,.json" multiple><button onclick="uploadOperations()">운영 증거 자동 분류 및 확인</button></details>`}
async function uploadOperations(){try{const documents=[];for(const file of $('operationFiles').files)documents.push(await readJsonFile(file));await api('operations_upload',{operator_id:defaultActor,documents});await load()}catch(error){$('result').textContent=error.message;console.error(error)}}
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
                    "policy_all": console.approve_all_policy_rules,
                    "draft_queue": console.draft_queue,
                    "draft_empty": console.confirm_empty_draft_queue,
                    "draft_decision": console.decide_draft,
                    "tone": console.record_report_tone,
                    "external": console.register_external_validation,
                    "external_upload": console.register_external_validation_upload,
                    "key": console.generate_key,
                    "receipts": console.sign_receipts,
                    "receipts_prepare": console.prepare_and_sign_receipts,
                    "operations": console.record_operations,
                    "operations_upload": console.record_uploaded_operations,
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
