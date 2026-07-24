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
:root{--blue:#3182f6;--blue-dark:#1b64da;--text:#191f28;--strong:#333d4b;--muted:#6b7684;--nav:#4e5968;--soft:#f9fafb;--line:#e5e8eb;--white:#fff;--success:#00a46c;--danger:#d22030}
*{box-sizing:border-box}html{background:var(--soft)}body{font-family:"Toss Product Sans",Tossface,"Pretendard Variable",Pretendard,-apple-system,BlinkMacSystemFont,"Noto Sans KR","Segoe UI",sans-serif;max-width:860px;margin:0 auto;padding:64px 24px 156px;color:var(--text);line-height:1.5;letter-spacing:0}h1{font-size:40px;line-height:1.3;margin:0 0 12px;font-weight:800}h2{font-size:26px;line-height:1.4;margin:0 0 10px}h3{font-size:19px;margin:0 0 8px}.intro,.help{color:var(--muted)}.intro{font-size:18px;margin:0 0 36px}.shell{background:var(--white);border-radius:28px;padding:36px;box-shadow:0 10px 36px rgba(0,27,55,.06)}section{padding:30px 0}.status{font-weight:700}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0}input,select,textarea,button{font:inherit;border:1px solid #d1d6db;border-radius:12px;padding:12px 14px}input,textarea,select{min-width:220px;background:white}textarea{width:100%;min-height:90px}button{cursor:pointer;background:var(--blue);color:white;border-color:var(--blue);font-weight:700}button:hover{background:var(--blue-dark)}button:disabled{cursor:default;background:#e5e8eb;color:#8b95a1;border-color:#e5e8eb}button.secondary{background:white;color:var(--nav);border-color:#d1d6db}.draft{background:var(--soft);padding:22px;border-radius:18px;margin-top:14px}.risk{color:var(--danger);font-weight:700}.rule{padding:10px 0;border-bottom:1px solid var(--line)}pre{white-space:pre-wrap;word-break:break-word;background:var(--soft);padding:14px;border-radius:10px}.evidence-list{max-height:440px;overflow:auto;padding:12px;background:var(--soft);border-radius:12px}.evidence-row{display:grid;grid-template-columns:110px 1fr;gap:8px;align-items:center;margin:7px 0}.step-strip{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:28px 0 8px}.step-dot{height:7px;border-radius:999px;background:#e5e8eb}.step-dot.completed{background:var(--blue)}.step-dot.current{background:#8bbcff}.eyebrow{color:var(--blue);font-weight:700;font-size:15px;margin:0 0 6px}.current-card{background:var(--white);border:1px solid var(--line);border-radius:22px;padding:28px;margin-top:22px}.sequence{display:grid;gap:10px;margin:22px 0}.sequence-item{display:grid;grid-template-columns:34px 1fr;gap:12px;align-items:start;padding:16px;background:var(--soft);border-radius:14px}.sequence-number{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:#e8f3ff;color:var(--blue);font-weight:800}.sequence-item.completed .sequence-number{background:#e8f8f2;color:var(--success)}.sequence-item.current{outline:2px solid #b7d7ff;background:#f5f9ff}.sequence-item p{margin:2px 0;color:var(--muted)}.metric{font-size:17px;font-weight:700;margin:8px 0}.action-dock{position:fixed;left:0;right:0;bottom:0;z-index:20;background:rgba(255,255,255,.96);border-top:1px solid var(--line);backdrop-filter:blur(18px);padding:14px 24px calc(14px + env(safe-area-inset-bottom))}.action-inner{max-width:812px;margin:0 auto;display:grid;grid-template-columns:1fr minmax(260px,360px);gap:20px;align-items:center}.action-label{font-size:13px;color:var(--muted);margin:0 0 2px}.action-title{font-size:17px;font-weight:800;margin:0}.primary-action{width:100%;min-height:54px;border-radius:14px;font-size:17px}.result-box{margin-top:18px;padding:14px 16px;background:var(--soft);border-radius:12px;color:var(--muted);font-size:14px;max-height:160px;overflow:auto}.result-box:empty{display:none}.advanced{margin-top:22px;color:var(--muted)}
@media(max-width:640px){body{padding:36px 16px 162px}.shell{padding:24px 18px;border-radius:22px}h1{font-size:30px}.intro{font-size:16px;margin-bottom:26px}.grid{grid-template-columns:1fr}.evidence-row{grid-template-columns:1fr}input,select{width:100%}.current-card{padding:20px 16px}.action-dock{padding:12px 16px calc(12px + env(safe-area-inset-bottom))}.action-inner{grid-template-columns:1fr;gap:8px}.action-label{display:none}.action-title{font-size:14px}.primary-action{min-height:52px}.step-strip{gap:5px}}
</style></head><body><main class="shell"><p class="eyebrow">TIPS 연구 운영</p><h1>최종 연구 세션</h1><p class="intro">아래 설명을 읽고 화면 아래의 파란 버튼만 순서대로 누르세요. 버튼은 항상 같은 자리에 있습니다.</p><div id="stepStrip" class="step-strip" aria-label="전체 단계"></div><div id="nextAction"></div><div id="steps"></div><section id="finalAudit" style="display:none"><h2>마지막 감사</h2><p class="help">모든 실제 증거가 준비되면 완료 상태를 확인합니다. 약 30초가 걸릴 수 있습니다.</p></section><details class="advanced"><summary>처리 결과 자세히 보기</summary><pre id="result" class="result-box" aria-live="polite"></pre></details></main><aside class="action-dock" aria-live="polite"><div class="action-inner"><div><p class="action-label">지금 할 일</p><p id="dockTitle" class="action-title">화면을 준비하고 있습니다.</p></div><button id="primaryAction" class="primary-action" onclick="runPrimaryAction()" disabled>잠시만 기다려 주세요</button></div></aside><script>
let state={},activeDraft=null,generatedKeyPath='',draftReviewerId='',currentStepIndex=0,initialStepSelected=false,pharmacistReviewOpened=false;
const defaultActor='웰니스박스';
const stepIds=['H-001','H-002','H-003','H-004','H-005','H-006','H-007'];
const labels={"H-001":"정렬 감사 확인","H-002":"정책 규칙 승인","H-003":"AI 초안 검토","H-004":"보고서 문체 확인","H-005":"외부 검증 등록","H-006":"Ed25519 영수증","H-007":"운영 환경 확인"};
const statusLabel={pending:'대기',completed:'완료',deferred:'보류'};
const operationLabels={rnd_api:'로컬 R&D API',wellnessbox_environment:'로컬 WellnessBox',health_check:'health 응답',browser_roundtrip:'브라우저 왕복'};
const $=id=>document.getElementById(id);const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(action,payload){$('result').textContent=action==='audit'?'완료 상태를 확인하고 있습니다. 약 30초만 기다려 주세요.':'처리하고 있습니다. 잠시만 기다려 주세요.';const response=await fetch('/api/action',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,...payload})});const data=await response.json();$('result').textContent=JSON.stringify(data,null,2);if(!response.ok)throw new Error(data.message||'요청을 처리하지 못했습니다.');return data}
async function act(action,payload){const primary=$('primaryAction');primary.disabled=true;primary.textContent='저장하고 있습니다…';try{await api(action,payload);await load();return true}catch(error){$('result').textContent=error.message;console.error(error);syncActionDock();return false}}
function operationalProfilesComplete(){const wizard=state.operational_wizard;return wizard.completed_profiles.length>=wizard.profile_count}
function stepCompleted(id){return state.steps[id].status==='completed'&&(id!=='H-007'||operationalProfilesComplete())}
function renderStepStrip(){const id=stepIds[currentStepIndex];$('stepStrip').innerHTML=stepIds.map(step=>`<span class="step-dot ${stepCompleted(step)?'completed':''} ${step===id?'current':''}" title="${step} ${labels[step]}"></span>`).join('')}
async function load(){state=await(await fetch('/api/state')).json();const firstOpen=stepIds.findIndex(id=>!stepCompleted(id));if(!initialStepSelected||currentStepIndex>=stepIds.length||stepCompleted(stepIds[currentStepIndex])){currentStepIndex=firstOpen<0?stepIds.length:firstOpen;initialStepSelected=true}renderStepStrip();const id=stepIds[currentStepIndex];const completedCount=stepIds.filter(stepCompleted).length;if(!id){$('nextAction').innerHTML='<p class="metric">7개 확인 단계가 모두 끝났습니다.</p>';$('steps').innerHTML='';$('finalAudit').style.display='block';syncActionDock();return}$('finalAudit').style.display='none';const displayStatus=stepCompleted(id)?'completed':id==='H-007'?'deferred':state.steps[id].status;$('nextAction').innerHTML=`<p class="metric">${currentStepIndex+1}/7단계 · ${completedCount}/7단계 처리됨</p>`;$('steps').innerHTML=`<section class="current-card ${displayStatus==='completed'?'done':''}"><p class="eyebrow">${id} · ${statusLabel[displayStatus]}</p><h2>${labels[id]}</h2>${controls(id)}</section>`;syncActionDock()}
function dockAction(){const id=stepIds[currentStepIndex];if(!id)return{title:'모든 확인 단계가 끝났습니다.',label:'최종 감사 실행',run:()=>act('audit',{})};if(id==='H-007'){const wizard=state.operational_wizard;if(wizard.baseline.status!=='completed')return{title:`프로필 ${wizard.profile_index+1}: 복용 전 상태를 저장합니다.`,label:'복용 전 상태 저장',run:()=>act('operational_baseline',{})};if(wizard.followup.status!=='completed')return{title:`프로필 ${wizard.profile_index+1}: 2주 후 상태를 저장합니다.`,label:'후속평가 저장',run:()=>act('operational_followup',{})};if(wizard.pharmacist_review.status!=='completed'&&!pharmacistReviewOpened)return{title:'권혁찬 약사가 추천 초안을 확인합니다.',label:'약사 검토 화면 열기',run:()=>{window.open(state.operational_urls.pharmacist_review,'_blank','noopener');pharmacistReviewOpened=true;syncActionDock()}};if(wizard.pharmacist_review.status!=='completed')return{title:'약사 화면에서 승인한 뒤 이 버튼을 누르세요.',label:'약사 승인 완료 확인',run:()=>act('operational_pharmacist',{})};return{title:'이 프로필의 세 단계가 끝났습니다.',label:'다음 프로필로 이동',run:async()=>{await load()}}}if(id==='H-001')return{title:'연구계획 정렬 결과를 확인합니다.',label:'정렬 결과 확인',run:()=>act('alignment',{reviewer_id:defaultActor})};if(id==='H-002')return{title:'안전 정책 9개를 한 번에 확인합니다.',label:'정책 전체 확인',run:()=>act('policy_all',{reviewer_id:defaultActor})};if(id==='H-003')return{title:'약사 검토 대기 초안을 불러옵니다.',label:'대기 초안 보기',run:()=>loadDraftQueue()};if(id==='H-004')return{title:'보고서 문체 표본을 승인합니다.',label:'문체 확인',run:()=>tone(true)};if(id==='H-005')return{title:'권혁찬의 OP-039 검토 화면을 엽니다.',label:'약사 안전 검토 열기',run:()=>{location.href='/op039-review'}};return{title:'현재 코드 기준으로 영수증을 서명합니다.',label:'영수증 서명',run:()=>prepareAndSignReceipts()}}
function syncActionDock(){const action=dockAction();$('dockTitle').textContent=action.title;const button=$('primaryAction');button.textContent=action.label;button.disabled=false}
async function runPrimaryAction(){const action=dockAction();return action.run()}
function controls(id){
 if(stepCompleted(id))return `<p class="help">처리 완료. 다시 누를 버튼이 없습니다.</p>`;
 if(id==='H-001')return `<p class="help">정렬 감사의 중대 어긋남 4건은 명시적 상태기계와 130개 평가 사례로 처리했습니다. 아래 고정 버튼으로 확인하세요.</p>`;
 if(id==='H-002')return `<p class="help">아래 정책 규칙 9개를 읽고 화면 아래의 고정 버튼으로 한 번에 확인하세요.</p>${state.policy_rules.map(rule=>`<div class="rule"><strong>${rule.rule_id}</strong> ${esc(rule.plain_language)}</div>`).join('')}<details class="advanced"><summary>규칙 수정 의견 남기기</summary><select id="rule">${state.policy_rules.map(rule=>`<option>${rule.rule_id}</option>`).join('')}</select><textarea id="proposal" placeholder="수정 의견"></textarea><button class="secondary" onclick="reviewRule('change_requested')">수정 의견 저장</button></details>`;
 if(id==='H-003')return `<p class="help">검토자 본인의 이름을 확인하고 화면 아래의 고정 버튼으로 대기 초안을 불러오세요.</p><input id="draftDb" type="hidden" value="${esc(state.draft_database_path)}"><label>약사 검토자 <input id="draftReviewer" value="권혁찬"></label><div id="draftCard" class="draft">대기 초안을 불러오면 여기에 표시됩니다.</div>`;
 if(id==='H-004')return `<p class="help">이번 세션에서 무작위로 고른 세 편입니다. 내용을 읽고 화면 아래의 고정 버튼으로 확인하세요.</p>${state.report_samples.map(report=>`<details><summary>${report.report_id} 읽기</summary><pre>${esc(report.excerpt)}</pre></details>`).join('')}<textarea id="toneComment" placeholder="문체 의견이 있으면 적으세요."></textarea>`;
 if(id==='H-005'){const deferred=state.steps[id].status==='deferred';return `<p class="risk">프로젝트 소속 면허 약사 권혁찬이 10개 사례를 직접 판정하고 서명해야 합니다.</p><p class="help">오너의 기존 판정은 복사되지 않으며 권혁찬은 과제 공동연구원이므로 independent=false로 기록됩니다.</p><details class="advanced"><summary>오프라인 검토가 필요할 때</summary><p><a href="${state.op039_package.download_path}" download>오프라인 패키지 내려받기</a></p><input id="externalFile" type="file" accept="application/json,.json"><button class="secondary" onclick="uploadExternal()">작성한 JSON 등록</button></details>${deferred?'<p class="help">실제 검토 전에는 보류 상태가 정상입니다.</p>':''}`}
 if(id==='H-006'){const saved=state.steps['H-006'];return `<p class="help">서명 키 경로와 발급자는 자동으로 설정했습니다. 화면 아래의 고정 버튼으로 영수증을 서명하세요.</p><input id="keyPath" type="hidden" value="${esc(generatedKeyPath||saved.key_path||state.default_signing_key_path)}"><input id="issuer" type="hidden" value="${defaultActor}">`}
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
function operationControls(){const coverage=state.operational_coverage;const wizard=state.operational_wizard;const p=wizard.prefill;const done=value=>value.status==='completed';const meds=p.medications.length?p.medications.join(', '):'없음';const current=!done(wizard.baseline)?0:!done(wizard.followup)?1:2;const item=(index,title,body,isDone)=>`<div class="sequence-item ${isDone?'completed':index===current?'current':''}"><span class="sequence-number">${isDone?'✓':index+1}</span><div><h3>${title}</h3><p>${body}</p></div></div>`;return `<p class="metric">프로필 ${wizard.profile_index+1}/${wizard.profile_count} · 완료 ${wizard.completed_profiles.length}/${wizard.profile_count}</p><p class="help">버튼을 찾을 필요가 없습니다. 아래 내용을 확인한 뒤 화면 맨 아래 파란 버튼만 누르세요.</p><div class="sequence">${item(0,'복용 전 상태',`${esc(p.participant_name)} · ${p.age}세 · 목표 ${esc(p.goal)} · 복용약물 ${esc(meds)} · ${esc(p.baseline)}`,done(wizard.baseline))}${item(1,'2주 후 상태',esc(p.followup),done(wizard.followup))}${item(2,'약사 검토','권혁찬 약사가 추천 초안을 확인하고 승인·수정 승인·반려 중 하나를 선택합니다.',done(wizard.pharmacist_review))}</div><p class="metric">누적 유효 세션 ${coverage.cumulative_session_count}회 · 완료 프로필 ${coverage.distinct_profile_count}/${coverage.target_distinct_profile_count}개</p><p class="help">사람이 실제로 저장한 기록만 누적합니다. 오너나 시스템 명의 판정은 약사 검토로 세지 않습니다.</p><details class="advanced"><summary>고급 기능</summary><p><a href="${state.operational_urls.user_session}" target="_blank">전체 사용자 화면 열기</a></p><button class="secondary" onclick="act('operations_collect',{operator_id:defaultActor})">운영 영수증 다시 확인</button></details>`}
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
            elif self.path == "/downloads/op039-external-review-package.zip":
                path = ROOT / "data/original_plan/final_session/op039_external_review_package.zip"
                raw = path.read_bytes()
                self.send_response(200)
                self.send_header("content-type", "application/zip")
                self.send_header("content-disposition", 'attachment; filename="op039-external-review-package.zip"')
                self.send_header("content-length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            elif self.path == "/op039-review":
                path = ROOT / "data/original_plan/final_session/op039_external_reviewer_form.html"
                self.reply(200, path.read_text(encoding="utf-8"), "text/html")
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
                    "operations_collect": console.collect_operational_receipts,
                    "operational_baseline": console.confirm_operational_baseline,
                    "operational_followup": console.confirm_operational_followup,
                    "operational_pharmacist": console.confirm_operational_pharmacist,
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
