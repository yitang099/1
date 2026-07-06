#!/usr/bin/env python3
"""
Recovered SMS/query API (47.76.163.227:8081) — behavioral clone.

Original is ASP.NET Kestrel; this Python replica matches observed routes,
JSON/text responses, and the 2-step SMS state machine.

Tencent wtlogin / TLV543 QQ bind logic is NOT in this file; see
../qq_sms_bind/qq_easy_core.py and parse_qq_bind_uin.py for protocol layer.
"""
from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from flask import Flask, jsonify, request

VALID_TOKEN = "b9887333ae4c43858c9235e0ac4e0921"


class Step(Enum):
    WAIT_SMS = 1
    WAIT_VERIFY = 2


@dataclass
class Order:
    order_id: str
    phone: str
    area: str
    step: Step = Step.WAIT_SMS
    created_at: float = field(default_factory=time.time)
    sms_code: Optional[str] = None
    result_data: str = ""
    done: bool = False

    def err_processing(self) -> str:
        if self.step == Step.WAIT_SMS:
            return f"订单正在处理 [{self.phone}] 请输入验证码！当前 1 / 2"
        return f"订单正在处理 [{self.phone}] ‼️短信验证码 [错误] 或者 [超时]！当前 2 / 2"


_lock = threading.Lock()
_orders_by_id: Dict[str, Order] = {}
_phone_active: Dict[str, str] = {}


def _check_token(secret: str) -> bool:
    return secret == VALID_TOKEN


def _valid_phone(area: str, data: str, islink: bool) -> bool:
    if islink:
        return False
    if area != "86":
        return bool(re.fullmatch(r"\d{6,15}", data))
    return bool(re.fullmatch(r"1\d{10}", data))


def create_app() -> Flask:
    app = Flask(__name__)

    @app.post("/create/<secret>")
    def create_order(secret: str):
        if not _check_token(secret):
            return "无效Token!", 200, {"Content-Type": "text/plain; charset=utf-8"}
        payload = request.get_json(silent=True) or {}
        area = str(payload.get("area") or "86")
        data = str(payload.get("data") or "").strip()
        islink = bool(payload.get("islink"))
        if not _valid_phone(area, data, islink):
            return jsonify(
                err="💬未检测到有效手机数据, 请检查输入格式", code=-2
            )
        with _lock:
            if data in _phone_active:
                return jsonify(
                    err="💬此手机号码已经正在进行查询，结束订单后提交",
                    code=-3,
                )
            order_id = uuid.uuid4().hex
            order = Order(order_id=order_id, phone=data, area=area)
            _orders_by_id[order_id] = order
            _phone_active[data] = order_id
        return jsonify(data=order_id, code=0)

    @app.get("/query/<secret>/<order_id>")
    def query_order(secret: str, order_id: str):
        if not _check_token(secret):
            return jsonify(err="无效Token!", code=-1)
        with _lock:
            order = _orders_by_id.get(order_id)
        if not order:
            return jsonify(err="订单不存在", code=-1)
        if order.done and order.result_data:
            return jsonify(code=0, data=order.result_data)
        if order.step == Step.WAIT_SMS:
            return jsonify(code=1, err=order.err_processing())
        if order.step == Step.WAIT_VERIFY and not order.sms_code:
            return jsonify(code=1, err=order.err_processing())
        if order.step == Step.WAIT_VERIFY:
            return jsonify(code=1, err=order.err_processing())
        return jsonify(code=1, err=order.err_processing())

    @app.get("/setsms/<secret>/<phone>/<code>")
    def set_sms(secret: str, phone: str, code: str):
        if not _check_token(secret):
            return "无效Token!", 200, {"Content-Type": "text/plain; charset=utf-8"}
        with _lock:
            order_id = _phone_active.get(phone)
            order = _orders_by_id.get(order_id) if order_id else None
        if not order:
            return "没有该手机订单!", 200, {"Content-Type": "text/plain; charset=utf-8"}
        order.sms_code = code
        if order.step == Step.WAIT_SMS:
            order.step = Step.WAIT_VERIFY
            return "上传短信验证码成功", 200, {"Content-Type": "text/plain; charset=utf-8"}
        return "上传短信验证码成功", 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8081, debug=False)
