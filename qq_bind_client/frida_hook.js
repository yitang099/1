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

function scanObjectForUin(obj, tag) {
  if (!obj) return;
  try {
    var ts = String(obj.toString());
    var m = ts.match(/(?:uin|Uin|saltUin|keyUin|key_uin)[=: \"]+([1-9]\d{4,10})/i);
    if (m) tryQQ(m[1], tag + '.toString');
    var cls = obj.getClass();
    var fields = cls.getDeclaredFields();
    for (var i = 0; i < fields.length; i++) {
      fields[i].setAccessible(true);
      var fname = fields[i].getName();
      if (!/uin|qq|account|salt/i.test(fname)) continue;
      var val = fields[i].get(obj);
      if (val === null) continue;
      var cn = val.getClass ? val.getClass().getName() : '';
      if (cn === '[B') {
        try {
          var arr = Java.array('byte', val);
          var ascii = '';
          for (var b = 0; b < Math.min(arr.length, 64); b++) {
            var c = arr[b] & 0xff;
            ascii += c >= 32 && c < 127 ? String.fromCharCode(c) : '.';
          }
          var bm = ascii.match(/([1-9]\d{4,10})/);
          if (bm) tryQQ(bm[1], tag + '.' + fname + '.bytes');
        } catch (e) {}
      } else {
        tryQQ(String(val), tag + '.' + fname);
      }
    }
  } catch (e) {}
}

function scanCollection(coll, tag) {
  if (!coll) return;
  var found = [];
  try {
    var List = Java.use('java.util.List');
    var list = Java.cast(coll, List);
    var size = list.size();
    for (var i = 0; i < size; i++) {
      scanObjectForUin(list.get(i), tag + '[' + i + ']');
      found.push(list.get(i));
    }
    if (size > 0) {
      send({ type: 'nt_account_list', size: size, tag: tag });
    }
    return;
  } catch (e) {}
  try {
    var iter = coll.iterator();
    var idx = 0;
    while (iter.hasNext()) {
      scanObjectForUin(iter.next(), tag + '[' + idx + ']');
      idx++;
    }
    if (idx > 0) send({ type: 'nt_account_list', size: idx, tag: tag });
  } catch (e2) {}
}

function hookNtMethod(C, mn, clsName) {
  if (!C[mn]) return;
  C[mn].overloads.forEach(function (ol) {
    ol.implementation = (function (methodName, overload) {
      return function () {
        var args = [].slice.call(arguments);
        for (var i = 0; i < args.length; i++) {
          scanObjectForUin(args[i], clsName + '.' + methodName + '.arg' + i);
          scanCollection(args[i], clsName + '.' + methodName + '.list' + i);
        }
        var ret = overload.apply(this, arguments);
        scanObjectForUin(ret, clsName + '.' + methodName + '.ret');
        scanCollection(ret, clsName + '.' + methodName + '.ret');
        if (/selectAccount|onAccountSelect|chooseAccount/i.test(methodName)) {
          log('NTLogin ' + methodName + ' called');
        }
        return ret;
      };
    })(mn, ol);
  });
  log('hooked NT ' + clsName + '.' + mn);
}

function hookNTLogin() {
  var classHints = ['PhoneSmsLogin', 'SaltUin', 'AccountInfo', 'NTLogin', 'SmsLogin', 'PhoneLogin'];
  var methodHints = [
    'SaltUin', 'saltUin', 'GetSaltUin', 'selectAccount', 'MultiAccount',
    'onGetSaltUin', 'loginByCoroutine', 'requestLogin', 'onSuccess',
  ];
  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      if (name.indexOf('tencent') === -1 && name.indexOf('qq') === -1 && name.indexOf('mobile') === -1) return;
      var hit = false;
      for (var t = 0; t < classHints.length; t++) {
        if (name.indexOf(classHints[t]) !== -1) {
          hit = true;
          break;
        }
      }
      if (!hit) return;
      try {
        var C = Java.use(name);
        var methods = C.class.getDeclaredMethods();
        for (var i = 0; i < methods.length; i++) {
          var mn = methods[i].getName();
          var should = /uin/i.test(mn);
          if (!should) {
            for (var h = 0; h < methodHints.length; h++) {
              if (mn.indexOf(methodHints[h]) !== -1) {
                should = true;
                break;
              }
            }
          }
          if (should) hookNtMethod(C, mn, name);
        }
      } catch (e) {}
    },
    onComplete: function () {
      log('NTLogin class scan done');
    },
  });
}

function hookJsonParse() {
  try {
    var JSONObject = Java.use('org.json.JSONObject');
    JSONObject.getString.implementation = function (key) {
      var v = this.getString(key);
      try {
        if (key && /uin/i.test(String(key))) tryQQ(v, 'JSONObject.' + key);
      } catch (e) {}
      return v;
    };
    JSONObject.optString.overload('java.lang.String').implementation = function (key) {
      var v = this.optString(key);
      try {
        if (key && /uin/i.test(String(key))) tryQQ(v, 'JSONObject.opt.' + key);
      } catch (e) {}
      return v;
    };
    log('hooked JSONObject uin getters');
  } catch (e) {}
  ['com.google.gson.Gson', 'com.alibaba.fastjson.JSON'].forEach(function (cls) {
    try {
      var G = Java.use(cls);
      if (!G.fromJson) return;
      G.fromJson.overloads.forEach(function (ol) {
        ol.implementation = function () {
          var r = ol.apply(this, arguments);
          try {
            if (arguments.length > 0) {
              var raw = String(arguments[0]);
              var m = raw.match(/"(?:saltUin|key_uin|keyUin|uin)"\s*:\s*"?([1-9]\d{4,10})"?/i);
              if (m) tryQQ(m[1], cls + '.fromJson');
            }
            scanObjectForUin(r, cls + '.fromJson');
          } catch (e) {}
          return r;
        };
      });
      log('hooked ' + cls);
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
    hookNTLogin();
    hookJsonParse();
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
