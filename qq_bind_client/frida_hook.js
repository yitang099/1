/**
 * QQ SMS bind capture — Java maps + native socket scan.
 */
'use strict';

function log(msg) {
  send({ type: 'log', msg: String(msg) });
}

function tryQQ(s, source) {
  if (!s) return;
  var t = String(s).trim();
  if (/^[1-9]\d{4,10}$/.test(t)) {
    send({ type: 'plain_qq', qq: t, source: source });
  }
}

function bytesToHex(arr) {
  if (!arr) return '';
  var out = [];
  for (var i = 0; i < arr.length; i++) {
    var b = (arr[i] & 0xff).toString(16);
    out.push(b.length === 1 ? '0' + b : b);
  }
  return out.join('');
}

function emitTlv(key, v) {
  try {
    var hex = '';
    if (v) {
      if (v.getClass && v.getClass().getName() === '[B') {
        hex = bytesToHex(Java.array('byte', v));
      } else {
        hex = String(v);
      }
    }
    send({ type: 'tlv543', key: String(key), hex: hex });
  } catch (e) {}
}

function isTlvKey(k) {
  if (k === null) return false;
  try {
    var cn = k.getClass().getName();
    if (cn === 'java.lang.Integer') {
      var n = Java.cast(k, Java.use('java.lang.Integer')).intValue();
      return n === 1347 || n === 543;
    }
    if (cn === 'java.lang.Short') {
      return Java.cast(k, Java.use('java.lang.Short')).shortValue() === 1347;
    }
    if (cn === 'java.lang.Long') {
      var l = Java.cast(k, Java.use('java.lang.Long')).longValue();
      return l === 1347 || l === 543;
    }
  } catch (e) {}
  var ks = String(k);
  return ks === '1347' || ks === '543';
}

function scanNativeBuffer(ptr, len, tag) {
  if (!ptr || len < 20 || len > 65536) return;
  try {
    var n = Math.min(len, 8192);
    var buf = Memory.readByteArray(ptr, n);
    var u8 = new Uint8Array(buf);
    var ascii = '';
    for (var i = 0; i < u8.length; i++) {
      var c = u8[i];
      ascii += c >= 32 && c < 127 ? String.fromCharCode(c) : '.';
    }
    var m = ascii.match(/key[_]?[Uu]in.{0,8}([1-9]\d{4,10})/);
    if (m) tryQQ(m[1], tag + '.ascii');
    for (var j = 0; j < u8.length - 10; j++) {
      if (u8[j] === 0xd2 && u8[j + 1] === 0x02) {
        var ln = u8[j + 2];
        if (ln >= 5 && ln <= 11 && j + 3 + ln <= u8.length) {
          var cand = '';
          for (var k = 0; k < ln; k++) cand += String.fromCharCode(u8[j + 3 + k]);
          tryQQ(cand, tag + '.pb42');
        }
      }
    }
  } catch (e2) {}
}

function hookNativeIO() {
  ['send', 'recv', 'sendto', 'recvfrom'].forEach(function (fn) {
    try {
      var p = Module.findExportByName('libc.so', fn);
      if (!p) return;
      Interceptor.attach(p, {
        onEnter: function (args) {
          this.fn = fn;
          this.buf = args[1];
          this.len = args[2] ? args[2].toInt32() : 0;
        },
        onLeave: function () {
          if (this.fn === 'recv' || this.fn === 'recvfrom') {
            scanNativeBuffer(this.buf, this.len, 'libc.' + this.fn);
          }
        },
      });
      log('native hooked libc.' + fn);
    } catch (e) {}
  });
}

function hookMapPutGet(MapClass, label) {
  try {
    var M = Java.use(MapClass);
    M.put.overload('java.lang.Object', 'java.lang.Object').implementation = function (k, v) {
      var ret = this.put(k, v);
      try {
        if (isTlvKey(k)) emitTlv(k, v);
      } catch (e) {}
      return ret;
    };
    M.get.overload('java.lang.Object').implementation = function (k) {
      var v = this.get(k);
      try {
        if (isTlvKey(k)) emitTlv(k, v);
      } catch (e) {}
      return v;
    };
    log('hooked ' + label);
  } catch (e) {}
}

function hookBundle() {
  try {
    var Bundle = Java.use('android.os.Bundle');
    Bundle.putString.implementation = function (key, val) {
      var r = this.putString(key, val);
      try {
        if (key && /uin/i.test(String(key))) tryQQ(val, 'Bundle.putString');
      } catch (e) {}
      return r;
    };
    Bundle.getString.implementation = function (key) {
      var v = this.getString(key);
      try {
        if (key && /uin/i.test(String(key))) tryQQ(v, 'Bundle.getString');
      } catch (e) {}
      return v;
    };
    log('hooked Bundle');
  } catch (e) {}
}

