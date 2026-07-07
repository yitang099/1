"""Parse QQ SMS bind payloads for plain QQ (key_uin)."""
from __future__ import annotations

import re
from dataclasses import dataclass


QQ_RE = re.compile(r"^[1-9]\d{4,10}$")


@dataclass
class UinAccount:
    key_uin: str
    mask_uin: str = ""
    nick: str = ""


@dataclass
class ParseResult:
    accounts: list[UinAccount]
    parse_path: str
    source: str


def _read_varint(data: bytes, i: int) -> tuple[int, int]:
    shift = 0
    value = 0
    while i < len(data):
        b = data[i]
        i += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, i
        shift += 7
        if shift > 63:
            break
    raise ValueError("bad varint")


def _walk_strings(data: bytes) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(data):
        try:
            tag, i = _read_varint(data, i)
        except ValueError:
            break
        wire = tag & 7
        field = tag >> 3
        if wire == 0:
            _, i = _read_varint(data, i)
        elif wire == 1:
            i += 8
        elif wire == 2:
            ln, i = _read_varint(data, i)
            chunk = data[i : i + ln]
            i += ln
            if field == 42:
                try:
                    s = chunk.decode("utf-8")
                    if QQ_RE.match(s):
                        out.append(s)
                except UnicodeDecodeError:
                    pass
            else:
                try:
                    s = chunk.decode("utf-8")
                    if QQ_RE.match(s):
                        out.append(s)
                except UnicodeDecodeError:
                    out.extend(_walk_strings(chunk))
        elif wire == 5:
            i += 4
        else:
            break
    return out


def normalize_input(raw: bytes) -> bytes:
    return raw


def parse_auto(raw: bytes) -> ParseResult:
    accounts: list[UinAccount] = []
    seen: set[str] = set()
    for qq in _walk_strings(raw):
        if qq not in seen:
            seen.add(qq)
            accounts.append(UinAccount(key_uin=qq))
    path = "protobuf_walk"
    if not accounts:
        text = raw.decode("utf-8", errors="ignore")
        for m in re.finditer(r"\b([1-9]\d{4,10})\b", text):
            qq = m.group(1)
            if qq not in seen:
                seen.add(qq)
                accounts.append(UinAccount(key_uin=qq))
        path = "regex_fallback"
    return ParseResult(accounts=accounts, parse_path=path, source="bytes")


def print_human(result: ParseResult) -> None:
    if not result.accounts:
        print("no accounts parsed")
        return
    for i, acc in enumerate(result.accounts, 1):
        print(f"[{i}] plain_qq={acc.key_uin} path={result.parse_path}")


def build_self_test_payload() -> bytes:
    # minimal protobuf: field 42 string "10001"
    qq = b"10001"
    tag = bytes([0xD2, 0x02])  # field 42, wire type 2
    ln = bytes([len(qq)])
    return tag + ln + qq


def run_self_test() -> None:
    raw = build_self_test_payload()
    result = parse_auto(raw)
    assert result.accounts and result.accounts[0].key_uin == "10001", result
    print("parser self-test OK")
