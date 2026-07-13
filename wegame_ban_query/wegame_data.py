"""Parse cookies / clientkey from user-provided WeGame data folder."""
from __future__ import annotations

import configparser
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from qq_session import session_from_clientkey

COOKIE_KEYS = {
  "uin", "p_uin", "skey", "p_skey", "ptcz", "RK", "pt_login_sig",
  "superuin", "supertoken", "superkey", "clientkey", "qq_domain_video_guid_verify",
}

QQ_FILE_RE = re.compile(r"^\d{5,12}$")
CLIENTKEY_RE = re.compile(
  r"(?:client[_-]?key|clientkey|ck)[\"'\s:=]+([A-Za-z0-9_\-]{32,512})",
  re.I,
)
HEX_KEY_RE = re.compile(r"\b([0-9a-fA-F]{56,256})\b")


@dataclass
class SessionInfo:
  uin: str
  cookies: dict[str, str]
  source: str
  kind: str = "cookie"  # cookie | clientkey
  clientkey: str = ""

  def materialize(self) -> "SessionInfo":
    """Resolve clientkey to cookies when needed."""
    if self.kind != "clientkey":
      return self
    if self.cookies.get("skey") or self.cookies.get("p_skey"):
      return self
    if not self.clientkey:
      raise ValueError(f"QQ {self.uin} 的 clientkey 为空")
    cookies = session_from_clientkey(self.uin, self.clientkey)
    return SessionInfo(
      uin=self.uin,
      cookies=cookies,
      source=self.source,
      kind="clientkey",
      clientkey=self.clientkey,
    )


def _clean_uin(val: str) -> str:
  return re.sub(r"\D", "", val or "")


def _merge_cookies(base: dict[str, str], extra: dict[str, str]) -> dict[str, str]:
  out = dict(base)
  for k, v in extra.items():
    if v:
      out[k] = v
  return out


def _read_text(path: Path) -> str:
  raw = path.read_bytes()
  for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"):
    try:
      return raw.decode(enc)
    except UnicodeDecodeError:
      continue
  return raw.decode("utf-8", errors="replace")


def _extract_clientkey(text: str) -> str | None:
  m = CLIENTKEY_RE.search(text)
  if m:
    return m.group(1).strip()
  m = HEX_KEY_RE.search(text)
  if m:
    return m.group(1).strip()
  t = text.strip()
  if 32 <= len(t) <= 512 and re.fullmatch(r"[A-Za-z0-9_\-]+", t):
    return t
  return None


def _session_from_clientkey_file(path: Path, uin: str | None = None) -> SessionInfo | None:
  qq = _clean_uin(uin or path.name)
  if not qq:
    return None
  try:
    text = _read_text(path)
  except OSError:
    return None
  key = _extract_clientkey(text)
  if not key:
    return None
  return SessionInfo(
    uin=qq,
    cookies={"uin": f"o{qq}", "clientuin": qq, "clientkey": key},
    source=str(path),
    kind="clientkey",
    clientkey=key,
  )


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
    ck = items.get("clientkey") or items.get("client_key") or items.get("ck")
    if ck:
      out.append(SessionInfo(
        uin=uin,
        cookies={"uin": f"o{uin}", "clientuin": uin, "clientkey": ck},
        source=str(path),
        kind="clientkey",
        clientkey=ck,
      ))
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
    elif "clientkey" in data or "client_key" in data or "ck" in data:
      uin = _clean_uin(str(data.get("uin") or data.get("qq") or ""))
      ck = str(data.get("clientkey") or data.get("client_key") or data.get("ck") or "")
      if uin and ck:
        out.append(SessionInfo(
          uin=uin,
          cookies={"uin": f"o{uin}", "clientuin": uin, "clientkey": ck},
          source=str(path),
          kind="clientkey",
          clientkey=ck,
        ))
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
    text = _read_text(path)
  except OSError:
    return []

  uin = _clean_uin(path.stem) if QQ_FILE_RE.match(path.stem) else ""
  if not uin:
    cookies = _parse_cookie_text(text)
    uin = _clean_uin(cookies.get("uin") or cookies.get("p_uin") or "")
    m = re.search(r"(?:qq|uin)[\"']?\s*[:=]\s*[\"']?(\d{5,12})", text, re.I)
    if not uin and m:
      uin = m.group(1)

  if uin:
    ck = _extract_clientkey(text)
    if ck:
      return [SessionInfo(
        uin=uin,
        cookies={"uin": f"o{uin}", "clientuin": uin, "clientkey": ck},
        source=str(path),
        kind="clientkey",
        clientkey=ck,
      )]

  if "skey" not in text.lower() and "p_skey" not in text.lower():
    return []
  cookies = _parse_cookie_text(text)
  uin = _clean_uin(cookies.get("uin") or cookies.get("p_uin") or uin)
  if uin and (cookies.get("skey") or cookies.get("p_skey")):
    return [SessionInfo(uin=uin, cookies=cookies, source=str(path))]
  return []


