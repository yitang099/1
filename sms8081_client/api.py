"""8081 SMS API client."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


FAIL_KEYWORDS = ("未注册", "发送短信失败", "失败", "未绑定", "短信发送失败", "余额不足")


def clean_result_data(data: str) -> str:
    if not data:
        return ""
    lines = data.split("\n")
    cleaned = []
    for line in lines:
        if any(k in line for k in ("订单扣费", "当前余额", "余额", "单价", "总价", "有效数据")):
            continue
        s = line.strip()
        if s:
            cleaned.append(s)
    return "\n".join(cleaned) if cleaned else data.strip()


class Sms8081Client:
    def __init__(
        self,
        sms_base: str = "http://47.76.163.227:8081",
        api_secret: str = "",
        proxy: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.sms_base = sms_base.rstrip("/")
        self.api_secret = api_secret.strip()
        self.proxy = proxy.strip() if proxy else None
        self.timeout = timeout

    def _opener(self) -> urllib.request.OpenerDirector:
        if self.proxy:
            handler = urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy})
            return urllib.request.build_opener(handler)
        return urllib.request.build_opener()

    def _request(
        self,
        method: str,
        url: str,
        payload: dict | None = None,
    ) -> tuple[int, str]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        opener = self._opener()
        try:
            with opener.open(req, timeout=self.timeout) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def _secret_path(self) -> str:
        if not self.api_secret:
            raise RuntimeError("请先填写 API Secret")
        return urllib.parse.quote(self.api_secret, safe="")

    def get_balance(self) -> str:
        code, body = self._request("GET", f"{self.sms_base}/balance/{self._secret_path()}")
        if code != 200:
            raise RuntimeError(f"查询余额失败 HTTP {code}: {body[:120]}")
        text = body.strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    for key in ("balance", "data", "amount"):
                        if key in data and data[key] is not None:
                            return str(data[key]).strip()
            except json.JSONDecodeError:
                pass
        return text

    def create_order(self, phone: str, area: str = "86", islink: bool = False) -> str:
        url = f"{self.sms_base}/create/{self._secret_path()}"
        code, body = self._request(
            "POST",
            url,
            {"area": area, "data": phone, "islink": islink},
        )
        if not body.startswith("{"):
            raise RuntimeError(body.strip() or f"HTTP {code}")
        data = json.loads(body)
        if data.get("code") != 0:
            raise RuntimeError(data.get("err") or data.get("data") or "下单失败")
        order_id = str(data.get("data") or "").strip()
        if not order_id:
            raise RuntimeError("未返回 order_id")
        return order_id

    def submit_sms_code(self, phone: str, code: str) -> str:
        url = (
            f"{self.sms_base}/setsms/{self._secret_path()}/"
            f"{urllib.parse.quote(phone, safe='')}/{urllib.parse.quote(code, safe='')}"
        )
        _, body = self._request("GET", url)
        return body

    def query_order(self, order_id: str) -> dict:
        url = f"{self.sms_base}/query/{self._secret_path()}/{urllib.parse.quote(order_id, safe='')}"
        _, body = self._request("GET", url)
        if not body.startswith("{"):
            raise RuntimeError(body[:200])
        return json.loads(body)
