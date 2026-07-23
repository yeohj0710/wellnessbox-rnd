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


HTML = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>최종 연구 세션</title><style>body{font-family:Pretendard,system-ui;max-width:920px;margin:40px auto;padding:0 20px;color:#191f28}button,input,textarea{font:inherit;padding:10px;margin:4px}section{border:1px solid #ddd;border-radius:16px;padding:20px;margin:16px 0}.done{border-color:#3182f6}pre{white-space:pre-wrap;background:#f2f4f6;padding:12px}</style></head><body><h1>최종 연구 세션</h1><p>H-001부터 H-007까지 실제 산출물에 기록합니다. 준비되지 않은 단계는 보류하고 다시 열어 이어갈 수 있습니다.</p><div id='steps'></div><section><h2>마지막 감사</h2><button onclick="act('audit',{})">최종 감사 실행</button><pre id='result'></pre></section><script>
let state={};const labels={"H-001":"정렬 감사 확인","H-002":"정책 규칙 승인","H-003":"AI 초안 검토 원장","H-004":"보고서 톤 확인","H-005":"외부 검증 등록","H-006":"Ed25519 영수증","H-007":"운영 환경 확인"};const statusLabel={pending:'대기',completed:'완료',deferred:'보류'};
async function act(action,payload){const r=await fetch('/api/action',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,...payload})});document.querySelector('#result').textContent=JSON.stringify(await r.json(),null,2);await load()}
async function load(){state=await(await fetch('/api/state')).json();document.querySelector('#steps').innerHTML=`<p><strong>${state.progress.completed}/${state.progress.total}단계 완료</strong></p>`+Object.entries(state.steps).map(([id,v])=>`<section class='${v.status==='completed'?'done':''}'><h2>${id} ${labels[id]}</h2><p>상태: ${statusLabel[v.status]}</p>${controls(id)}</section>`).join('')}
function controls(id){if(id==='H-001')return `<input id='owner' placeholder='확인자 ID'><button onclick="act('alignment',{reviewer_id:owner.value})">정렬 감사 확인</button>`;if(id==='H-002')return `<p>${state.policy_rules.map(r=>`${r.rule_id} · ${r.plain_language}`).join('<br>')}</p><input id='pharm' placeholder='약사 ID'><select id='rule'>${state.policy_rules.map(r=>`<option>${r.rule_id}</option>`).join('')}</select><button onclick="act('policy',{reviewer_id:pharm.value,rule_id:rule.value,decision:'approved'})">이 규칙 승인</button><textarea id='proposal' placeholder='바꿀 내용을 구체적으로 적어 주세요'></textarea><button onclick="act('policy',{reviewer_id:pharm.value,rule_id:rule.value,decision:'change_requested',comment:proposal.value})">수정 의견 저장</button>`;if(id==='H-003')return `<input id='draftDb' placeholder='AI 초안 SQLite 경로'><input id='draftId' placeholder='초안 ID'><input id='draftReviewer' placeholder='약사 ID'><button onclick="act('draft_queue',{database_path:draftDb.value})">대기 건 보기</button><button onclick="act('draft_decision',{database_path:draftDb.value,draft_id:draftId.value,reviewer_id:draftReviewer.value,decision:'approved'})">승인</button><textarea id='edited' placeholder='수정한 JSON'></textarea><button onclick="act('draft_decision',{database_path:draftDb.value,draft_id:draftId.value,reviewer_id:draftReviewer.value,decision:'approved_with_edits',edited_content:JSON.parse(edited.value)})">수정 승인</button><input id='rejectReason' placeholder='반려 사유'><button onclick="act('draft_decision',{database_path:draftDb.value,draft_id:draftId.value,reviewer_id:draftReviewer.value,decision:'rejected',rejection_reason:rejectReason.value})">반려</button>`;if(id==='H-004')return `${state.report_samples.map(r=>`<details><summary>${r.report_id} 읽기</summary><pre>${r.excerpt}</pre></details>`).join('')}<input id='toneOwner' placeholder='오너 ID'><textarea id='toneComment' placeholder='문체 의견'></textarea><button onclick="act('tone',{owner_id:toneOwner.value,approved:true,comment:toneComment.value})">보고서 문체 승인</button>`;if(id==='H-005')return `<input id='external' placeholder='OP-039 외부 평가 결과 JSON 경로'><button onclick="act('external',{source_path:external.value})">검증하고 등록</button><button onclick="act('external',{source_path:null})">나중에 등록</button>`;if(id==='H-006')return `<input id='keyPath' placeholder='Ed25519 키 파일 경로'><input id='issuer' placeholder='발급자 ID'><button onclick="act('key',{key_path:keyPath.value})">키 생성</button><button onclick="act('receipts',{key_path:keyPath.value,issuer_id:issuer.value})">영수증 2종 서명</button>`;return `<input id='operator' placeholder='운영 확인자 ID'><textarea id='checks' placeholder='각 항목에 status=PASS와 증거값을 넣은 JSON'></textarea><button onclick="act('operations',{operator_id:operator.value,checks:JSON.parse(checks.value)})">운영 증거 검증하고 저장</button>`}load();</script></body></html>"""


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
                    "drafts": lambda ledger_path, reviewer_id: console.record_draft_review_summary(
                        ledger_path, reviewer_id
                    ),
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
