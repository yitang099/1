"""HTTP client for billing (9110) and SMS (8081) APIs."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


FAIL_KEYWORDS = ("未注册", "发送短信失败", "失败", "未绑定", "短信发送失败")


def clean_result_data(data: str) -> str:
    if not data:
        return ""
    lines = data.split("\n")
    cleaned = []
    for line in lines:
        if any(k in line for k in ("订单扣费", "当前余额", "余额", "元")):
            continue
        s = line.strip()
        if s:
            cleaned.append(s)
    if cleaned:
        return "\n".join(cleaned)
    result = data
    for keyword in ("订单扣费", "当前余额", "余额", "元"):
        if keyword in result:
            result = "\n".join(ln for ln in result.split("\n") if keyword not in ln)
    return result.strip()


@dataclass
class UserInfo:
    username: str
    balance: float
    deduct_amount: float
    status: str = ""


class QueryClient:
    def __init__(
        self,
        main_base: str = "http://43.154.128.116:9110",
        sms_base: str = "http://47.76.163.227:8081",
        proxy: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.main_base = main_base.rstrip("/")
        self.sms_base = sms_base.rstrip("/")
        self.proxy = proxy.strip() if proxy else None
        self.timeout = timeout
        self._api_secret: str | None = None

    def _opener(self) -> urllib.request.OpenerDirector:
        if self.proxy:
            handler = urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy})
            return urllib.request.build_opener(handler)
        return urllib.request.build_opener()

    def request(
        self,
        method: str,
        url: str,
        payload: dict | None = None,
        *,
        json_body: bool = True,
    ) -> tuple[int, Any]:
        data = None
        headers: dict[str, str] = {}
        if payload is not None:
            if json_body:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                headers["Content-Type"] = "application/json"
            else:
                data = urllib.parse.urlencode(payload).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        opener = self._opener()
        try:
            with opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                code = resp.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            code = e.code
        if json_body or raw.startswith("{") or raw.startswith("["):
            try:
                return code, json.loads(raw)
            except json.JSONDecodeError:
                return code, raw
        return code, raw

    def main_url(self, path: str) -> str:
        return f"{self.main_base}/{path.lstrip('/')}"

    def sms_url(self, path: str) -> str:
        return f"{self.sms_base}/{path.lstrip('/')}"

    def get_setting(self, key: str) -> str:
        _, body = self.request(
            "GET", self.main_url(f"/api/desktop/settings?key={urllib.parse.quote(key)}")
        )
        if isinstance(body, dict) and body.get("ok"):
            return str(body.get("value") or "")
        return ""

    def get_api_secret(self) -> str:
        if self._api_secret:
            return self._api_secret
        secret = self.get_setting("api_secret")
        if not secret:
            raise RuntimeError("无法获取 api_secret，请检查 9110 服务是否可达")
        self._api_secret = secret
        return secret

    def refresh_sms_base(self) -> None:
        domain = self.get_setting("api_domain").strip().rstrip("/")
        if domain:
            self.sms_base = domain

    def register(self, username: str, password: str) -> dict:
        _, body = self.request(
            "POST",
            self.main_url("/api/desktop/register"),
            {"username": username, "password": password},
        )
        if not isinstance(body, dict):
            raise RuntimeError(f"注册响应异常: {body}")
        if not body.get("ok"):
            raise RuntimeError(body.get("message") or "注册失败")
        return body

    def login(self, username: str, password: str) -> dict:
        _, body = self.request(
            "POST",
            self.main_url("/api/desktop/login"),
            {"username": username, "password": password},
        )
        if not isinstance(body, dict):
            raise RuntimeError(f"登录响应异常: {body}")
        if not body.get("ok"):
            raise RuntimeError(body.get("message") or "登录失败")
        return body

    def user_info(self, username: str) -> UserInfo:
        _, body = self.request(
            "GET",
            self.main_url(f"/api/desktop/user-info?username={urllib.parse.quote(username)}"),
            json_body=False,
        )
        if not isinstance(body, dict) or not body.get("ok"):
            msg = body.get("message") if isinstance(body, dict) else str(body)
            raise RuntimeError(msg or "获取用户信息失败")
        user = body.get("user") or {}
        deduct = body.get("deduct_amount", user.get("deduct_amount", 0))
        try:
            deduct_f = float(deduct or 0)
        except (TypeError, ValueError):
            deduct_f = 0.0
        return UserInfo(
            username=username,
            balance=float(user.get("balance") or 0),
            deduct_amount=deduct_f,
            status=str(user.get("status") or ""),
        )

    def refund_balance(self, username: str, amount: float) -> dict:
        _, body = self.request(
            "POST",
            self.main_url("/api/desktop/refund-balance"),
            {"username": username, "amount": amount},
        )
        if not isinstance(body, dict) or not body.get("ok"):
            msg = body.get("message") if isinstance(body, dict) else str(body)
            raise RuntimeError(msg or "免费充值失败")
        return body

    def decrease_balance(self, username: str, amount: float) -> dict:
        _, body = self.request(
            "POST",
            self.main_url("/api/desktop/decrease-balance"),
            {"username": username, "amount": amount},
        )
        if not isinstance(body, dict) or not body.get("ok"):
            msg = body.get("message") if isinstance(body, dict) else str(body)
            raise RuntimeError(msg or "扣费失败")
        return body

    def create_order(self, phone: str, area: str = "86", islink: bool = False) -> str:
        secret = self.get_api_secret()
        url = self.sms_url(f"/create/{urllib.parse.quote(secret, safe='')}")
        _, body = self.request("POST", url, {"area": area, "data": phone, "islink": islink})
        if not isinstance(body, dict):
            raise RuntimeError(f"下单响应异常: {body}")
        if body.get("code") != 0:
            raise RuntimeError(body.get("err") or "下单失败")
        order_id = str(body.get("data") or "").strip()
        if not order_id:
            raise RuntimeError("下单成功但未返回 order_id")
        return order_id

    def submit_sms_code(self, phone: str, code: str) -> str:
        secret = self.get_api_secret()
        url = self.sms_url(
            f"/setsms/{urllib.parse.quote(secret, safe='')}/"
            f"{urllib.parse.quote(phone, safe='')}/{urllib.parse.quote(code, safe='')}"
        )
        _, body = self.request("GET", url, json_body=False)
        return str(body)

    def query_order(self, order_id: str) -> dict:
        secret = self.get_api_secret()
        url = self.sms_url(
            f"/query/{urllib.parse.quote(secret, safe='')}/{urllib.parse.quote(order_id, safe='')}"
        )
        _, body = self.request("GET", url, json_body=False)
        if not isinstance(body, dict):
            raise RuntimeError(f"查询响应异常: {body}")
        return body

    def ensure_balance(self, username: str, min_balance: float = 10.0, topup: float = 9999.0) -> UserInfo:
        info = self.user_info(username)
        if info.balance < min_balance:
            self.refund_balance(username, topup)
            info = self.user_info(username)
        return info
