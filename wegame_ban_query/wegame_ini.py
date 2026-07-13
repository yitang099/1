"""Parse WeGameTQ / data提取6 WeGameData ini (data/QQ号.ini)."""
from __future__ import annotations

import re
from dataclasses import dataclass

SECTION_RE = re.compile(r"^\[(\d{5,12})\]\s*$", re.M)
FIELD_RE = re.compile(r"^(0109_0001|0109_0038|0107_0001|0103_0001|0107_0088)\s*=\s*(.+)$", re.M)


@dataclass
class WeGameData:
  uin: str
  fields: dict[str, str]

  def hex_bytes(self, key: str) -> bytes:
    raw = self.fields.get(key, "")
    if not raw:
      return b""
    return bytes(int(x, 16) for x in raw.split())

  def ascii_field(self, key: str) -> str:
    data = self.hex_bytes(key)
    if not data:
      return ""
    return data.decode("ascii", errors="ignore").strip("\x00").strip()

  def clientkey_candidates(self) -> list[str]:
    out: list[str] = []
    blob = self.hex_bytes("0109_0038")
    if blob:
      out.append(blob.hex())
      try:
        s = blob.decode("latin-1").strip("\x00").strip()
        if len(s) >= 16:
          out.append(s)
      except Exception:
        pass
    short = self.hex_bytes("0109_0001")
    if short:
      out.append(short.hex())
    return [x for x in out if x]


def parse_wegame_data(text: str, uin: str | None = None) -> WeGameData | None:
  sec = SECTION_RE.search(text)
  qq = (sec.group(1) if sec else "") or re.sub(r"\D", "", uin or "")
  if not qq:
    return None

  fields: dict[str, str] = {}
  for m in FIELD_RE.finditer(text):
    fields[m.group(1)] = m.group(2).strip()

  if not fields:
    return None

  return WeGameData(uin=qq, fields=fields)


def cookies_from_wegame_data(data: WeGameData) -> dict[str, str]:
  skey = data.ascii_field("0107_0001") or data.ascii_field("0103_0001")
  cookies: dict[str, str] = {
    "uin": f"o{data.uin}",
    "p_uin": f"o{data.uin}",
  }
  if skey:
    cookies["skey"] = skey
  return cookies
