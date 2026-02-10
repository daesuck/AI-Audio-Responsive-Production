"""
간단한 Install Wizard (FastAPI 기반, v1)

- GET / : 간단한 HTML 폼(정적)
- GET /api/config : 현재 설정 반환
- POST /api/config : 설정 저장(검증 포함)
- GET /api/status : 엔진 상태(간단한 JSON)

주의: 실행 환경에 FastAPI/uvicorn이 없을 수 있으므로, 해당 패키지가 없으면
실행 시 명시적 오류가 발생합니다. 테스트는 `config_manager` 검증을 사용합니다.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from src.web import config_manager

app = FastAPI()
logger = logging.getLogger(__name__)


@app.get("/", response_class=HTMLResponse)
async def wizard_index():
    # 매우 단순한 HTML 폼 (자바스크립트 없이 최소한의 기능)
    html = """
    <html>
      <head><title>Install Wizard</title></head>
      <body>
        <h1>Install Wizard (v1)</h1>
        <p>API 엔드포인트를 통해 구성 파일을 업로드/저장하세요.</p>
        <ul>
          <li>GET /api/config - 현재 구성 조회</li>
          <li>POST /api/config - JSON 구성 저장</li>
        </ul>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/api/config")
async def api_get_config():
    cfg = config_manager.load_config()
    return JSONResponse(content=cfg)


@app.post("/api/config")
async def api_post_config(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON 파싱 실패")

    ok, errors = config_manager.validate_config(body)
    if not ok:
        raise HTTPException(status_code=422, detail={"errors": errors})

    # 저장
    config_manager.save_config(body)
    return JSONResponse(content={"ok": True})


@app.get("/api/status")
async def api_status():
    # 간단한 엔진 상태 반환 (확장 가능)
    cfg = config_manager.load_config()
    mtime = config_manager.get_config_mtime()
    return JSONResponse(content={"running": False, "config_mtime": mtime, "config_present": bool(cfg)})
