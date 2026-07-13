"""Get skey via local QQ (SSO) or saved WeGameData clientkey."""
from __future__ import annotations

import re
from urllib.parse import quote

import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # type: ignore[attr-defined]

DEFAULT_UA = (
  "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
  "(KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
)
REFERER = "https://xui.ptlogin2.qq.com/"
LOCAL_PORTS = list(range(4301, 4310)) + [4300]


def _cookies_dict(session: requests.Session) -> dict[str, str]:
  return {c.name: c.value for c in session.cookies}


def _has_skey(cookies: dict[str, str]) -> bool:
  return bool(cookies.get("skey") or cookies.get("p_skey"))


def _parse_check_sig(text: str) -> str | None:
  m = re.search(
    r"ptui_qlogin_CB\s*\(\s*'(\d+)'\s*,\s*'(https?://[^']+)'",
    text or "",
    re.I,
  )
  if m and m.group(1) == "0":
    return m.group(2).replace("\\/", "/")
  m = re.search(r"(https?://[^'\"\s]+check_sig[^'\"\s]*)", text or "")
  if m:
    return m.group(1).replace("\\/", "/")
  return None


def _normalize_clientkey(clientkey: str) -> str:
  key = clientkey.strip()
  if " " in key and re.fullmatch(r"[0-9A-Fa-f ]+", key):
    key = "".join(key.split())
  if re.fullmatch(r"[0-9A-Fa-f]+", key) and len(key) % 2 == 0:
    return key.lower()
  return key.encode("latin-1", errors="ignore").hex()


def _follow(session: requests.Session, url: str, timeout: int) -> None:
  headers = {"User-Agent": DEFAULT_UA, "Referer": "https://ssl.ptlogin2.qq.com/"}
  resp = session.get(url, timeout=timeout, allow_redirects=False, headers=headers)
  session.cookies.update(resp.cookies)
  for _ in range(6):
    if _has_skey(_cookies_dict(session)):
      return
    loc = resp.headers.get("Location")
    sig = _parse_check_sig(resp.text or "")
    nxt = None
    if sig:
      nxt = sig
    elif loc:
      nxt = ("https:" + loc) if loc.startswith("//") else loc
    if not nxt:
      break
    if "www.qq.com" in nxt and "check_sig" not in nxt:
      break
    resp = session.get(nxt, timeout=timeout, allow_redirects=False, headers=headers)
    session.cookies.update(resp.cookies)


def fetch_local_clientkey(uin: str, *, timeout: int = 3) -> str | None:
  """Get fresh clientkey from logged-in PC QQ (localhost.ptlogin2)."""
  uin = re.sub(r"\D", "", uin)
  session = requests.Session()
  session.headers.update({"User-Agent": DEFAULT_UA, "Referer": REFERER})
  try:
    r = session.get(
      "https://xui.ptlogin2.qq.com/cgi-bin/xlogin"
      "?appid=715030901&daid=73&style=20&pt_no_auth=1"
      f"&s_url={quote('https://qzs.qq.com/', safe='')}",
      timeout=timeout,
    )
  except requests.RequestException:
    return None
  pt_local_token = r.cookies.get("pt_local_token") or ""
  if not pt_local_token:
    return None

  for port in LOCAL_PORTS:
    try:
      st = session.get(
        f"https://localhost.ptlogin2.qq.com:{port}/pt_get_st"
        f"?clientuin={uin}&callback=ptui_getst_CB&pt_local_tk={pt_local_token}",
        timeout=timeout,
        headers={"Referer": REFERER, "Cookie": f"pt_local_token={pt_local_token}"},
        verify=False,
      )
      ck = st.cookies.get("clientkey") or session.cookies.get("clientkey")
      if ck:
        return ck
    except requests.RequestException:
      continue
  return None


