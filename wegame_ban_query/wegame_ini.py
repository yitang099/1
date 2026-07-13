"""Parse WeGameTQ / data提取6 WeGameData ini (data/QQ号.ini)."""
from __future__ import annotations

import re
from dataclasses import dataclass

SECTION_RE = re.compile(r"^\[(\d{5,12})\]\s*$", re.M)
FIELD_RE = re.compile(
  r"^(0109_0001|0109_0038|0107_0001|0103_0001|0107_0088)\s*=\s*(.+)$",
  re.M,
)
SKEY_RE = re.compile(r"^@[A-Za-z0-9_-]{6,}$")


@dataclass
class WeGameData:
  uin: str
  fields: dict[str, str]

  def hex_bytes(self, key: str) -> bytes:
    raw = self.fields.get(key, "")
    if not raw:
      return b""
    parts = raw.replace(",", " ").split()
    return bytes(int(x, 16) for x in parts if re.fullmatch(r"[0-9A-Fa-f]{1,2}", x))

  def clientkey_hex(self) -> str:
    """0109_0038 is the 56-byte clientkey used by CK工具 (keyindex=18)."""
    blob = self.hex_bytes("0109_0038")
    if blob:
      return blob.hex()
    blob = self.hex_bytes("0109_0001")
    return blob.hex() if blob else ""

  def maybe_skey(self) -> str:
    """Only treat 0107_0001 as skey when it looks like a real QQ skey (@...)."""
    data = self.hex_bytes("0107_0001") or self.hex_bytes("0103_0001")
    if not data:
      return ""
    try:
      text = data.decode("ascii")
    except UnicodeDecodeError:
      return ""
    if SKEY_RE.match(text):
      return text
    return ""


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
