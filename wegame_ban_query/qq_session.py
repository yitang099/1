"""Exchange QQ clientkey for skey via ptlogin (matches CK tool keyindex=18)."""
from __future__ import annotations

import re
from urllib.parse import quote

import requests

DEFAULT_UA = (
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REFERER = "https://xui.ptlogin2.qq.com/"


def _cookies_dict(session: requests.Session) -> dict[str, str]:
  return {c.name: c.value for c in session.cookies}


def _has_skey(cookies: dict[str, str]) -> bool:
  sk = cookies.get("skey") or cookies.get("p_skey") or ""
  return bool(sk)


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


def _follow(session: requests.Session, url: str, timeout: int) -> None:
  headers = {"User-Agent": DEFAULT_UA, "Referer": "https://ssl.ptlogin2.qq.com/"}
  resp = session.get(url, timeout=timeout, allow_redirects=False, headers=headers)
  session.cookies.update(resp.cookies)
  for _ in range(5):
    if _has_skey(_cookies_dict(session)):
      return
    loc = resp.headers.get("Location")
    if not loc:
      body_url = _parse_check_sig(resp.text or "")
      if body_url and body_url != url:
        resp = session.get(body_url, timeout=timeout, allow_redirects=False, headers=headers)
        session.cookies.update(resp.cookies)
        continue
      break
    if loc.startswith("//"):
      loc = "https:" + loc
    resp = session.get(loc, timeout=timeout, allow_redirects=False, headers=headers)
    session.cookies.update(resp.cookies)


def session_from_clientkey(
  uin: str,
  clientkey: str,
  *,
  timeout: int = 12,
) -> dict[str, str]:
  """ptlogin jump with keyindex=18 (same as CK获取以及封号.exe)."""
  uin = re.sub(r"\D", "", uin)
  key = clientkey.strip().lower()
  if not uin or not key:
    raise ValueError("QQ 或 clientkey 为空")

  # WeGameData 0109_0038 is raw bytes; URL needs hex without spaces
  if " " in key:
    key = "".join(key.split())
  if re.fullmatch(r"[0-9a-fA-F]+", key) and len(key) % 2 == 0:
    pass  # already hex
  else:
    key = key.encode("latin-1", errors="ignore").hex()

  session = requests.Session()
  session.headers.update({"User-Agent": DEFAULT_UA})
  cookie_hdr = f"clientuin={uin}; clientkey={key}"

  jump_urls = [
    f"http://ptlogin2.qq.com/jump?keyindex=18&clientuin={uin}&clientkey={key}",
    f"https://ptlogin2.qq.com/jump?keyindex=18&clientuin={uin}&clientkey={key}",
    f"https://ssl.ptlogin2.qq.com/jump?clientuin={uin}&clientkey={key}",
    (
      "https://ssl.ptlogin2.qq.com/jump"
      f"?clientuin={uin}&clientkey={key}"
      "&aid=7000201&keyindex=1"
      f"&u1={quote('https://credit.gamesafe.qq.com/', safe='')}"
    ),
  ]

  last_body = ""
  for jump in jump_urls:
    try:
      resp = session.get(
        jump,
        timeout=timeout,
        allow_redirects=False,
        headers={"Referer": REFERER, "Cookie": cookie_hdr, "User-Agent": DEFAULT_UA},
      )
      session.cookies.update(resp.cookies)
      last_body = (resp.text or "")[:300]
      if _has_skey(_cookies_dict(session)):
        break
      sig = _parse_check_sig(resp.text or "")
      if sig:
        _follow(session, sig, timeout)
      elif resp.headers.get("Location"):
        loc = resp.headers["Location"]
        if loc.startswith("//"):
          loc = "https:" + loc
        # www.qq.com alone means login failed
        if "www.qq.com" not in loc or "check_sig" in loc:
          _follow(session, loc, timeout)
      if _has_skey(_cookies_dict(session)):
        break
    except requests.RequestException:
      continue

  cookies = _cookies_dict(session)
  cookies.setdefault("uin", f"o{uin}")
  cookies.setdefault("p_uin", f"o{uin}")
  cookies["clientuin"] = uin
  cookies["clientkey"] = key

  if not _has_skey(cookies):
    raise ValueError(
      "clientkey 换取 skey 失败（data 可能过期）。"
      f"请重新用 data提取 生成 ini。详情: {last_body[:120]}"
    )
  return cookies