def list_local_uins(*, timeout: int = 3) -> list[str]:
  session = requests.Session()
  session.headers.update({"User-Agent": DEFAULT_UA, "Referer": REFERER})
  try:
    r = session.get(
      "https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=715030901&daid=73&style=20&pt_no_auth=1"
      f"&s_url={quote('https://qzs.qq.com/', safe='')}",
      timeout=timeout,
    )
  except requests.RequestException:
    return []
  token = r.cookies.get("pt_local_token") or ""
  if not token:
    return []
  for port in LOCAL_PORTS:
    try:
      resp = session.get(
        f"https://localhost.ptlogin2.qq.com:{port}/pt_get_uins"
        f"?callback=ptui_getuins_CB&pt_local_tk={token}",
        timeout=timeout,
        headers={"Referer": REFERER, "Cookie": f"pt_local_token={token}"},
        verify=False,
      )
      return re.findall(r'"uin"\s*:\s*"(\d+)"', resp.text or "")
    except requests.RequestException:
      continue
  return []


def session_from_clientkey(
  uin: str,
  clientkey: str,
  *,
  timeout: int = 12,
) -> dict[str, str]:
  """Exact jump used by data提取6 / CK封号工具: keyindex=18."""
  uin = re.sub(r"\D", "", uin)
  key = _normalize_clientkey(clientkey)
  if not uin or not key:
    raise ValueError("QQ 或 clientkey 为空")

  session = requests.Session()
  cookie_hdr = f"clientuin={uin}; clientkey={key}"
  headers = {
    "User-Agent": DEFAULT_UA,
    "Referer": REFERER,
    "Cookie": cookie_hdr,
    "Accept": "*/*",
  }

  # 与 data提取6 字符串完全一致的拼接方式
  jump_urls = [
    f"https://ptlogin2.qq.com/jump?keyindex=18&clientuin={uin}&clientkey={key}",
    f"http://ptlogin2.qq.com/jump?keyindex=18&clientuin={uin}&clientkey={key}",
    f"https://ptlogin2.qq.com/jump?keyindex=18&clientuin={uin}&u1={quote('https://cf.qq.com/', safe='')}&clientkey={key}",
    f"https://ssl.ptlogin2.qq.com/jump?clientuin={uin}&clientkey={key}&u1={quote('https://credit.gamesafe.qq.com/', safe='')}",
  ]

  last_body = ""
  for jump in jump_urls:
    try:
      resp = session.get(jump, timeout=timeout, allow_redirects=False, headers=headers)
      session.cookies.update(resp.cookies)
      last_body = (resp.text or "")[:200]
      if _has_skey(_cookies_dict(session)):
        break
      sig = _parse_check_sig(resp.text or "")
      loc = resp.headers.get("Location")
      if sig:
        _follow(session, sig, timeout)
      elif loc and "check_sig" in loc:
        _follow(session, loc if not loc.startswith("//") else "https:" + loc, timeout)
      if _has_skey(_cookies_dict(session)):
        break
    except requests.RequestException:
      continue

  cookies = _cookies_dict(session)
  cookies.setdefault("uin", f"o{uin}")
  cookies.setdefault("p_uin", f"o{uin}")
  if not _has_skey(cookies):
    raise ValueError(
      "clientkey 换取 skey 失败。\n"
      "原因通常是：ini 已过期，或本机 QQ 未登录该号。\n"
      "解决：1) 用 PC QQ 登录该号后点「本地QQ刷新」；"
      "2) 或重新 data提取 生成 ini。\n"
      f"详情: {last_body[:100]}"
    )
  return cookies


def session_for_uin(uin: str, saved_clientkey: str = "", *, timeout: int = 12) -> dict[str, str]:
  """Prefer fresh local QQ clientkey; fall back to saved WeGameData key."""
  uin = re.sub(r"\D", "", uin)
  errors: list[str] = []

  local_ck = fetch_local_clientkey(uin, timeout=min(4, timeout))
  if local_ck:
    try:
      return session_from_clientkey(uin, local_ck, timeout=timeout)
    except ValueError as exc:
      errors.append(f"本地QQ CK失败: {exc}")

  if saved_clientkey:
    try:
      return session_from_clientkey(uin, saved_clientkey, timeout=timeout)
    except ValueError as exc:
      errors.append(str(exc))

  local_uins = list_local_uins(timeout=2)
  hint = ""
  if local_uins:
    hint = f"\n本机 QQ 已登录: {', '.join(local_uins)}（不含目标号则无法刷新）"
  elif not local_ck:
    hint = "\n未检测到本机 QQ 快捷登录（请先打开并登录 PC QQ）"

  raise ValueError(("；".join(errors) if errors else "无可用 clientkey") + hint)
