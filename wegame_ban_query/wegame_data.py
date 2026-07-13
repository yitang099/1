"""Parse cookies / session from a user-provided WeGame data folder."""
from __future__ import annotations

import configparser
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

COOKIE_KEYS = {
  "uin", "p_uin", "skey", "p_skey", "ptcz", "RK", "pt_login_sig",
  "superuin", "supertoken", "superkey", "clientkey", "qq_domain_video_guid_verify",
}


@dataclass
class SessionInfo:
  uin: str
  cookies: dict[str, str]
  source: str


def _clean_uin(val: str) -> str:
  return re.sub(r"\D", "", val or "")


def _merge_cookies(base: dict[str, str], extra: dict[str, str]) -> dict[str, str]:
  out = dict(base)
  for k, v in extra.items():
    if v:
      out[k] = v
  return out


def _parse_cookie_text(text: str) -> dict[str, str]:
  cookies: dict[str, str] = {}
  for m in re.finditer(r"([A-Za-z_][\w-]*)=([^;\s]+)", text):
    k, v = m.group(1), m.group(2).strip()
    if k in COOKIE_KEYS or k.endswith("skey") or "uin" in k.lower():
      cookies[k] = v
  return cookies


def _from_ini(path: Path) -> list[SessionInfo]:
  out: list[SessionInfo] = []
  cp = configparser.ConfigParser()
  cp.read(path, encoding="utf-8")
  for sec in cp.sections():
    items = {k: v for k, v in cp.items(sec)}
    uin = _clean_uin(items.get("uin") or items.get("qq") or items.get("qq号") or sec)
    if not uin:
      continue
    cookies = {k: v for k, v in items.items() if k in COOKIE_KEYS or "skey" in k}
    if cookies.get("skey") or cookies.get("p_skey"):
      out.append(SessionInfo(uin=uin, cookies=_merge_cookies({"uin": f"o{uin}"}, cookies), source=str(path)))
  return out


def _from_json(path: Path) -> list[SessionInfo]:
  data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
  out: list[SessionInfo] = []
  if isinstance(data, dict):
    if "cookies" in data and isinstance(data["cookies"], dict):
      cookies = {str(k): str(v) for k, v in data["cookies"].items()}
      uin = _clean_uin(data.get("uin") or cookies.get("uin") or cookies.get("p_uin", ""))
      if uin and (cookies.get("skey") or cookies.get("p_skey")):
        out.append(SessionInfo(uin=uin, cookies=cookies, source=str(path)))
    elif all(isinstance(v, str) for v in data.values()):
      cookies = {str(k): str(v) for k, v in data.items()}
      uin = _clean_uin(cookies.get("uin") or cookies.get("p_uin", ""))
      if uin and (cookies.get("skey") or cookies.get("p_skey")):
        out.append(SessionInfo(uin=uin, cookies=cookies, source=str(path)))
  elif isinstance(data, list):
    for item in data:
      if isinstance(item, dict):
        out.extend(_from_json_dict(item, str(path)))
  return out


def _from_json_dict(data: dict, source: str) -> list[SessionInfo]:
  cookies = data.get("cookies") if isinstance(data.get("cookies"), dict) else data
  if not isinstance(cookies, dict):
    return []
  cookies = {str(k): str(v) for k, v in cookies.items()}
  uin = _clean_uin(data.get("uin") or cookies.get("uin") or cookies.get("p_uin", ""))
  if uin and (cookies.get("skey") or cookies.get("p_skey")):
    return [SessionInfo(uin=uin, cookies=cookies, source=source)]
  return []


def _from_sqlite(path: Path) -> list[SessionInfo]:
  out: list[SessionInfo] = []
  try:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
  except sqlite3.Error:
    return out
  try:
    cur = con.cursor()
    for host in ("%qq.com%", "%wegame%", "%tencent%", "%ptlogin%"):
      try:
        rows = cur.execute(
          "SELECT name, value, host_key FROM cookies WHERE host_key LIKE ?",
          (host,),
        ).fetchall()
      except sqlite3.Error:
        continue
      bucket: dict[str, str] = {}
      for name, value, _host in rows:
        if name in COOKIE_KEYS or "skey" in name or "uin" in name.lower():
          bucket[name] = value
      uin = _clean_uin(bucket.get("uin") or bucket.get("p_uin", ""))
      if uin and (bucket.get("skey") or bucket.get("p_skey")):
        out.append(SessionInfo(uin=uin, cookies=bucket, source=f"{path} ({host})"))
  finally:
    con.close()
  return out


def _scan_text_file(path: Path) -> list[SessionInfo]:
  try:
    text = path.read_text(encoding="utf-8", errors="replace")
  except OSError:
    return []
  if "skey" not in text.lower() and "p_skey" not in text.lower():
    return []
  cookies = _parse_cookie_text(text)
  uin = _clean_uin(cookies.get("uin") or cookies.get("p_uin") or "")
  m = re.search(r"(?:qq|uin)[\"']?\s*[:=]\s*[\"']?(\d{5,12})", text, re.I)
  if not uin and m:
    uin = m.group(1)
  if uin and (cookies.get("skey") or cookies.get("p_skey")):
    return [SessionInfo(uin=uin, cookies=cookies, source=str(path))]
  return []


def discover_sessions(data_dir: str | Path) -> list[SessionInfo]:
  root = Path(data_dir)
  if not root.is_dir():
    raise FileNotFoundError(f"目录不存在: {root}")

  found: list[SessionInfo] = []
  seen: set[tuple[str, str]] = set()

  def add(items: Iterable[SessionInfo]) -> None:
    for s in items:
      key = (s.uin, s.cookies.get("skey") or s.cookies.get("p_skey", ""))
      if key in seen:
        continue
      seen.add(key)
      found.append(s)

  patterns = [
    "**/cookies.json",
    "**/session.json",
    "**/cookie.txt",
    "**/cookies.txt",
    "**/account.ini",
    "**/cookies.ini",
    "**/Cookies",
    "**/Cookies-journal",
  ]
  for pat in patterns:
    for p in root.glob(pat):
      if not p.is_file():
        continue
      if p.suffix.lower() == ".json":
        try:
          add(_from_json(p))
        except (json.JSONDecodeError, OSError):
          pass
      elif p.suffix.lower() in {".ini"} or p.name in {"account.ini", "cookies.ini"}:
        add(_from_ini(p))
      elif "cookie" in p.name.lower() or p.name == "Cookies":
        if p.suffix.lower() in {".db", ""} and p.name == "Cookies":
          add(_from_sqlite(p))
        else:
          add(_scan_text_file(p))

  # sqlite cookie DBs
  for p in root.glob("**/*.db"):
    if p.name.lower() in {"cookies", "cookies.db"} or "cookie" in p.name.lower():
      add(_from_sqlite(p))

  # broad text scan (limited)
  for p in root.rglob("*"):
    if not p.is_file() or p.stat().st_size > 2_000_000:
      continue
    if p.suffix.lower() in {".log", ".txt", ".json", ".ini", ".cfg", ".dat"}:
      add(_scan_text_file(p))

  return found


def pick_session(sessions: list[SessionInfo], uin: str) -> SessionInfo:
  target = _clean_uin(uin)
  for s in sessions:
    if s.uin == target:
      return s
  if len(sessions) == 1:
    return sessions[0]
  raise ValueError(f"未在数据目录找到 QQ {target} 的登录态，已发现: {[s.uin for s in sessions]}")
