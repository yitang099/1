/**
 * QQ SMS bind -> plain QQ (key_uin / TLV 0x543).
 * Modes: keyonly (default) | full | light
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
      } else if (v.getClass && v.getClass().getName() === 'java.lang.String') {
        hex = String(v);
      } else {
        try {
          if (v.toByteArray) {
            hex = bytesToHex(Java.array('byte', v.toByteArray()));
          } else {
            hex = String(v);
          }
        } catch (e2) {
          hex = String(v);
        }
      }
    }
    send({ type: 'tlv543', key: String(key), hex: hex, java: v ? String(v) : '' });
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
      var s = Java.cast(k, Java.use('java.lang.Short')).shortValue();
      return s === 1347 || s === 543;
    }
    if (cn === 'java.lang.Long') {
      var l = Java.cast(k, Java.use('java.lang.Long')).longValue();
      return l === 1347 || l === 543;
    }
  } catch (e) {}
  var ks = String(k);
  return ks === '1347' || ks === '543' || ks === '0x543';
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
    return true;
  } catch (e) {
    log(label + ' skip: ' + e);
    return false;
  }
}

function hookOkHttp() {
  var bodies = ['okhttp3.ResponseBody', 'com.android.okhttp.ResponseBody'];
  for (var i = 0; i < bodies.length; i++) {
    try {
      var ResponseBody = Java.use(bodies[i]);
      ResponseBody.string.implementation = function () {
        var s = this.string();
        try {
          if (s.indexOf('key_uin') !== -1 || s.indexOf('keyUin') !== -1 || s.indexOf('str_key_uin') !== -1) {
            var m = s.match(/"(?:str_)?key[_]?[Uu]in"\s*:\s*"?([1-9]\d{4,10})"?/);
            if (m) tryQQ(m[1], bodies[i]);
          }
        } catch (e) {}
        return s;
      };
      log('hooked ' + bodies[i] + '.string');
    } catch (e) {}
  }
}

function hookJsonObject() {
  try {
    var JSONObject = Java.use('org.json.JSONObject');
    JSONObject.getString.implementation = function (key) {
      var v = this.getString(key);
      try {
        if (key && String(key).toLowerCase().indexOf('uin') !== -1) tryQQ(v, 'JSONObject.getString');
      } catch (e) {}
      return v;
    };
    log('hooked JSONObject.getString');
  } catch (e) {}
}

function hookUserSigInfo() {
  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      if (name.indexOf('SigInfo') === -1 && name.indexOf('siginfo') === -1) return;
      if (name.indexOf('oicq') === -1 && name.indexOf('wlogin') === -1 && name.indexOf('WUser') === -1) return;
      if (name.indexOf('$') !== -1) return;
      try {
        var C = Java.use(name);
        var methods = C.class.getDeclaredMethods();
        for (var i = 0; i < methods.length; i++) {
          var mn = methods[i].getName();
          if (
            mn.indexOf('KeyUin') !== -1 ||
            mn.indexOf('keyUin') !== -1 ||
            mn.indexOf('TLV') !== -1 ||
            mn.indexOf('Tlv') !== -1
          ) {
            if (!C[mn]) continue;
            var overloads = C[mn].overloads;
            for (var j = 0; j < overloads.length; j++) {
              overloads[j].implementation = (function (cls, methodName) {
                return function () {
                  var r = this[methodName].apply(this, arguments);
                  try {
                    if (methodName.indexOf('Uin') !== -1) tryQQ(r, cls + '.' + methodName);
                    else if (r && r.getClass && r.getClass().getName() === '[B') emitTlv(methodName, r);
                  } catch (e) {}
                  return r;
                };
              })(name, mn);
            }
            log('hooked ' + name + '.' + mn);
          }
        }
      } catch (e2) {}
    },
    onComplete: function () {
      log('SigInfo scan done');
    },
  });
}

function hookGetKeyUin() {
  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      var hit =
        name.indexOf('oicq') !== -1 ||
        name.indexOf('wtlogin') !== -1 ||
        name.indexOf('WtLogin') !== -1 ||
        name.indexOf('AccountInfo') !== -1 ||
        name.indexOf('UinInfo') !== -1;
      if (!hit) return;
      if (name.indexOf('$') !== -1) return;
      try {
        var C = Java.use(name);
        var methods = C.class.getDeclaredMethods();
        for (var i = 0; i < methods.length; i++) {
          var mname = methods[i].getName();
          if (
            mname === 'getKeyUin' ||
            mname === 'getUin' ||
            mname === 'getKeyUinString' ||
            mname === 'getStrKeyUin'
          ) {
            var overloads = C[mname].overloads;
            for (var j = 0; j < overloads.length; j++) {
              overloads[j].implementation = (function (cls, mn) {
                return function () {
                  var r = this[mn].apply(this, arguments);
                  tryQQ(r, cls + '.' + mn);
                  return r;
                };
              })(name, mname);
            }
            log('hooked ' + name + '.' + mname);
          }
        }
        if (name.indexOf('AccountInfo') !== -1 && C.$init) {
          var inits = C.$init.overloads;
          for (var k = 0; k < inits.length; k++) {
            inits[k].implementation = (function (cls) {
              return function () {
                var r = this.$init.apply(this, arguments);
                try {
                  for (var a = 0; a < arguments.length; a++) {
                    tryQQ(arguments[a], cls + '.<init>');
                  }
                } catch (e) {}
                return r;
              };
            })(name);
          }
        }
      } catch (e2) {}
    },
    onComplete: function () {
      log('getKeyUin scan done — 请立即填验证码');
      send({ type: 'ready', stage: 'scan' });
    },
  });
}

function installHooks() {
  var mode = typeof __HOOK_MODE__ === 'undefined' ? 'keyonly' : String(__HOOK_MODE__);
  log('frida_hook.js mode=' + mode + ' pid=' + Process.id);

  if (mode === 'light') {
    log('轻量模式: 仅 getKeyUin');
  } else {
    hookMapPutGet('java.util.HashMap', 'HashMap');
    hookMapPutGet('java.util.concurrent.ConcurrentHashMap', 'ConcurrentHashMap');
    hookOkHttp();
    hookJsonObject();
    hookUserSigInfo();
  }

  send({ type: 'ready', stage: 'maps' });
  hookGetKeyUin();
}

var maxJavaWait = 8;
if (typeof __JAVA_WAIT_SEC__ !== 'undefined' && __JAVA_WAIT_SEC__ > 0) {
  maxJavaWait = __JAVA_WAIT_SEC__;
}

function artModuleNames() {
  try {
    return Process.enumerateModules()
      .filter(function (m) {
        return /art|jvm|dvm|java|jdk/i.test(m.name);
      })
      .map(function (m) {
        return m.name;
      });
  } catch (e) {
    return [];
  }
}

function tryInstallHooks() {
  if (typeof Java === 'undefined') return false;
  if (Java.available) {
    Java.perform(installHooks);
    return true;
  }
  if (artModuleNames().length > 0) {
    try {
      Java.perform(installHooks);
      return true;
    } catch (e) {
      log('Java.perform retry: ' + e);
    }
  }
  return false;
}

function waitForJava(attempt) {
  if (tryInstallHooks()) return;
  if (attempt >= maxJavaWait) {
    send({ type: 'no_java', pid: Process.id, arts: artModuleNames() });
    log('no Java in pid=' + Process.id);
    return;
  }
  if (attempt === 0) {
    log('等待 Java... max=' + maxJavaWait + 's');
  }
  setTimeout(function () {
    waitForJava(attempt + 1);
  }, 1000);
}

log('frida_hook.js loaded');
waitForJava(0);
