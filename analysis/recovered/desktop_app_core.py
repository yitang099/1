"""
Core SMS/order logic recovered from desktop_app.pyc bytecode (pycdas/xdis).

pycdc decompilation truncates at ~line 580; these methods are rebuilt from
disassembly constants and control flow. UI code: recovered/desktop_app.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request


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


class SmsClientMixin:
  """Mixin for App — implement get_api_config, api_get_text_sms, decrease_balance, etc."""

  def get_api_config(self) -> tuple[str, str]:
    domain = self.get_setting_value("api_domain", "").strip().rstrip("/")
    key = self.get_setting_value("api_secret", "").strip()
    return domain, key

  def get_current_deduct(self) -> float:
    try:
      data = self.api_get_json(
        "/api/desktop/user-info", {"username": self.current_user}
      )
      if data.get("ok"):
        deduct = data.get("deduct_amount", 0)
        if deduct in (None, ""):
          return 0.0
        return float(deduct)
    except Exception:
      pass
    return 0.0

  def get_user_balance(self) -> float:
    try:
      data = self.api_get_json(
        "/api/desktop/user-info", {"username": self.current_user}
      )
      if data.get("ok"):
        user = data.get("user") or {}
        return float(user.get("balance") or 0)
    except Exception:
      pass
    return 0.0

  def decrease_balance(self, amount: float) -> None:
    result = self.api_post_json(
      "/api/desktop/decrease-balance",
      {"username": self.current_user, "amount": amount},
    )
    if not result.get("ok"):
      raise RuntimeError(result.get("message") or "扣费失败")
    self.refresh_balance()

  def api_post_json_sms(self, url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
      url,
      data=data,
      headers={"Content-Type": "application/json"},
      method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
      return json.loads(resp.read().decode("utf-8", errors="replace"))

  def api_get_text_sms(self, url: str) -> str:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
      return resp.read().decode("utf-8", errors="replace")

  def submit_order_for_row(self, row: int) -> None:
    phone = self.phone_entries[row].get().strip()
    if not phone:
      self._set_row_status(row, "❌ 手机号为空", "#ef4444")
      return
    balance = self.get_user_balance()
    deduct_amount = self.get_current_deduct()
    if balance < deduct_amount:
      self._set_row_status(
        row,
        f"❌ 余额不足: 需要{deduct_amount}，余额{balance}",
        "#ef4444",
      )
      return
    domain, key = self.get_api_config()
    if not domain or not key:
      self._set_row_status(row, "请配置域名和密钥", "#ef4444")
      return
    area = self.area_code_entry.get().strip() or "86"
    create_url = f"{domain}/create/{urllib.parse.quote(key, safe='')}"
    payload = {"area": area, "data": phone, "islink": False}
    self._set_row_status(row, "⏳ 提交订单中...", "#f59e0b")
    try:
      create_resp = self.api_post_json_sms(create_url, payload)
    except Exception as exc:
      self._set_row_status(row, f"❌ 网络错误: {exc}", "#ef4444")
      return
    if create_resp.get("code") != 0:
      err_msg = create_resp.get("err") or "提交失败"
      self._set_row_status(row, f"❌ {err_msg}", "#ef4444")
      return
    order_id = create_resp.get("data") or ""
    od = self.order_data[row]
    od.update(
      order_id=order_id,
      phone=phone,
      status="查询中",
      submitted=True,
      polling=False,
      stop_polling=False,
      waiting_for_code=False,
      completed=False,
      balance_deducted=False,
    )
    if not od.get("balance_deducted"):
      try:
        self.decrease_balance(deduct_amount)
        od["balance_deducted"] = True
      except Exception as exc:
        self._set_row_status(row, f"❌ {exc}", "#ef4444")
        return
    self._set_row_status(row, "✅ 订单创建成功", "#10b981")
    self.poll_order(row)

  def query_order_sync(self, row: int) -> None:
    """查询订单状态 - 参考1.py的完整逻辑"""
    od = self.order_data[row]
    order_id = od.get("order_id") or ""
    phone = od.get("phone") or self.phone_entries[row].get().strip()
    if not order_id:
      self._set_row_status(row, "❌ 订单号为空", "#ef4444")
      return
    domain, key = self.get_api_config()
    if not domain or not key:
      self._set_row_status(row, "❌ 未配置API", "#ef4444")
      return
    url = f"{domain}/query/{urllib.parse.quote(key, safe='')}/{order_id}"
    try:
      resp_text = self.api_get_text_sms(url)
      resp_json = json.loads(resp_text)
    except json.JSONDecodeError:
      self._set_row_status(row, "❌ JSON解析错误", "#ef4444")
      return
    except Exception as exc:
      self._set_row_status(row, f"❌ 网络错误: {exc}", "#ef4444")
      return
    code = resp_json.get("code")
    data = resp_json.get("data") or ""
    err = resp_json.get("err") or ""
    cleaned = clean_result_data(str(data))
    if code == 0:
      self._set_row_status(row, f"✅ {cleaned[:50]}", "#10b981")
      od["completed"] = True
      od["result"] = cleaned
      self.record_row_if_finished(row)
      return
    if code == 1 and err:
      m = re.search(r"\b(\d{4,6})\b", err)
      if m:
        sms_code = m.group(1)
        self.code_entries[row].delete(0, "end")
        self.code_entries[row].insert(0, sms_code)
        self._set_row_status(row, f"✅ 验证码: {sms_code}", "#10b981")
      if "请输入验证码" in err or "等待" in err:
        od["waiting_for_code"] = True
        self._set_row_status(row, "⏳ 请输入验证码后点击提交", "#f59e0b")
        return
      self._set_row_status(row, f"⏳ {err}", "#f59e0b")
      return
    if any(k in str(data) + str(err) for k in FAIL_KEYWORDS):
      self._set_row_status(row, f"❌ 失败: {err or data}", "#ef4444")
      od["completed"] = True
      return
    self._set_row_status(row, "⏳ 处理中...", "#f59e0b")

  def submit_code_sync(self, row: int) -> None:
    code = self.code_entries[row].get().strip()
    phone = self.phone_entries[row].get().strip()
    if not code:
      self._set_row_status(row, "❌ 验证码为空", "#ef4444")
      return
    domain, key = self.get_api_config()
    if not domain or not key:
      self._set_row_status(row, "❌ 未配置API", "#ef4444")
      return
    url = f"{domain}/setsms/{urllib.parse.quote(key, safe='')}/{phone}/{code}"
    self._set_row_status(row, "⏳ 提交验证码中...", "#f59e0b")
    try:
      resp = self.api_get_text_sms(url)
    except Exception as exc:
      self._set_row_status(row, f"❌ {exc}", "#ef4444")
      return
    if "成功" in resp:
      od = self.order_data[row]
      od["waiting_for_code"] = False
      od["status"] = "查询中"
      self._set_row_status(row, "✅ 验证码已提交，等待结果...", "#10b981")
    else:
      self._set_row_status(row, f"❌ {resp}", "#ef4444")

  def poll_order(self, row: int) -> None:
    def poll_worker():
      od = self.order_data[row]
      od["polling"] = True
      for i in range(1, 121):
        if od.get("stop_polling") or od.get("completed"):
          break
        if od.get("waiting_for_code"):
          deadline = time.time() + 300
          while time.time() < deadline:
            if od.get("stop_polling") or od.get("completed"):
              break
            if not od.get("waiting_for_code"):
              break
            time.sleep(1)
          else:
            self._set_row_status(row, "⏰ 等待验证码超时", "#ef4444")
            break
        self.query_order_sync(row)
        if od.get("completed"):
          break
        time.sleep(3)
      else:
        if not od.get("completed"):
          self._set_row_status(row, "⏰ 查询超时", "#ef4444")
      od["polling"] = False

    import threading

    threading.Thread(target=poll_worker, daemon=True).start()
