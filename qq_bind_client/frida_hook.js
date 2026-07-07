/**
 * Frida hook for QQ mobile SMS bind -> plain QQ (key_uin).
 * Waits for Java VM (fixes "Java is not defined" on wrong/native process).
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
    send({ type: 'tlv543', key: String(key), hex: hex, java: v ? String(v) : '' });
  } catch (e) {}
}

function installHooks() {
  log('frida_hook.js installing hooks...');

  try {
    var HashMap = Java.use('java.util.HashMap');
    HashMap.put.overload('java.lang.Object', 'java.lang.Object').implementation = function (k, v) {
      var ret = this.put(k, v);
      try {
        var ks = k ? k.toString() : '';
        if (ks === '1347' || ks === '543') emitTlv(ks, v);
      } catch (e) {}
      return ret;
    };
    HashMap.get.overload('java.lang.Object').implementation = function (k) {
      var v = this.get(k);
      try {
        var ks = k ? k.toString() : '';
        if (ks === '1347' || ks === '543') emitTlv(ks, v);
      } catch (e) {}
      return v;
    };
    log('hooked HashMap put/get');
  } catch (e) {
    log('HashMap skip: ' + e);
  }

  Java.enumerateLoadedClasses({
    onMatch: function (name) {
      if (name.indexOf('tencent') === -1 && name.indexOf('qq') === -1 && name.indexOf('oicq') === -1) return;
      if (name.indexOf('$') !== -1) return;
      try {
        var C = Java.use(name);
        var methods = C.class.getDeclaredMethods();
        for (var i = 0; i < methods.length; i++) {
          var mname = methods[i].getName();
          if (mname === 'getKeyUin' || mname === 'getUin' || mname === 'getKeyUinString') {
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
      } catch (e2) {}
    },
    onComplete: function () {
      log('class scan done — 请在 QQ 完成短信验证');
    },
  });
}

var maxJavaWait = 8;
if (typeof __SPAWN_MODE__ !== 'undefined' && __SPAWN_MODE__) {
  maxJavaWait = 120;
}

function waitForJava(attempt) {
  if (typeof Java !== 'undefined' && Java.available) {
    Java.perform(installHooks);
    return;
  }
  if (attempt >= maxJavaWait) {
    send({ type: 'no_java', pid: Process.id, spawn: !!__SPAWN_MODE__ });
    if (__SPAWN_MODE__) {
      log('ERROR: QQ 冷启动后仍未加载 Java，请完全退出 QQ 后重试「冷启动Hook」');
    } else {
      log('skip pid=' + Process.id + ' (no Java, not the hook target)');
    }
    return;
  }
  if (attempt === 0) {
    log('等待 Java 环境加载... (pid=' + Process.id + ', max=' + maxJavaWait + 's)');
  }
  setTimeout(function () {
    waitForJava(attempt + 1);
  }, 1000);
}

log('frida_hook.js loaded, pid=' + Process.id);
waitForJava(0);