def _scan_qq_named_file(path: Path) -> list[SessionInfo]:
  if not path.is_file():
    return []
  if not QQ_FILE_RE.match(path.name) and not QQ_FILE_RE.match(path.stem):
    return []
  if path.stat().st_size > 5_000_000:
    return []
  item = _session_from_clientkey_file(path)
  return [item] if item else []


def discover_sessions(data_dir: str | Path) -> list[SessionInfo]:
  root = Path(data_dir)
  if not root.is_dir():
    raise FileNotFoundError(f"目录不存在: {root}")

  found: list[SessionInfo] = []
  seen: set[tuple[str, str]] = set()

  def add(items: Iterable[SessionInfo]) -> None:
    for s in items:
      token = s.cookies.get("skey") or s.cookies.get("p_skey") or s.clientkey or ""
      key = (s.uin, token[:24])
      if key in seen:
        continue
      seen.add(key)
      found.append(s)

  # QQ 号文件（CK 缓存，与木马同款：文件名即 QQ 号）
  for p in root.iterdir():
    if p.is_file():
      add(_scan_qq_named_file(p))

  patterns = [
    "**/cookies.json",
    "**/session.json",
    "**/cookie.txt",
    "**/cookies.txt",
    "**/account.ini",
    "**/cookies.ini",
    "**/Cookies",
  ]
  for pat in patterns:
    for p in root.glob(pat):
      if not p.is_file():
        continue
      if p.suffix.lower() == ".json":
        try:
          add(_from_json(p))
        except (json.JSONDecodeError, OSError, ValueError):
          pass
      elif p.suffix.lower() in {".ini"} or p.name in {"account.ini", "cookies.ini"}:
        try:
          add(_from_ini(p))
        except ValueError:
          pass
      elif "cookie" in p.name.lower() or p.name == "Cookies":
        if p.name == "Cookies":
          add(_from_sqlite(p))
        else:
          add(_scan_text_file(p))

  for p in root.glob("**/*.db"):
    if "cookie" in p.name.lower():
      add(_from_sqlite(p))

  for p in root.rglob("*"):
    if not p.is_file() or p.stat().st_size > 2_000_000:
      continue
    if QQ_FILE_RE.match(p.name) or QQ_FILE_RE.match(p.stem):
      add(_scan_qq_named_file(p))
      continue
    if p.suffix.lower() in {".log", ".txt", ".json", ".ini", ".cfg", ".dat", ".ck"}:
      try:
        add(_scan_text_file(p))
      except ValueError:
        pass

  return found


def pick_session(sessions: list[SessionInfo], uin: str) -> SessionInfo:
  target = _clean_uin(uin)
  for s in sessions:
    if s.uin == target:
      return s
  if len(sessions) == 1:
    return sessions[0]
  raise ValueError(f"未找到 QQ {target} 的登录数据。data 里需有同名文件（如 {target}）且含有效 clientkey")


def resolve_session(data_dir: str | Path, uin: str) -> SessionInfo:
  """Scan folder and resolve session; exchange clientkey on demand."""
  sessions = discover_sessions(data_dir)
  target = _clean_uin(uin)
  session: SessionInfo | None = None
  try:
    session = pick_session(sessions, target)
  except ValueError:
    session = None

  if session is None:
    root = Path(data_dir)
    for name in (target, f"{target}.txt", f"{target}.ck", f"{target}.ini"):
      p = root / name
      if p.is_file():
        session = _session_from_clientkey_file(p, target)
        if session:
          break

  if session is None:
    raise ValueError(
      f"未找到 QQ {target} 的数据文件。请在 data 文件夹放入名为「{target}」的 CK 文件"
    )

  return session.materialize()
