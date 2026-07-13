"""Tencent gamesafe punish_query API client."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import requests

PUNISH_URL = "https://credit.gamesafe.qq.com/cgi-bin/qq/proxy/punish_query"
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class BanRecord:
    game_name: str
    reason: str
    zone: str
    start_time: str
    duration: str

    @classmethod
    def from_item(cls, item: dict[str, Any]) -> "BanRecord":
        start = item.get("start_stmp") or item.get("start_time") or ""
        if isinstance(start, (int, float)) and start > 0:
            try:
                start = datetime.fromtimestamp(int(start)).strftime("%Y-%m-%d %H:%M:%S")
            except (OSError, ValueError, OverflowError):
                start = str(start)
        dur = item.get("duration") or item.get("ban_duration") or ""
        if isinstance(dur, (int, float)):
            dur = f"{dur}天" if dur else ""
        return cls(
            game_name=str(item.get("game_name") or item.get("game") or "未知"),
            reason=str(item.get("reason") or item.get("ban_reason") or ""),
            zone=str(item.get("zone") or item.get("area") or ""),
            start_time=str(start),
            duration=str(dur),
        )


def calc_gtk(skey: str) -> int:
  h = 5381
  for ch in skey:
    h += (h << 5) + ord(ch)
  return h & 0x7FFFFFFF


def normalize_uin(uin: str) -> str:
  u = re.sub(r"\D", "", str(uin or ""))
  if not u:
    raise ValueError("QQ号无效")
  return u


def build_cookie_header(cookies: dict[str, str], uin: str) -> dict[str, str]:
  u = normalize_uin(uin)
  ck = dict(cookies)
  ck.setdefault("uin", f"o{u}")
  ck.setdefault("p_uin", f"o{u}")
  if "skey" not in ck and "p_skey" in ck:
    ck["skey"] = ck["p_skey"]
  if not ck.get("skey"):
    raise ValueError("缺少 skey，请确认 WeGame 数据目录包含有效登录态")
  parts = [f"{k}={v}" for k, v in ck.items() if v]
  headers = {
    "User-Agent": DEFAULT_UA,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://credit.gamesafe.qq.com/",
    "Cookie": "; ".join(parts),
  }
  return headers


def _walk_records(node: Any, out: list[dict[str, Any]]) -> None:
  if isinstance(node, dict):
    if "history_list" in node and isinstance(node["history_list"], list):
      for item in node["history_list"]:
        if isinstance(item, dict):
          out.append(item)
    for v in node.values():
      _walk_records(v, out)
  elif isinstance(node, list):
    for item in node:
      _walk_records(item, out)


def query_ban_history(
  uin: str,
  cookies: dict[str, str],
  *,
  limit: int = 50,
  query_type: int = 3,
  begin_date: int = 1451577600,
  timeout: int = 20,
) -> tuple[list[BanRecord], dict[str, Any]]:
  """Query punish/ban history for the QQ account tied to cookies."""
  params = {
    "limit": str(limit),
    "query_type": str(query_type),
    "begin_date": str(begin_date),
  }
  headers = build_cookie_header(cookies, uin)
  skey = cookies.get("skey") or cookies.get("p_skey", "")
  if skey:
    params["g_tk"] = str(calc_gtk(skey))

  resp = requests.get(PUNISH_URL, params=params, headers=headers, timeout=timeout)
  resp.raise_for_status()
  raw: Any
  try:
    raw = resp.json()
  except json.JSONDecodeError:
    raw = {"raw_text": resp.text[:2000]}

  records: list[dict[str, Any]] = []
  _walk_records(raw, records)
  bans = [BanRecord.from_item(x) for x in records]
  meta = {
    "url": resp.url,
    "status": resp.status_code,
    "record_count": len(bans),
    "raw_preview": raw if isinstance(raw, dict) else str(raw)[:500],
  }
  return bans, meta
