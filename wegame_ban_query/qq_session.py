"""Exchange QQ clientkey (CK) for session cookies via ptlogin."""
from __future__ import annotations

import re
from urllib.parse import quote, unquote

import requests

DEFAULT_UA = (
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

REFERER = "https://xui.ptlogin2.qq.com/"
GAMESAFE_HOME = "https://credit.gamesafe.qq.com/"
GAMESAFE_PAGE = "https://credit.gamesafe.qq.com/static/gamecredit_refactor/index.html"


def _cookies_dict(session: requests.Session) -> dict[str, str]:
  return {c.name: c.value for c in session.cookies}


def _has_session_key(cookies: dict[str, str]) -> bool:
  return bool(cookies.get("skey") or cookies.get("p_skey"))


def _parse_qlogin_cb(text: str) -> str | None:
  m = re.search(
    r"ptui_qlogin_CB\s*\(\s*'(\d+)'\s*,\s*'(https?://[^']+)'\s*,",
    text,
    re.I,
  )
  if m and m.group(1) == "0":
    return m.group(2).replace("\\/", "/")
  m = re.search(r"(https?://[^'\"\s]+check_sig[^'\"\s]*)", text)
  if m:
    return m.group(1).replace("\\/", "/")
  m = re.search(r"https?://[^\s'\"\\]+", text)
  if m and "check_sig" in m.group(0):
    return m.group(0).replace("\\/", "/")
  return None


def _fetch_pt_local_token(session: requests.Session, timeout: int) -> str:
  url = (
    "https://xui.ptlogin2.qq.com/cgi-bin/xlogin"
    "?appid=715030901&daid=127&style=20&pt_no_auth=0"
    f"&s_url={quote(GAMESAFE_PAGE, safe='')}"
  )
  resp = session.get(
    url,
    timeout=timeout,
    headers={"User-Agent": DEFAULT_UA, "Referer": GAMESAFE_HOME},
  )
  return resp.cookies.get("pt_local_token", "") or ""


def _follow_check_sig(
  session: requests.Session,
  sig_url: str,
  *,
  timeout: int,
) -> None:
  headers = {"User-Agent": DEFAULT_UA, "Referer": "https://ssl.ptlogin2.qq.com/"}
  resp = session.get(sig_url, timeout=timeout, allow_redirects=False, headers=headers)
  session.cookies.update(resp.cookies)

  for _ in range(5):
    if _has_session_key(_cookies_dict(session)):
      return
    loc = resp.headers.get("Location")
    if not loc:
      break
    if loc.startswith("//"):
      loc = "https:" + loc
    resp = session.get(loc, timeout=timeout, allow_redirects=False, headers=headers)
    session.cookies.update(resp.cookies)


def _try_jump(
  session: requests.Session,
  jump_url: str,
  headers: dict[str, str],
  *,
  timeout: int,
) -> bool:
  resp = session.get(jump_url, timeout=timeout, allow_redirects=False, headers=headers)
  session.cookies.update(resp.cookies)

  if _has_session_key(_cookies_dict(session)):
    return True

  sig_url = _parse_qlogin_cb(resp.text or "")
  if sig_url:
    _follow_check_sig(session, sig_url, timeout=timeout)
    if _has_session_key(_cookies_dict(session)):
      return True

  loc = resp.headers.get("Location")
  if loc:
    if loc.startswith("//"):
      loc = "https:" + loc
    _follow_check_sig(session, loc, timeout=timeout)
    if _has_session_key(_cookies_dict(session)):
      return True

  return _has_session_key(_cookies_dict(session))


def session_from_clientkey(
  uin: str,
  clientkey: str,
  *,
  timeout: int = 25,
) -> dict[str, str]:
  """Use saved clientkey + QQ to obtain skey (same ptlogin flow as CK tools)."""
  uin = re.sub(r"\D", "", uin)
  key = clientkey.strip()
  if not uin or not key:
    raise ValueError("QQ 或 clientkey 为空")

  session = requests.Session()
  pt_local_token = _fetch_pt_local_token(session, timeout)

  session.cookies.set("clientuin", uin)
  session.cookies.set("clientkey", key)
  if pt_local_token:
    session.cookies.set("pt_local_token", pt_local_token)

  u1 = quote(GAMESAFE_PAGE, safe="")
  tk_part = f"&pt_local_tk={pt_local_token}" if pt_local_token else ""
  base_headers = {
    "User-Agent": DEFAULT_UA,
    "Referer": REFERER,
    "Accept": "*/*",
    "Cookie": f"pt_local_token={pt_local_token}; clientuin={uin}; clientkey={key}",
  }

  jump_urls = [
  # 木马同款：ptlogin2 jump + clientuin/clientkey
    f"https://ptlogin2.qq.com/jump?clientuin={uin}&clientkey={key}",
    f"https://ssl.ptlogin2.qq.com/jump?clientuin={uin}&clientkey={key}&keyindex=9"
    f"&pt_aid=715030901&daid=127&u1={u1}{tk_part}&pt_3rd_aid=0&ptopt=1&style=40",
    f"https://ssl.ptlogin2.qq.com/jump?ptlang=1033&clientuin={uin}&clientkey={key}"
    f"&u1={u1}&keyindex=19{tk_part}",
    f"https://ssl.ptlogin2.qq.com/jump?clientuin={uin}&keyindex=9&pt_aid=549000912&daid=5"
    f"&u1={u1}{tk_part}&pt_3rd_aid=0&ptopt=1&style=40&has_onekey=1",
  ]

  for jump_url in jump_urls:
    try:
      if _try_jump(session, jump_url, base_headers, timeout=timeout):
        break
    except requests.RequestException:
      continue
  else:
    raise ValueError("clientkey 已失效或无法换取登录态，请重新获取 CK 后再试")

  try:
    session.get(
      GAMESAFE_HOME,
      timeout=timeout,
      headers={"User-Agent": DEFAULT_UA, "Referer": GAMESAFE_PAGE},
    )
  except requests.RequestException:
    pass

  cookies = _cookies_dict(session)
  cookies.setdefault("uin", f"o{uin}")
  cookies.setdefault("p_uin", f"o{uin}")
  cookies.setdefault("clientuin", uin)
  cookies.setdefault("clientkey", key)

  if not _has_session_key(cookies):
    raise ValueError("clientkey 已失效或无法换取登录态，请重新获取 CK 后再试")

  return cookies
