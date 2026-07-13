"""Exchange QQ clientkey (CK) for session cookies via ptlogin."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import requests

DEFAULT_UA = (
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

GAMESAFE_URL = "https://credit.gamesafe.qq.com/"


def _cookies_dict(session: requests.Session) -> dict[str, str]:
  out: dict[str, str] = {}
  for c in session.cookies:
    out[c.name] = c.value
  return out


def _pick_cookie(cookies: dict[str, str], *names: str) -> str:
  for name in names:
    if cookies.get(name):
      return cookies[name]
  return ""


def session_from_clientkey(
  uin: str,
  clientkey: str,
  *,
  timeout: int = 25,
) -> dict[str, str]:
  """Use saved clientkey + QQ to obtain skey cookies (same flow as CK tools)."""
  uin = re.sub(r"\D", "", uin)
  key = clientkey.strip()
  if not uin or not key:
    raise ValueError("QQ 或 clientkey 为空")

  session = requests.Session()
  session.headers.update({"User-Agent": DEFAULT_UA})

  jump_url = (
    "https://ssl.ptlogin2.qq.com/jump"
    f"?ptlang=1033&clientuin={uin}&clientkey={quote(key, safe='')}"
    f"&u1={quote(GAMESAFE_URL, safe='')}&keyindex=19"
  )
  resp = session.get(jump_url, timeout=timeout, allow_redirects=False)
  _collect_jump_cookies(session, resp)

  for _ in range(6):
    if _pick_cookie(_cookies_dict(session), "skey", "p_skey"):
      break
    loc = resp.headers.get("Location")
    if not loc:
      break
    if loc.startswith("//"):
      loc = "https:" + loc
    resp = session.get(loc, timeout=timeout, allow_redirects=False)
    _collect_jump_cookies(session, resp)

  cookies = _cookies_dict(session)
  cookies.setdefault("uin", f"o{uin}")
  cookies.setdefault("p_uin", f"o{uin}")
  cookies.setdefault("clientuin", uin)
  cookies.setdefault("clientkey", key)

  if not _pick_cookie(cookies, "skey", "p_skey"):
    raise ValueError("clientkey 已失效或无法换取登录态，请重新获取 CK 后再试")

  return cookies


def _collect_jump_cookies(session: requests.Session, resp: requests.Response) -> None:
  session.cookies.update(resp.cookies)
  text = resp.text or ""
  m = re.search(r"ptsigx=([0-9a-fA-F]+)", text)
  if not m:
    return
  sig_url_m = re.search(r"(https?://[^'\"\s]+check_sig[^'\"\s]*)", text)
  if not sig_url_m:
    return
  try:
    sig_resp = session.get(sig_url_m.group(1), timeout=20, allow_redirects=False)
    session.cookies.update(sig_resp.cookies)
    loc = sig_resp.headers.get("Location")
    if loc:
      if loc.startswith("//"):
        loc = "https:" + loc
      follow = session.get(loc, timeout=20, allow_redirects=False)
      session.cookies.update(follow.cookies)
  except requests.RequestException:
    pass