function hookOkHttp() {
  ['okhttp3.ResponseBody', 'com.android.okhttp.ResponseBody'].forEach(function (cls) {
    try {
      var RB = Java.use(cls);
      RB.string.implementation = function () {
        var s = this.string();
        try {
          var m = s.match(/"(?:str_)?key[_]?[Uu]in"\s*:\s*"?([1-9]\d{4,10})"?/);
          if (m) tryQQ(m[1], cls);
        } catch (e) {}
        return s;
      };
      log('hooked ' + cls);
    } catch (e) {}
  });
}

function hookKnownWtlogin() {
  var names = [
    'oicq.wlogin_sdk.request.WtloginHelper',
    'oicq.wlogin_sdk.request.WUserSigInfo',
    'oicq.wlogin_sdk.sharemem.WloginLoginInfo',
  ];
  names.forEach(function (name) {
    try {
      var C = Java.use(name);
      log('found class ' + name);
      var methods = C.class.getDeclaredMethods();
      for (var i = 0; i < methods.length; i++) {
        var mn = methods[i].getName();
        if (!/uin|Uin|TLV|Tlv|tlv/i.test(mn)) continue;
        if (!C[mn]) continue;
        C[mn].overloads.forEach(function (ol) {
          ol.implementation = (function (n, m) {
            return function () {
              var r = this[m].apply(this, arguments);
              try {
                if (/uin/i.test(m)) tryQQ(r, n + '.' + m);
                else if (r && r.getClass && r.getClass().getName() === '[B') emitTlv(m, r);
              } catch (e) {}
              return r;
            };
          })(name, mn);
        });
        log('hooked ' + name + '.' + mn);
      }
    } catch (e) {}
  });
}

function hookGetKeyUin() {
  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      if (name.indexOf('oicq') === -1 && name.indexOf('wtlogin') === -1 && name.indexOf('WtLogin') === -1) return;
      if (name.indexOf('$') !== -1) return;
      try {
        var C = Java.use(name);
        var methods = C.class.getDeclaredMethods();
        for (var i = 0; i < methods.length; i++) {
          var mn = methods[i].getName();
          if (mn === 'getKeyUin' || mn === 'getUin' || mn === 'getStrKeyUin' || mn === 'getKeyUinString') {
            C[mn].overloads.forEach(function (ol) {
              ol.implementation = (function (cls, m) {
                return function () {
                  var r = this[m].apply(this, arguments);
                  tryQQ(r, cls + '.' + m);
                  return r;
                };
              })(name, mn);
            });
            log('hooked ' + name + '.' + mn);
          }
        }
      } catch (e2) {}
    },
    onComplete: function () {
      log('class scan done — submit SMS code now');
      send({ type: 'ready', stage: 'scan' });
    },
  });
}

function installHooks() {
  var mode = typeof __HOOK_MODE__ === 'undefined' ? 'full' : String(__HOOK_MODE__);
  log('mode=' + mode + ' pid=' + Process.id);
  hookNativeIO();
  if (mode !== 'light') {
    hookMapPutGet('java.util.HashMap', 'HashMap');
    hookMapPutGet('java.util.concurrent.ConcurrentHashMap', 'ConcurrentHashMap');
    hookMapPutGet('java.util.LinkedHashMap', 'LinkedHashMap');
    hookMapPutGet('android.util.ArrayMap', 'ArrayMap');
    hookBundle();
    hookOkHttp();
    hookKnownWtlogin();
  }
  send({ type: 'ready', stage: 'maps' });
  hookGetKeyUin();
}

var maxJavaWait = 8;
if (typeof __JAVA_WAIT_SEC__ !== 'undefined' && __JAVA_WAIT_SEC__ > 0) {
  maxJavaWait = __JAVA_WAIT_SEC__;
}

function tryInstallHooks() {
  if (typeof Java === 'undefined') {
    hookNativeIO();
    send({ type: 'ready', stage: 'native-only' });
    return true;
  }
  if (Java.available) {
    Java.perform(installHooks);
    return true;
  }
  try {
    Java.perform(installHooks);
    return true;
  } catch (e) {
    log('Java.perform: ' + e);
  }
  return false;
}

function waitForJava(attempt) {
  if (tryInstallHooks()) return;
  if (attempt >= maxJavaWait) {
    hookNativeIO();
    send({ type: 'no_java', pid: Process.id });
    log('no Java — native IO only pid=' + Process.id);
    return;
  }
  if (attempt === 0) log('waiting Java max=' + maxJavaWait + 's');
  setTimeout(function () {
    waitForJava(attempt + 1);
  }, 1000);
}

log('frida_hook.js loaded');
waitForJava(0);
