#!/usr/bin/env python3
"""
8081 API 接口与数据结构全量探测。
输出 JSON 报告到 stdout，供写入 analysis/8081_API_SPEC.md
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

SMS = "http://47.76.163.227:8081"
SECRET = "18cdfb81a4e44a3a915528e67d923dba"


@dataclass
class Sample:
    name: str
    method: str
    path: str
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body_raw: str = ""
    body_json: Any | None = None
    notes: str = ""


def req(
    method: str,
    path: str,
    payload: dict | None = None,
    headers: dict | None = None,
    timeout: float = 15,
) -> Sample:
    url = SMS + path
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    h = dict(headers or {})
    if data is not None:
        h.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            hdrs = {k: v for k, v in resp.headers.items()}
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        hdrs = {k: v for k, v in e.headers.items()} if e.headers else {}
        status = e.code

    parsed = None
    if raw.lstrip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            pass
    return Sample("", method, path, status, hdrs, raw, parsed)


def parse_result_data(data: str) -> dict[str, Any]:
    """Parse query success data block into structured fields."""
    out: dict[str, Any] = {"raw": data, "lines": []}
    if not data:
        return out
    lines = [ln.strip() for ln in data.replace("\r\n", "\n").split("\n")]
    out["lines"] = [ln for ln in lines if ln]
    for ln in out["lines"]:
        if "----" in ln and not ln.startswith("订单") and not ln.startswith("当前"):
            phone, _, status = ln.partition("----")
            out["phone"] = phone.strip()
            out["bind_status"] = status.strip()
        if ln.startswith("订单扣费"):
            out["order_fee"] = ln.split("：", 1)[-1].strip()
        if ln.startswith("当前余额"):
            out["channel_balance"] = ln.split("：", 1)[-1].strip()
        if ln.startswith("单价"):
            out["unit_price"] = ln.split("：", 1)[-1].strip()
        if ln.startswith("总价"):
            out["total_price"] = ln.split("：", 1)[-1].strip()
        if ln.startswith("有效数据"):
            out["valid_data_hint"] = ln
    return out


def poll_query(secret: str, order_id: str, max_wait: int = 30) -> list[Sample]:
    samples: list[Sample] = []
    path = f"/query/{secret}/{order_id}"
    for i in range(max_wait):
        s = req("GET", path)
        s.name = f"query_poll_{i+1}"
        samples.append(s)
        if s.body_json and s.body_json.get("code") == 0:
            break
        if s.body_json and s.body_json.get("code") not in (-1, 1):
            break
        time.sleep(2)
    return samples


def main() -> int:
    report: dict[str, Any] = {
        "base": SMS,
        "secret_sample": SECRET[:8] + "...",
        "timestamp": int(time.time()),
        "endpoints": {},
        "error_codes": {},
        "lifecycle": [],
        "data_schema": {},
    }

    # --- balance ---
    bal = req("GET", f"/balance/{SECRET}")
    bal.name = "balance_ok"
    report["endpoints"]["balance"] = {
        "method": "GET",
        "path": "/balance/{secret}",
        "response_type": "plain_text_number" if bal.body_raw.replace(".", "", 1).isdigit() else "text",
        "samples": [bal.__dict__],
    }

    # --- create variants ---
    create_cases = [
        ("create_ok", {"area": "86", "data": f"1990000{int(time.time())%10000:04d}", "islink": False}),
        ("create_bad_phone", {"area": "86", "data": "abc", "islink": False}),
        ("create_empty", {"area": "86", "data": "", "islink": False}),
        ("create_no_area", {"data": f"1990000{(int(time.time())+1)%10000:04d}", "islink": False}),
        ("create_hk", {"area": "852", "data": "91234567", "islink": False}),
        ("create_islink", {"area": "86", "data": f"1990000{(int(time.time())+2)%10000:04d}", "islink": True}),
    ]
    create_samples: list[dict] = []
    main_order_id = ""
    main_phone = ""
    for name, payload in create_cases:
        s = req("POST", f"/create/{SECRET}", payload)
        s.name = name
        create_samples.append(s.__dict__)
        if name == "create_ok" and s.body_json and s.body_json.get("code") == 0:
            main_order_id = str(s.body_json.get("data") or "")
            main_phone = str(payload["data"])
        if s.body_json:
            code = s.body_json.get("code")
            report["error_codes"].setdefault(str(code), []).append(
                {"endpoint": "create", "case": name, "err": s.body_json.get("err"), "data": s.body_json.get("data")}
            )
    report["endpoints"]["create"] = {
        "method": "POST",
        "path": "/create/{secret}",
        "content_type": "application/json",
        "body_fields": {
            "area": "string, 区号, 可省略默认86",
            "data": "string, 手机号",
            "islink": "bool, true=链接模式",
        },
        "samples": create_samples,
    }

    # --- query lifecycle on main order ---
    if main_order_id:
        lifecycle: list[dict] = []
        for s in poll_query(SECRET, main_order_id, max_wait=15):
            item = {
                "name": s.name,
                "status": s.status,
                "body_raw": s.body_raw[:500],
                "body_json": s.body_json,
            }
            if s.body_json and s.body_json.get("code") == 0:
                item["parsed_data"] = parse_result_data(str(s.body_json.get("data") or ""))
            lifecycle.append(item)
            if s.body_json:
                code = s.body_json.get("code")
                report["error_codes"].setdefault(f"query_{code}", []).append(
                    {"err": s.body_json.get("err"), "data_preview": str(s.body_json.get("data") or "")[:120]}
                )
        report["lifecycle"] = lifecycle

        # setsms before/during - use wrong code on active phone if any
        for phone, code, label in [
            (main_phone, "000000", "setsms_wrong_code"),
            ("18800000000", "1234", "setsms_no_order"),
        ]:
            path = f"/setsms/{SECRET}/{urllib.parse.quote(phone)}/{code}"
            s = req("GET", path)
            s.name = label
            report.setdefault("setsms_samples", []).append(s.__dict__)

        # duplicate create same phone
        if main_phone:
            s = req("POST", f"/create/{SECRET}", {"area": "86", "data": main_phone, "islink": False})
            s.name = "create_duplicate_phone"
            report.setdefault("create_extra", []).append(s.__dict__)

    # --- query edge cases ---
    query_cases = [
        ("query_missing_order", f"/query/{SECRET}/{'0'*32}"),
        ("query_short_id", f"/query/{SECRET}/abc"),
        ("query_secret_order", f"/query/{SECRET}/{SECRET}"),
    ]
    query_samples = []
    for name, path in query_cases:
        s = req("GET", path)
        s.name = name
        query_samples.append(s.__dict__)
    report["endpoints"]["query"] = {
        "method": "GET",
        "path": "/query/{secret}/{order_id}",
        "samples": query_samples,
    }

    report["endpoints"]["setsms"] = {
        "method": "GET (POST also 200)",
        "path": "/setsms/{secret}/{phone}/{sms_code}",
        "response_type": "plain_text",
        "samples": report.get("setsms_samples", []),
    }

    # data schema from lifecycle
    parsed_examples = []
    for step in report.get("lifecycle", []):
        if step.get("parsed_data"):
            parsed_examples.append(step["parsed_data"])
    report["data_schema"] = {
        "format": "multiline_text_in_json_data_field",
        "fields": {
            "phone----status": "首行: 手机号----绑定状态(未注册/QQ号等)",
            "订单扣费": "本单扣费金额",
            "当前余额": "通道余额(泄露)",
            "单价/总价/有效数据": "create失败或部分err中出现",
        },
        "examples": parsed_examples[:3],
    }

    # balance after
    bal2 = req("GET", f"/balance/{SECRET}")
    report["balance_after"] = bal2.body_raw.strip()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
