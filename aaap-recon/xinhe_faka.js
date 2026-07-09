var $_GET = (function () {
	var url = window.document.location.href.toString();
	var u = url.split("?");
	if (typeof (u[1]) == "string") {
		u = u[1].split("&");
		var get = {};
		for (var i in u) {
			var j = u[i].split("=");
			get[j[0]] = j[1];
		}
		return get;
	} else {
		return {};
	}
})();

(function () {
	var cookieFunction = function (name, value, options) {
		if (typeof value !== 'undefined') {
			options = options || {};
			if (value === null || value === '') {
				value = '';
				options.expires = -1;
			}
			var expires = '';
			if (options.expires && (typeof options.expires == 'number' || options.expires.toUTCString)) {
				var date;
				if (typeof options.expires == 'number') {
					date = new Date();
					date.setTime(date.getTime() + (options.expires * 24 * 60 * 60 * 1000));
				} else {
					date = options.expires;
				}
				expires = '; expires=' + date.toUTCString();
			}
			var path = options.path ? '; path=' + (options.path) : '';
			var domain = options.domain ? '; domain=' + (options.domain) : '';
			var secure = options.secure ? '; secure' : '';
			document.cookie = [name, '=', encodeURIComponent(value), expires, path, domain, secure].join('');
		} else {
			var cookieValue = null;
			if (document.cookie && document.cookie != '') {
				var cookies = document.cookie.split(';');
				for (var i = 0; i < cookies.length; i++) {
					var cookie = cookies[i].trim();
					if (cookie.substring(0, name.length + 1) == (name + '=')) {
						cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
						break;
					}
				}
			}
			return cookieValue;
		}
	};

	function initCookie() {
		if (typeof window.jQuery !== 'undefined' && typeof window.jQuery.cookie !== 'function') {
			window.jQuery.cookie = cookieFunction;
		}
		if (typeof window.$ !== 'undefined' && typeof window.$.cookie !== 'function') {
			window.$.cookie = cookieFunction;
		}
	}

	initCookie();

	var checkInterval = setInterval(function () {
		initCookie();
		if ((typeof window.jQuery !== 'undefined' && typeof window.jQuery.cookie === 'function') ||
			(typeof window.$ !== 'undefined' && typeof window.$.cookie === 'function')) {
			clearInterval(checkInterval);
		}
	}, 10);

	setTimeout(function () {
		clearInterval(checkInterval);
		initCookie();
	}, 1000);

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', initCookie);
	}
	window.addEventListener('load', initCookie);
})();
function getCookieValue(name) {
	if (typeof $ === 'undefined') {
		return null;
	}
	if (typeof $.cookie !== 'function') {
		var cookieImpl = function (name, value, options) {
			if (typeof value !== 'undefined') {
				options = options || {};
				if (value === null || value === '') {
					value = '';
					options.expires = -1;
				}
				var expires = '';
				if (options.expires && (typeof options.expires == 'number' || options.expires.toUTCString)) {
					var date;
					if (typeof options.expires == 'number') {
						date = new Date();
						date.setTime(date.getTime() + (options.expires * 24 * 60 * 60 * 1000));
					} else {
						date = options.expires;
					}
					expires = '; expires=' + date.toUTCString();
				}
				var path = options.path ? '; path=' + (options.path) : '';
				var domain = options.domain ? '; domain=' + (options.domain) : '';
				var secure = options.secure ? '; secure' : '';
				document.cookie = [name, '=', encodeURIComponent(value), expires, path, domain, secure].join('');
			} else {
				var cookieValue = null;
				if (document.cookie && document.cookie != '') {
					var cookies = document.cookie.split(';');
					for (var i = 0; i < cookies.length; i++) {
						var cookie = cookies[i].trim();
						if (cookie.substring(0, name.length + 1) == (name + '=')) {
							cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
							break;
						}
					}
				}
				return cookieValue;
			}
		};
		$.cookie = cookieImpl;
		if (typeof window.jQuery !== 'undefined' && window.jQuery !== $) {
			window.jQuery.cookie = cookieImpl;
		}
	}
	try {
		return $.cookie(name);
	} catch (e) {
		return null;
	}
}

function setCookieValue(name, value) {
	if (typeof $ === 'undefined') {
		return;
	}
	if (typeof $.cookie !== 'function') {
		var cookieImpl = function (name, value, options) {
			if (typeof value !== 'undefined') {
				options = options || {};
				if (value === null || value === '') {
					value = '';
					options.expires = -1;
				}
				var expires = '';
				if (options.expires && (typeof options.expires == 'number' || options.expires.toUTCString)) {
					var date;
					if (typeof options.expires == 'number') {
						date = new Date();
						date.setTime(date.getTime() + (options.expires * 24 * 60 * 60 * 1000));
					} else {
						date = options.expires;
					}
					expires = '; expires=' + date.toUTCString();
				}
				var path = options.path ? '; path=' + (options.path) : '';
				var domain = options.domain ? '; domain=' + (options.domain) : '';
				var secure = options.secure ? '; secure' : '';
				document.cookie = [name, '=', encodeURIComponent(value), expires, path, domain, secure].join('');
			} else {
				var cookieValue = null;
				if (document.cookie && document.cookie != '') {
					var cookies = document.cookie.split(';');
					for (var i = 0; i < cookies.length; i++) {
						var cookie = cookies[i].trim();
						if (cookie.substring(0, name.length + 1) == (name + '=')) {
							cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
							break;
						}
					}
				}
				return cookieValue;
			}
		};
		$.cookie = cookieImpl;
		if (typeof window.jQuery !== 'undefined' && window.jQuery !== $) {
			window.jQuery.cookie = cookieImpl;
		}
	}
	try {
		$.cookie(name, value);
	} catch (e) {
	}
}

function getPoint() {
	var multi = $('#tid').attr('multi');
	var count = $('#tid').attr('count');
	var price = $('#tid').attr('price');
	var shopimg = $('#tid').attr('shopimg');
	var close = $('#tid').attr('close');
	$('#display_price').show();
	if (multi == 1 && count > 1) {
		$('#need').val('ï¿¥' + price + "å…ƒ âž  " + count + "ä¸ª");
	} else {
		$('#need').val('ï¿¥' + price + "å…ƒ");
	}
	if (close == 1) {
		$('#submit_buy').val('åœæ­¢ä¸‹å•');
		$('#submit_buy').html('åœæ­¢ä¸‹å•');
		layer.alert('å½“å‰å•†å“ç»´æŠ¤ä¸­ï¼Œåœæ­¢ä¸‹å•ï¼');
	} else if (price == 0) {
		$('#submit_buy').val('å…è´¹é¢†å–');
		$('#submit_buy').html('å…è´¹é¢†å–');
	} else {
		$('#submit_buy').val('ç«‹å³è´­ä¹°');
		$('#submit_buy').html('ç«‹å³è´­ä¹°');
	}
	if (multi == 1) {
		$('#display_num').show();
	} else {
		$('#display_num').hide();
	}
	var isinvitegift = $('#tid').attr('isinvitegift');
	var invitegift_money = $('#tid').attr('invitegift_money');
	var invite_gift = $('#tid').attr('invite_gift');
	if (isinvitegift == 1 && invitegift_money != 0) {
		$('#alert_invitegift').show();
		$('#display_invitegift').show();
		$('#invitegift').val(invite_gift + "å…ƒ");
		$('#alert_invitegift').html('<strong>å•†å“è¿”åˆ©è§„åˆ™è¯´æ˜Žï¼š</strong><br/>ç”Ÿæˆä¸“å±žå•†å“è¿”åˆ©é“¾æŽ¥åŽå³å¯å¼€å§‹å‘é€ç»™å¥½å‹ï¼Œåˆ«äººè®¿é—®ä½ çš„ä¸“å±žå•†å“è¿”åˆ©é“¾æŽ¥å¹¶è´­ä¹°è¯¥è¿”åˆ©å•†å“é‡‘é¢ä¸€æ¬¡æ€§è¾¾åˆ°<font color="red">ã€' + invitegift_money + 'ã€‘å…ƒ</font>ï¼Œä½ å°±å¯ä»¥èŽ·å¾—å•†å“è¿”åˆ©<font color="red">ã€' + invite_gift + 'ã€‘å…ƒ</font>ï¼');
	} else {
		$('#alert_invitegift').hide();
		$('#display_invitegift').hide();
	}
	var desc = $('#tid').attr('desc');
	if (desc != '' && alert != 'null') {
		$('#alert_frame').show();
		$('#alert_frame').html(unescape(desc));
	} else {
		$('#alert_frame').hide();
	}
	var inputnametype = '';
	$('#inputsname').html("");
	var inputname = $('#tid').attr('inputname');
	if (inputname == 'hide') {
		var mysidValue = getCookieValue('mysid') || '';
		$('#inputsname').append('<input type="hidden" name="inputvalue" id="inputvalue" value="' + mysidValue + '"/>');
	} else {
		if (inputname == '') inputname = 'ä¸‹å•è´¦å·';
		if (inputname.indexOf('[') > 0 && inputname.indexOf(']') > 0) {
			inputnametype = inputname.split('[')[1].split(']')[0];
			inputname = inputname.split('[')[0];
		}
		$('#inputsname').append('<div class="from bl_view_title"><div class="from_wz_3" id="inputname">' + inputname + 'ï¼š</div><div class="from_in_2"><input type="text" name="inputvalue" id="inputvalue" value="' + ($_GET['qq'] ? $_GET['qq'] : '') + '" class="form-control" required onblur="checkInput()"/></div></div>');
	}
	var inputsname = $('#tid').attr('inputsname');
	if (inputsname != '') {
		$.each(inputsname.split('|'), function (i, value) {
			var inputsnametype = '';
			if (value.indexOf('[') > 0 && value.indexOf(']') > 0) {
				inputsnametype = value.split('[')[1].split(']')[0];
				value = value.split('[')[0];
			}
			if (value.indexOf('{') > 0 && value.indexOf('}') > 0) {
				var addstr = '';
				var selectname = value.split('{')[0];
				var selectstr = value.split('{')[1].split('}')[0];
				$.each(selectstr.split(','), function (i, v) {
					if (v.indexOf(':') > 0) {
						i = v.split(':')[0];
						v = v.split(':')[1];
					} else {
						i = v;
					}
					addstr += '<option value="' + i + '">' + v + '</option>';
				});
				$('#inputsname').append('<div class="from bl_view_title"><div class="from_wz_3" id="inputname' + (i + 2) + '">' + selectname + 'ï¼š</div><div class="from_in_2"><select name="inputvalue' + (i + 2) + '" id="inputvalue' + (i + 2) + '" class="form-control">' + addstr + '</select></div></div>');
			} else if (inputsnametype == 'multi') {
				$('#inputsname').append('<div class="from bl_view_title"><div class="from_wz_3" id="inputname' + (i + 2) + '" gettype="' + inputsnametype + '">' + value + 'ï¼š</div><div class="from_in_2"><input type="number" name="inputvalue' + (i + 2) + '" id="inputvalue' + (i + 2) + '" value="" class="form-control" required min="1" max="99999" onchange="getmulti(this)" act="getmulti"/></div></div>');
			} else {
				if (value == 'è¯´è¯´ID' || value == 'è¯´è¯´ï¼©ï¼¤' || inputsnametype == 'ssid')
					var addstr = '<div class="from_in_2 yanzheng onclick" onclick="get_shuoshuo(\'inputvalue' + (i + 2) + '\',$(\'#inputvalue\').val())">è‡ªåŠ¨èŽ·å–</div>';
				else if (value == 'æ—¥å¿—ID' || value == 'æ—¥å¿—ï¼©ï¼¤' || inputsnametype == 'rzid')
					var addstr = '<div class="from_in_2 yanzheng onclick" onclick="get_rizhi(\'inputvalue' + (i + 2) + '\',$(\'#inputvalue\').val())">è‡ªåŠ¨èŽ·å–</div>';
				else if (value == 'ä½œå“ID' || value == 'ä½œå“ï¼©ï¼¤' || inputsnametype == 'zpid')
					var addstr = '<div class="from_in_2 yanzheng onclick" onclick="getshareid2(\'inputvalue' + (i + 2) + '\',$(\'#inputvalue\').val())">è‡ªåŠ¨èŽ·å–</div>';
				else if (value == 'æ”¶è´§åœ°å€' || value == 'æ”¶è´§äººåœ°å€' || inputsnametype == 'address')
					var addstr = '<div class="from_in_2 yanzheng onclick" onclick="getCity(\'inputvalue' + (i + 2) + '\')">ç‚¹æ­¤é€‰æ‹©</div>';
				else
					var addstr = '';
				$('#inputsname').append('<div class="from bl_view_title"><div class="from_wz_3" id="inputname' + (i + 2) + '" gettype="' + inputsnametype + '">' + value + 'ï¼š</div><div class="from_in_2"><input type="text" name="inputvalue' + (i + 2) + '" id="inputvalue' + (i + 2) + '" value="" class="form-control" required/></div>' + addstr + '</div>');
			}
		});
	}
	if ($("#inputname2").html() == 'è¯´è¯´IDï¼š' || $("#inputname2").html() == 'è¯´è¯´ï¼©ï¼¤ï¼š' || $("#inputname2").attr('gettype') == 'ssid') {
		$('#inputvalue2').attr("disabled", true);
		$('#inputvalue2').attr("placeholder", "å¡«å†™QQè´¦å·åŽç‚¹å‡»â†’");
	} else if ($("#inputname").html() == 'ä½œå“IDï¼š' || $("#inputname").html() == 'ä½œå“ï¼©ï¼¤ï¼š' || $("#inputname").html() == 'å¸–å­IDï¼š' || $("#inputname").html() == 'ç”¨æˆ·IDï¼š' || $("#inputname").html() == 'ç”¨æˆ·ï¼©ï¼¤ï¼š' || inputnametype == 'shareid') {
		$('#inputvalue').attr("placeholder", "åœ¨æ­¤è¾“å…¥åˆ†äº«é“¾æŽ¥ å¯è‡ªåŠ¨èŽ·å–");
		$('#inputname').attr("gettype", "shareid");
		if ($("#inputname2").html() == 'ä½œå“IDï¼š' || $("#inputname2").html() == 'ä½œå“ï¼©ï¼¤ï¼š' || $("#inputname2").attr('gettype') == 'zpid') {
			$('#inputvalue2').attr("placeholder", "å¡«å†™ä½œå“é“¾æŽ¥åŽç‚¹å‡»â†’");
			$("#inputvalue2").attr('disabled', true);
		}
	} else if ($("#inputname").html() == 'ä½œå“é“¾æŽ¥ï¼š' || $("#inputname").html() == 'è§†é¢‘é“¾æŽ¥ï¼š' || $("#inputname").html() == 'åˆ†äº«é“¾æŽ¥ï¼š' || inputnametype == 'shareurl') {
		$('#inputvalue').attr("placeholder", "åœ¨æ­¤è¾“å…¥å¤åˆ¶åŽçš„é“¾æŽ¥ å¯è‡ªåŠ¨è½¬æ¢");
		$('#inputname').attr("gettype", "shareurl");
	} else if (inputnametype == 'pinduoduo') {
		$('#inputvalue').attr("placeholder", "åœ¨æ­¤ç²˜è´´ä½ çš„æ‹¼å¤šå¤šåŠ©åŠ›å£ä»¤");
		$('#inputname').attr("gettype", "pinduoduo");
	} else {
		$('#inputvalue').removeAttr("placeholder");
		$('#inputvalue2').removeAttr("placeholder");
	}
	if ($('#tid').attr('isfaka') == 1) {
		$('#inputvalue').attr("placeholder", "ç”¨äºŽæŽ¥æ”¶å¡å¯†å’ŒæŸ¥è¯¢è®¢å•");
		$('#display_left').show();
		var emailValue = getCookieValue('email');
		if (emailValue) {
			$('#inputvalue').val(emailValue);
		}
	} else {
		$('#display_left').hide();
	}
	var alert = $('#tid').attr('alert');
	if (alert != '' && alert != 'null') {
		var ii = layer.alert('' + unescape(alert) + '', {
			btn: ['æˆ‘çŸ¥é“äº†'],
			title: 'å•†å“æç¤º'
		}, function () {
			layer.close(ii);
		});
	}
}
function get_shuoshuo(id, uin, km, page) {
	km = km || 0;
	page = page || 1;
	if (uin == '') {
		layer.alert('è¯·å…ˆå¡«å†™QQå·ï¼'); return false;
	}
	var ii = layer.load(2, { shade: [0.1, '#fff'] });
	$.ajax({
		type: "GET",
		url: "ajax.php?act=getshuoshuo&uin=" + uin + "&page=" + page + "&hashsalt=" + hashsalt,
		dataType: 'json',
		success: function (data) {
			layer.close(ii);
			if (data.code == 0) {
				var addstr = '';
				$.each(data.data, function (i, item) {
					addstr += '<option value="' + item.tid + '">' + item.content + '</option>';
				});
				var nextpage = page + 1;
				var lastpage = page > 1 ? page - 1 : 1;
				if ($('#show_shuoshuo').length > 0) {
					$('#show_shuoshuo').html('<div class="from_wz_3 onclick" title="ä¸Šä¸€é¡µ" onclick="get_shuoshuo(\'' + id + '\',$(\'#inputvalue\').val(),' + km + ',' + lastpage + ')">ä¸Šä¸€é¡µ</div><div class="from_in_2"><select id="shuoid" class="form-control" onchange="set_shuoshuo(\'' + id + '\');">' + addstr + '</select></div><div class="from_in_2 yanzheng onclick" title="ä¸‹ä¸€é¡µ" onclick="get_shuoshuo(\'' + id + '\',$(\'#inputvalue\').val(),' + km + ',' + nextpage + ')">ä¸‹ä¸€é¡µ</div>');
				} else {
					$('#inputsname').append('<div class="from bl_view_title" id="show_shuoshuo"><div class="from_wz_3 onclick" title="ä¸Šä¸€é¡µ" onclick="get_shuoshuo(\'' + id + '\',$(\'#inputvalue\').val(),' + km + ',' + lastpage + ')">ä¸Šä¸€é¡µ</div><div class="from_in_2"><select id="shuoid" class="form-control" onchange="set_shuoshuo(\'' + id + '\');">' + addstr + '</select></div><div class="from_in_2 yanzheng onclick" title="ä¸‹ä¸€é¡µ" onclick="get_shuoshuo(\'' + id + '\',$(\'#inputvalue\').val(),' + km + ',' + nextpage + ')">ä¸‹ä¸€é¡µ</div></div>');
				}
				set_shuoshuo(id);
			} else {
				layer.alert(data.msg);
			}
		}
	});
}
function set_shuoshuo(id) {
	var shuoid = $('#shuoid').val();
	$('#' + id).val(shuoid);
}
function get_rizhi(id, uin, km, page) {
	km = km || 0;
	page = page || 1;
	if (uin == '') {
		layer.alert('è¯·å…ˆå¡«å†™QQå·ï¼'); return false;
	}
	var ii = layer.load(2, { shade: [0.1, '#fff'] });
	$.ajax({
		type: "GET",
		url: "ajax.php?act=getrizhi&uin=" + uin + "&page=" + page + "&hashsalt=" + hashsalt,
		dataType: 'json',
		success: function (data) {
			layer.close(ii);
			if (data.code == 0) {
				var addstr = '';
				$.each(data.data, function (i, item) {
					addstr += '<option value="' + item.blogId + '">' + item.title + '</option>';
				});
				var nextpage = page + 1;
				var lastpage = page > 1 ? page - 1 : 1;
				if ($('#show_rizhi').length > 0) {
					$('#show_rizhi').html('<div class="input-group"><div class="from_wz_3 onclick" onclick="get_rizhi(\'' + id + '\',$(\'#inputvalue\').val(),' + km + ',' + lastpage + ')"><i class="fa fa-chevron-left"></i></div><select id="blogid" class="form-control" onchange="set_rizhi(\'' + id + '\');">' + addstr + '</select><div class="from_in_2 yanzheng onclick" onclick="get_rizhi(\'' + id + '\',$(\'#inputvalue\').val(),' + km + ',' + nextpage + ')"><i class="fa fa-chevron-right"></i></div></div>');
				} else {
					$('#inputsname').append('<div class="from bl_view_title" id="show_rizhi"><div class="input-group"><div class="from_wz_3 onclick" onclick="get_rizhi(\'' + id + '\',$(\'#inputvalue\').val(),' + km + ',' + lastpage + ')"><i class="fa fa-chevron-left"></i></div><select id="blogid" class="form-control" onchange="set_rizhi(\'' + id + '\');">' + addstr + '</select><div class="from_in_2 yanzheng onclick" onclick="get_rizhi(\'' + id + '\',$(\'#inputvalue\').val(),' + km + ',' + nextpage + ')"><i class="fa fa-chevron-right"></i></div></div></div>');
				}
				set_rizhi(id);
			} else {
				layer.alert(data.msg);
			}
		}
	});
}
function set_rizhi(id) {
	var blogid = $('#blogid').val();
	$('#' + id).val(blogid);
}
function getsongid() {
	var songurl = $("#inputvalue").val();
	if (songurl == '') { layer.alert('è¯·ç¡®ä¿æ¯é¡¹ä¸èƒ½ä¸ºç©ºï¼'); return false; }
	if (songurl.indexOf('.qq.com') < 0) { layer.alert('è¯·è¾“å…¥æ­£ç¡®çš„æ­Œæ›²çš„åˆ†äº«é“¾æŽ¥ï¼'); return false; }
	try {
		var songid = songurl.split('s=')[1].split('&')[0];
		layer.msg('IDèŽ·å–æˆåŠŸï¼ä¸‹å•å³å¯');
	} catch (e) {
		layer.alert('è¯·è¾“å…¥æ­£ç¡®çš„æ­Œæ›²çš„åˆ†äº«é“¾æŽ¥ï¼'); return false;
	}
	$('#inputvalue').val(songid);
}
function getsharelink() {
	var songurl = $("#inputvalue").val();
	if (songurl == '') { layer.alert('è¯·ç¡®ä¿æ¯é¡¹ä¸èƒ½ä¸ºç©ºï¼'); return false; }
	if (songurl.indexOf('http') < 0) { layer.alert('è¯·è¾“å…¥æ­£ç¡®çš„å†…å®¹ï¼'); return false; }
	try {
		if (songurl.indexOf('http://') >= 0) {
			var songid = 'http://' + songurl.split('http://')[1].split(' ')[0].split('ï¼Œ')[0];
		} else if (songurl.indexOf('https://') >= 0) {
			var songid = 'https://' + songurl.split('https://')[1].split(' ')[0].split('ï¼Œ')[0];
		}
		if (songid != $("#inputvalue").val()) layer.msg('é“¾æŽ¥è½¬æ¢æˆåŠŸï¼ä¸‹å•å³å¯');
	} catch (e) {
		layer.alert('è¯·è¾“å…¥æ­£ç¡®çš„å†…å®¹ï¼'); return false;
	}
	$('#inputvalue').val(songid);
}
function getshareid() {
	var songurl = $("#inputvalue").val();
	if (songurl == '') { layer.alert('è¯·ç¡®ä¿æ¯é¡¹ä¸èƒ½ä¸ºç©ºï¼'); return false; }
	if (songurl.indexOf('http') < 0) { layer.alert('è¯·è¾“å…¥æ­£ç¡®çš„å†…å®¹ï¼'); return false; }
	try {
		if (songurl.indexOf('http://') >= 0) {
			var songurl = 'http://' + songurl.split('http://')[1].split(' ')[0].split('ï¼Œ')[0];
		} else if (songurl.indexOf('https://') >= 0) {
			var songurl = 'https://' + songurl.split('https://')[1].split(' ')[0].split('ï¼Œ')[0];
		} else {
			throw false;
		}
		var ii = layer.load(2, { shade: [0.1, '#fff'] });
		$.ajax({
			type: "POST",
			url: "ajax.php?act=getshareid",
			data: { url: songurl, hashsalt: hashsalt },
			dataType: 'json',
			success: function (data) {
				layer.close(ii);
				if (data.code == 0) {
					$('#inputvalue').val(data.songid);
					if (typeof data.songid2 != "undefined" && $('#inputvalue2').length > 0) $('#inputvalue2').val(data.songid2);
					layer.msg('IDèŽ·å–æˆåŠŸï¼ä¸‹å•å³å¯');
				} else {
					layer.alert(data.msg); return false;
				}
			}
		});
	} catch (e) {
		layer.alert('è¯·è¾“å…¥æ­£ç¡®çš„å†…å®¹ï¼'); return false;
	}
}
function getshareid2(id, songurl) {
	if (songurl == '') { layer.alert('è¯·ç¡®ä¿æ¯é¡¹ä¸èƒ½ä¸ºç©ºï¼'); return false; }
	if (songurl.indexOf('http') < 0) { return false; }
	getshareid();
}
function getpddinput() {
	var result = "";
	var pddinput = $("#inputvalue").val();
	if (pddinput == '') {
		return false;
	}
	if (pddinput.indexOf("PinDuoDuo") != -1 && pddinput.indexOf("http") === -1) {
		pddinput = pddinput.replace("PinDuoDuo", "");
	}
	var pattresult = (/[a-zA-Z0-9=_\&\?\-\/]?[a-zA-Z0-9]{16}[a-zA-Z0-9=_\&\?\-\/]?/).exec(pddinput);
	var patt_str = (/Ï„[a-zA-Z0-9]{13}Ï„/).exec(pddinput);
	var pattresult1 = (/(^[a-zA-Z0-9][a-zA-Z0-9]+)ç‚¹+/).exec(pddinput);
	var pattresult2 = (/(^[0-9]{15})/).exec(pddinput);
	var pattresult3 = (/([0-9]{15}$)/).exec(pddinput);
	var pattresult4 = (/[0-9]{6,20}/).exec(pddinput);
	var pattresult5 = (/(http|https):\/\/[\w\.\=\_\/\-\$\&\!\?\(\)#%+:;]+/).exec(pddinput);
	var pattresult6 = (/([0-9]{8})/).exec(pddinput);
	var pattresult7 = (/[a-zA-Z0-9=_\&\?\-\/]?[a-zA-Z0-9]{15}[a-zA-Z0-9=_\&\?\-\/]?/).exec(pddinput);
	var pattresult12 = (/^[a-zA-Z0-9]{16}/).exec(pddinput);

	var pattresult10 = (/[\ud83a-\ud83f][\u0000-\uFFFF]/).exec(pddinput);
	var no_emoji_input = pddinput.replace(/[\ud83a-\ud83f][\u0000-\uFFFF]/g, "");
	no_emoji_input = no_emoji_input.replace(/[\ufe00-\ufe0f]/g, "");
	no_emoji_input = no_emoji_input.replace(/[\u0000-\uffff][\u20aa-\u20ff]/g, "");

	var pattresult13 = (/[a-zA-Z0-9]{13}/).exec(no_emoji_input);
	var pattresult14 = (/[a-zA-Z0-9]{14}/).exec(no_emoji_input);
	var status = false;
	if (exec_succ(patt_str)) {
		result = patt_str[0];
	} else if (exec_succ(pattresult1) && pattresult1.length > 1) {
		result = pattresult1[1];
	} else if (exec_succ(pattresult2) && pattresult2.length > 1) {
		result = pattresult2[1];
	} else if (exec_succ(pattresult3) && pattresult3.length > 1) {
		result = pattresult3[1];
	} else if (exec_succ(pattresult) && pattresult[0].length == 16) {
		var a = pattresult[0].length;
		result = pattresult[0];
	} else if (exec_succ(pattresult5) && pattresult5.length > 1) {
		var a = pattresult5[0].length;
		result = pattresult5[0];
	} else if (pddinput.indexOf("â‡¥") != -1 && pddinput.indexOf("â‡¤") != -1) {
		result = pddinput.substring(pddinput.indexOf("â‡¥"), pddinput.indexOf("â‡¤") + 1);
		layer.msg('IDèŽ·å–æˆåŠŸï¼æäº¤ä¸‹å•å³å¯');
	} else if (exec_succ(pattresult4) && (pattresult4[0].length == 9 || pattresult4[0].length == 13 || pattresult4[0].length == 15)) {
		result = pattresult4[0];
		status = true;
	} else if (pddinput.indexOf("å£ä»¤") != -1 && exec_succ(pattresult6) && pattresult6.length > 1) {
		result = pattresult6[1];
	} else if (!exec_succ(pattresult10) && exec_succ(pattresult7) && pattresult7[0].length == 15) {
		var a = pattresult7[0].length;
		result = pattresult7[0];
	} else if (exec_succ(pattresult12)) {
		result = pattresult12[0];
	} else if (exec_succ(pattresult13) && !exec_succ(pattresult14)) {
		var password = "\ud83d\ude42" + pattresult13[0].slice(0, 6) + "\ud83d\ude42" + pattresult13[0].slice(6) + "\ud83d\ude42";
		result = password;
		$('#inputvalue').prop('readonly', true);
	} else {
		result = pddinput;
	}
	$('#inputvalue').val(result);
	return status;
}
function exec_succ(pattresult) {
	if (typeof (pattresult) == 'object' && pattresult != null && pattresult.length > 0) {
		return true;
	} else {
		return false;
	}
}
function getmulti(obj) {
	var num = parseInt($(obj).val());
	if (num < 1) { num = 1; $(obj).val('1'); }

	var mult = 1;
	$("input[act='getmulti']").each(function () {
		mult = mult * parseInt($(this).val());
	});

	var i = parseInt($("#num").val());
	if (isNaN(i)) return false;
	var price = parseFloat($('#tid option:selected').attr('price'));
	var count = parseInt($('#tid option:selected').attr('count'));
	var prices = $('#tid option:selected').attr('prices');
	if (i < 1) $("#num").val(1);
	if (prices != '' || prices != 'null') {
		var discount = 0;
		$.each(prices.split(','), function (index, item) {
			if (i >= parseInt(item.split('|')[0])) discount = parseFloat(item.split('|')[1]);
		});
		price = price - discount;
	}
	price = price * i * mult;
	count = count * i;
	if (count > 1) $('#need').val('ï¿¥' + price.toFixed(2) + "å…ƒ âž  " + count + "ä¸ª");
	else $('#need').val('ï¿¥' + price.toFixed(2) + "å…ƒ");
}
var handlerEmbed = function (captchaObj) {
	captchaObj.appendTo('#captcha');
	captchaObj.onReady(function () {
		$("#captcha_wait").hide();
	}).onSuccess(function () {
		var result = captchaObj.getValidate();
		if (!result) {
			return alert('è¯·å®ŒæˆéªŒè¯');
		}
		var ii = layer.load(2, { shade: [0.1, '#fff'] });
		$.ajax({
			type: "POST",
			url: "ajax.php?act=pay",
			data: { tid: $("#tid").val(), inputvalue: $("#inputvalue").val(), inputvalue2: $("#inputvalue2").val(), inputvalue3: $("#inputvalue3").val(), inputvalue4: $("#inputvalue4").val(), inputvalue5: $("#inputvalue5").val(), num: $("#num").val(), hashsalt: hashsalt, geetest_challenge: result.geetest_challenge, geetest_validate: result.geetest_validate, geetest_seccode: result.geetest_seccode, csrf_token: typeof csrf_token !== 'undefined' ? csrf_token : '' },
			dataType: 'json',
			success: function (data) {
				layer.close(ii);
				if (data.code >= 0) {
					$('#alert_frame').hide();
					alert('é¢†å–æˆåŠŸï¼');
					window.location.href = '?buyok=1';
				} else {
					layer.alert(data.msg);
					captchaObj.reset();
				}
			}
		});
	});
};
var handlerEmbed2 = function (token) {
	if (!token) {
		return alert('è¯·å®ŒæˆéªŒè¯');
	}
	var ii = layer.load(2, { shade: [0.1, '#fff'] });
	$.ajax({
		type: "POST",
		url: "ajax.php?act=pay",
		data: { tid: $("#tid").val(), inputvalue: $("#inputvalue").val(), inputvalue2: $("#inputvalue2").val(), inputvalue3: $("#inputvalue3").val(), inputvalue4: $("#inputvalue4").val(), inputvalue5: $("#inputvalue5").val(), num: $("#num").val(), hashsalt: hashsalt, token: token, csrf_token: typeof csrf_token !== 'undefined' ? csrf_token : '' },
		dataType: 'json',
		success: function (data) {
			layer.close(ii);
			if (data.code >= 0) {
				$('#alert_frame').hide();
				alert('é¢†å–æˆåŠŸï¼');
				window.location.href = '?buyok=1';
			} else {
				layer.alert(data.msg);
			}
		}
	});
};
var handlerEmbed3 = function (vaptchaObj) {
	vaptchaObj.render();
	$('#captcha_text').hide();
	vaptchaObj.listen('pass', function () {
		var token = vaptchaObj.getToken();
		if (!token) {
			return alert('è¯·å®ŒæˆéªŒè¯');
		}
		var ii = layer.load(2, { shade: [0.1, '#fff'] });
		$.ajax({
			type: "POST",
			url: "ajax.php?act=pay",
			data: { tid: $("#tid").val(), inputvalue: $("#inputvalue").val(), inputvalue2: $("#inputvalue2").val(), inputvalue3: $("#inputvalue3").val(), inputvalue4: $("#inputvalue4").val(), inputvalue5: $("#inputvalue5").val(), num: $("#num").val(), hashsalt: hashsalt, token: token, csrf_token: typeof csrf_token !== 'undefined' ? csrf_token : '' },
			dataType: 'json',
			success: function (data) {
				layer.close(ii);
				if (data.code >= 0) {
					$('#alert_frame').hide();
					alert('é¢†å–æˆåŠŸï¼');
					window.location.href = '?buyok=1';
				} else {
					layer.alert(data.msg);
					vaptchaObj.reset();
				}
			}
		});
	});
};
function dopay(type, orderid) {
	if (type == 'rmb') {
		var ii = layer.msg('æ­£åœ¨æäº¤è®¢å•è¯·ç¨å€™...', { icon: 16, shade: 0.5, time: 15000 });
		$.ajax({
			type: "POST",
			url: "ajax.php?act=payrmb",
			data: { orderid: orderid, csrf_token: typeof csrf_token !== 'undefined' ? csrf_token : '' },
			dataType: 'json',
			success: function (data) {
				layer.close(ii);
				if (data.code == 1) {
					// æ”¯ä»˜æˆåŠŸåŽï¼Œæ›´æ–°è´­ç‰©è½¦è®¡æ•°
					$.ajax({
						type: "GET",
						url: "ajax.php?act=getcount",
						dataType: 'json',
						async: true,
						success: function (countData) {
							if (countData.cart_count != null) {
								$('#cart_count').html(countData.cart_count);
								if (countData.cart_count == 0) {
									$('#alert_cart').slideUp();
								}
							}
						}
					});
					alert(data.msg);
					window.location.href = '?buyok=1';
				} else if (data.code == -2) {
					// æ”¯ä»˜æˆåŠŸåŽï¼Œæ›´æ–°è´­ç‰©è½¦è®¡æ•°
					$.ajax({
						type: "GET",
						url: "ajax.php?act=getcount",
						dataType: 'json',
						async: true,
						success: function (countData) {
							if (countData.cart_count != null) {
								$('#cart_count').html(countData.cart_count);
								if (countData.cart_count == 0) {
									$('#alert_cart').slideUp();
								}
							}
						}
					});
					alert(data.msg);
					window.location.href = '?buyok=1';
				} else if (data.code == -3) {
					var confirmobj = layer.confirm('ä½ çš„ä½™é¢ä¸è¶³ï¼Œè¯·å……å€¼ï¼', {
						btn: ['ç«‹å³å……å€¼', 'å–æ¶ˆ']
					}, function () {
						window.location.href = './user/recharge.php';
					}, function () {
						layer.close(confirmobj);
					});
				} else if (data.code == -4) {
					var confirmobj = layer.confirm('ä½ è¿˜æœªç™»å½•ï¼Œæ˜¯å¦çŽ°åœ¨ç™»å½•ï¼Ÿ', {
						btn: ['ç™»å½•', 'æ³¨å†Œ', 'å–æ¶ˆ']
					}, function () {
						window.location.href = './user/login.php';
					}, function () {
						window.location.href = './user/reg.php';
					}, function () {
						layer.close(confirmobj);
					});
				} else {
					layer.alert(data.msg);
				}
			}
		});
	} else {
		window.location.href = 'other/submit.php?type=' + type + '&orderid=' + orderid;
	}
}
function cancel(orderid) {
	layer.closeAll();
	$.ajax({
		type: "POST",
		url: "ajax.php?act=cancel",
		data: { orderid: orderid, hashsalt: hashsalt, csrf_token: typeof csrf_token !== 'undefined' ? csrf_token : '' },
		dataType: 'json',
		async: true,
		success: function (data) {
			if (data.code == 0) {
			} else {
				layer.msg(data.msg);
				window.location.reload();
			}
		},
		error: function (data) {
			window.location.reload();
		}
	});
}
function checkInput() {
	if ($('#inputname').attr("gettype") == 'shareid') {
		if ($("#inputvalue").val() != '' && $("#inputvalue").val().indexOf('http') >= 0) {
			getshareid();
		}
	}
	else if ($('#inputname').attr("gettype") == 'shareurl') {
		if ($("#inputvalue").val() != '' && $("#inputvalue").val().indexOf('http') >= 0) {
			getsharelink();
		}
	}
	else if ($('#inputname').attr("gettype") == 'pinduoduo') {
		if ($("#inputvalue").val() != '') {
			getpddinput();
		}
	}
}
function getCity(inputid, fid, i) {
	i = i || 0;
	fid = fid || 0;
	if (i == 0) {
		var options = '<select class="form-control" id="biaozhi_' + (i + 1) + '" onchange="getCity(\'' + inputid + '\',this.value,' + (i + 1) + ')">';
		options += '<option>è¯·é€‰æ‹©åœ°å€</option>';
		$.each("\u5317\u4eac|1|72|1,\u4e0a\u6d77|2|78|1,\u5929\u6d25|3|51035|1,\u91cd\u5e86|4|113|1,\u6cb3\u5317|5|142,\u5c71\u897f|6|303,\u6cb3\u5357|7|412,\u8fbd\u5b81|8|560,\u5409\u6797|9|639,\u9ed1\u9f99\u6c5f|10|698,\u5185\u8499\u53e4|11|799,\u6c5f\u82cf|12|904,\u5c71\u4e1c|13|1000,\u5b89\u5fbd|14|1116,\u6d59\u6c5f|15|1158,\u798f\u5efa|16|1303,\u6e56\u5317|17|1381,\u6e56\u5357|18|1482,\u5e7f\u4e1c|19|1601,\u5e7f\u897f|20|1715,\u6c5f\u897f|21|1827,\u56db\u5ddd|22|1930,\u6d77\u5357|23|2121,\u8d35\u5dde|24|2144,\u4e91\u5357|25|2235,\u897f\u85cf|26|2951,\u9655\u897f|27|2376,\u7518\u8083|28|2487,\u9752\u6d77|29|2580,\u5b81\u590f|30|2628,\u65b0\u7586|31|2652,\u6e2f\u6fb3|52993|52994,\u53f0\u6e7e|32|2768,\u9493\u9c7c\u5c9b|84|84".split(","), function (a, c) {
			c = c.split("|"),
				options += '<option value="' + c[1] + '">' + c[0] + '</option>'
		});
		options += '</select>';
		layer.alert('<div id="layer_button">' + options + '</div>', function (index) {
			var con = '';
			$("#layer_button select").each(function () {
				con += $(this.options[this.selectedIndex]).text();
			});
			if ($("#more_dizhi").length > 0) con += $("#more_dizhi").val();
			if (con.length < 7) return layer.alert('è¯·é€‰æ‹©å®Œæ•´çš„æ”¶è´§åœ°å€ï¼');
			$("#" + inputid).val(con).show();
			$("#button_" + inputid).hide();
			layer.close(index);
		});
	} else {
		$.ajax({
			type: "get",
			url: "https://fts.jd.com/area/get?fid=" + fid,
			dataType: "jsonp",
			success: function (data) {
				if (data.length < 1) {
					if ($("#layer_button").html().indexOf("getCity('" + inputid + "',this.value," + (i + 1) + ")") != -1) {
						$("#biaozhi_" + (i + 1)).remove();
					}
					if ($("#more_dizhi").length > 0) { } else $("#layer_button").append('<input class="form-control" id="more_dizhi" placeholder="è¯¦ç»†åœ°å€(æ‘ã€é—¨ç‰Œå·)">');
					return false;
				}
				var options = '<select class="form-control" id="biaozhi_' + (i + 1) + '" onchange="getCity(\'' + inputid + '\',this.value,' + (i + 1) + ')">';
				options += '<option>è¯·é€‰æ‹©åœ°å€</option>';
				$.each(data, function (index, res) {
					options += '<option value="' + res.id + '">' + res.name + '</option>';
				});
				options += '</select>';
				if ($("#layer_button").html().indexOf("getCity('" + inputid + "',this.value," + (i + 1) + ")") != -1) {
					$("#more_dizhi").remove();
					$("#biaozhi_" + (i + 1)).html(options);
				} else {
					$("#layer_button").append(options);
				}
			}
		});
	}
}
function openCart() {
	window.location.href = './?mod=cart';
}
$(document).ready(function () {
	$("#submit_buy").click(function () {
		var tid = $("#tid").val();
		if (tid == 0) { layer.alert('è¯·é€‰æ‹©å•†å“ï¼'); return false; }
		var inputvalue = $("#inputvalue").val();
		if (inputvalue == '' || tid == '') { layer.alert('è¯·ç¡®ä¿æ¯é¡¹ä¸èƒ½ä¸ºç©ºï¼'); return false; }
		if ($("#inputvalue2").val() == '' || $("#inputvalue3").val() == '' || $("#inputvalue4").val() == '' || $("#inputvalue5").val() == '') { layer.alert('è¯·ç¡®ä¿æ¯é¡¹ä¸èƒ½ä¸ºç©ºï¼'); return false; }
		if (($('#inputname').html() == 'ä¸‹å•ï¼±ï¼±ï¼š' || $('#inputname').html() == 'ï¼±ï¼±è´¦å·ï¼š' || $("#inputname").html() == 'QQè´¦å·ï¼š') && (inputvalue.length < 5 || inputvalue.length > 11 || isNaN(inputvalue))) { layer.alert('è¯·è¾“å…¥æ­£ç¡®çš„QQå·ï¼'); return false; }
		var reg = /^([a-zA-Z0-9_-])+@([a-zA-Z0-9_-])+(.[a-zA-Z0-9_-])+/;
		if ($('#inputname').html() == 'ä½ çš„é‚®ç®±ï¼š' && !reg.test(inputvalue)) { layer.alert('é‚®ç®±æ ¼å¼ä¸æ­£ç¡®ï¼'); return false; }
		reg = /^[1][0-9]{10}$/;
		if ($('#inputname').html() == 'æ‰‹æœºå·ç ï¼š' && !reg.test(inputvalue)) { layer.alert('æ‰‹æœºå·ç æ ¼å¼ä¸æ­£ç¡®ï¼'); return false; }
		if ($("#inputname2").html() == 'è¯´è¯´IDï¼š' || $("#inputname2").html() == 'è¯´è¯´ï¼©ï¼¤ï¼š') {
			if ($("#inputvalue2").val().length != 24) { layer.alert('è¯´è¯´å¿…é¡»æ˜¯åŽŸåˆ›è¯´è¯´ï¼'); return false; }
		}
		checkInput();
		if ($("#inputname").html() == 'æŠ–éŸ³ä½œå“IDï¼š' || $("#inputname").html() == 'ç«å±±ä½œå“IDï¼š' || $("#inputname").html() == 'ç«å±±ç›´æ’­IDï¼š') {
			if ($("#inputvalue").val().length != 19) { layer.alert('æ‚¨è¾“å…¥çš„ä½œå“IDæœ‰è¯¯ï¼'); return false; }
		}
		if ($("#inputname2").html() == 'æŠ–éŸ³è¯„è®ºIDï¼š') {
			if ($("#inputvalue2").val().length != 19) { layer.alert('æ‚¨è¾“å…¥çš„è¯„è®ºIDæœ‰è¯¯ï¼è¯·ç‚¹å‡»è‡ªåŠ¨èŽ·å–æ‰‹åŠ¨é€‰æ‹©è¯„è®ºï¼'); return false; }
		}
		if ($('#inputname').attr("gettype") == 'shareurl') {
			if ($("#inputvalue").val().indexOf('http://') == -1 && $("#inputvalue").val().indexOf('https://') == -1) {
				layer.alert('æ‚¨è¾“å…¥çš„é“¾æŽ¥æœ‰è¯¯ï¼è¯·é‡æ–°è¾“å…¥ï¼'); return false;
			}
		}
		var ii = layer.load(2, { shade: [0.1, '#fff'] });
		$.ajax({
			type: "POST",
			url: "ajax.php?act=pay",
			data: { tid: tid, inputvalue: $("#inputvalue").val(), inputvalue2: $("#inputvalue2").val(), inputvalue3: $("#inputvalue3").val(), inputvalue4: $("#inputvalue4").val(), inputvalue5: $("#inputvalue5").val(), num: $("#num").val(), hashsalt: hashsalt, csrf_token: typeof csrf_token !== 'undefined' ? csrf_token : '' },
			dataType: 'json',
			success: function (data) {
				layer.close(ii);
				if (data.code == 0) {
					if ($('#inputname').html() == 'ä½ çš„é‚®ç®±ï¼š') {
						setCookieValue('email', inputvalue);
					}
					window.location.href = './?mod=order&orderid=' + data.trade_no;
				} else if (data.code == 1) {
					if ($('#inputname').html() == 'ä½ çš„é‚®ç®±ï¼š') {
						setCookieValue('email', inputvalue);
					}
					alert('é¢†å–æˆåŠŸï¼');
					window.location.href = '?buyok=1';
				} else if (data.code == 2) {
					if (data.type == 1) {
						layer.open({
							type: 1,
							title: 'å®ŒæˆéªŒè¯',
							skin: 'layui-layer-rim',
							area: ['320px', '100px'],
							content: '<div id="captcha"><div id="captcha_text">æ­£åœ¨åŠ è½½éªŒè¯ç </div><div id="captcha_wait"><div class="loading"><div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div></div></div></div>',
							success: function () {
								$.getScript("//static.geetest.com/static/tools/gt.js", function () {
									$.ajax({
										url: "ajax.php?act=captcha&t=" + (new Date()).getTime(),
										type: "get",
										dataType: "json",
										success: function (data) {
											$('#captcha_text').hide();
											$('#captcha_wait').show();
											initGeetest({
												gt: data.gt,
												challenge: data.challenge,
												new_captcha: data.new_captcha,
												product: "popup",
												width: "100%",
												offline: !data.success
											}, handlerEmbed);
										}
									});
								});
							}
						});
					} else if (data.type == 2) {
						layer.open({
							type: 1,
							title: 'å®ŒæˆéªŒè¯',
							skin: 'layui-layer-rim',
							area: ['320px', '260px'],
							content: '<div id="captcha" style="margin: auto;"><div id="captcha_text">æ­£åœ¨åŠ è½½éªŒè¯ç </div></div>',
							success: function () {
								$.getScript("//cdn.dingxiang-inc.com/ctu-group/captcha-ui/index.js", function () {
									var myCaptcha = _dx.Captcha(document.getElementById('captcha'), {
										appId: data.appid,
										type: 'basic',
										style: 'embed',
										success: handlerEmbed2
									})
									myCaptcha.on('ready', function () {
										$('#captcha_text').hide();
									})
								});
							}
						});
					} else if (data.type == 3) {
						layer.open({
							type: 1,
							title: 'å®ŒæˆéªŒè¯',
							skin: 'layui-layer-rim',
							area: ['320px', '231px'],
							content: '<div id="captcha"><div id="captcha_text">æ­£åœ¨åŠ è½½éªŒè¯ç </div></div>',
							success: function () {
								$.getScript("//v.vaptcha.com/v3.js", function () {
									vaptcha({
										vid: data.appid,
										type: 'embed',
										container: '#captcha',
										offline_server: 'https://management.vaptcha.com/api/v3/demo/offline'
									}).then(handlerEmbed3);
								});
							}
						});
					}
				} else if (data.code == 3) {
					layer.alert(data.msg, {
						closeBtn: false
					}, function () {
						window.location.reload();
					});
				} else if (data.code == 4) {
					var confirmobj = layer.confirm('è¯·ç™»å½•åŽå†è´­ä¹°ï¼Œæ˜¯å¦çŽ°åœ¨ç™»å½•ï¼Ÿ', {
						btn: ['ç™»å½•', 'æ³¨å†Œ', 'å–æ¶ˆ']
					}, function () {
						window.location.href = './user/login.php';
					}, function () {
						window.location.href = './user/reg.php';
					}, function () {
						layer.close(confirmobj);
					});
				} else {
					layer.alert(data.msg, { icon: 2 });
				}
			}
		});
	});
	//èŽ·å–å•†å“è¿”åˆ©é“¾æŽ¥
	$("#submit_invitegift_link").click(function () {
		var tid = $("#tid").val();
		if (tid == 0) { layer.alert('è¯·é€‰æ‹©å•†å“ï¼'); return false; }
		layer.msg('æ­£åœ¨ç”Ÿæˆå•†å“è¿”åˆ©é“¾æŽ¥...', { icon: 16, time: 9999999 })
		$.ajax({
			type: "POST",
			url: "./ajax.php?act=share_invitegift_link",
			data: { tid: tid, csrf_token: typeof csrf_token !== 'undefined' ? csrf_token : '' },
			dataType: "json",
			success: function (data) {
				if (data.code == 0) {
					var clipboard;
					var confirmobj = layer.confirm(data.content, {
						title: 'ç”Ÿæˆå•†å“è¿”åˆ©é“¾æŽ¥æˆåŠŸ', shadeClose: true, btn: ['å¤åˆ¶', 'å…³é—­'], success: function () {
							clipboard = new Clipboard('.layui-layer-btn0', { text: function () { return data.content; } });
							clipboard.on('success', function (e) {
								alert('å¤åˆ¶æˆåŠŸï¼');
							});
							clipboard.on('error', function (e) {
								alert('å¤åˆ¶å¤±è´¥ï¼Œè¯·é•¿æŒ‰é“¾æŽ¥åŽæ‰‹åŠ¨å¤åˆ¶');
							});
						}
						, end: function () {
							clipboard.destroy();
						}
					}, function () {
					}, function () {
						layer.close(confirmobj);
					});
				} else {
					layer.msg(data.msg, { icon: 2 });
				}
			},
			error: function () {
				layer.alert('ç”Ÿæˆå¤±è´¥ï¼');
			}
		});
	});
	//èŽ·å–å•†å“æµ·æŠ¥
	$("#submit_get_share").click(function () {
		var tid = $("#tid").val();
		if (tid == 0) { layer.alert('è¯·é€‰æ‹©å•†å“ï¼'); return false; }
		layer.msg('æ­£åœ¨ç”Ÿæˆå•†å“åˆ†äº«æµ·æŠ¥...', { icon: 16, time: 9999999 })
		$.ajax({
			type: "POST",
			url: "./ajax.php?act=SharePoster",
			data: { tid: tid, csrf_token: typeof csrf_token !== 'undefined' ? csrf_token : '' },
			dataType: "json",
			success: function (data) {
				if (data.code == 0) {
					layer.alert('<img src="' + data.poster + '" width=300 heigth=450 />', {
						area: ['340px', '490px'],
						title: false,
						btn: false, shade: [0.8, '#000'],
						shadeClose: true,
					})
				} else {
					layer.msg(data.msg, { icon: 2 });
				}
			},
			error: function () {
				layer.alert('ç”Ÿæˆå¤±è´¥ï¼');
			}
		});
	});
	$("#num_add").click(function () {
		var i = parseInt($("#num").val());
		if ($("#need").val() == '') {
			layer.alert('è¯·å…ˆé€‰æ‹©å•†å“');
			return false;
		}
		var multi = $('#tid').attr('multi');
		var count = parseInt($('#tid').attr('count'));
		if (multi == '0') {
			layer.alert('è¯¥å•†å“ä¸æ”¯æŒé€‰æ‹©æ•°é‡');
			return false;
		}
		i++;
		$("#num").val(i);
		var price = parseFloat($('#tid').attr('price'));
		var prices = $('#tid').attr('prices');
		if (prices != '' || prices != 'null') {
			var discount = 0;
			$.each(prices.split(','), function (index, item) {
				if (i >= parseInt(item.split('|')[0])) discount = parseFloat(item.split('|')[1]);
			});
			price = price - discount;
		}

		var mult = 1;
		$("input[act='getmulti']").each(function () {
			mult = mult * parseInt($(this).val());
		});

		price = price * i * mult;
		count = count * i;
		if (count > 1) $('#need').val('ï¿¥' + price.toFixed(2) + "å…ƒ âž  " + count + "ä¸ª");
		else $('#need').val('ï¿¥' + price.toFixed(2) + "å…ƒ");
	});
	$("#num_min").click(function () {
		var i = parseInt($("#num").val());
		if (i <= 1) {
			layer.msg('æœ€ä½Žä¸‹å•ä¸€ä»½å“¦ï¼');
			return false;
		}
		if ($("#need").val() == '') {
			layer.alert('è¯·å…ˆé€‰æ‹©å•†å“');
			return false;
		}
		var multi = $('#tid').attr('multi');
		var count = parseInt($('#tid').attr('count'));
		if (multi == '0') {
			layer.alert('è¯¥å•†å“ä¸æ”¯æŒé€‰æ‹©æ•°é‡');
			return false;
		}
		i--;
		if (i <= 0) i = 1;
		$("#num").val(i);
		var price = parseFloat($('#tid').attr('price'));
		var prices = $('#tid').attr('prices');
		if (prices != '' || prices != 'null') {
			var discount = 0;
			$.each(prices.split(','), function (index, item) {
				if (i >= parseInt(item.split('|')[0])) discount = parseFloat(item.split('|')[1]);
			});
			price = price - discount;
		}

		var mult = 1;
		$("input[act='getmulti']").each(function () {
			mult = mult * parseInt($(this).val());
		});

		price = price * i * mult;
		count = count * i;
		if (count > 1) $('#need').val('ï¿¥' + price.toFixed(2) + "å…ƒ âž  " + count + "ä¸ª");
		else $('#need').val('ï¿¥' + price.toFixed(2) + "å…ƒ");
	});
	$("#num").keyup(function () {
		var i = parseInt($("#num").val());
		if (isNaN(i)) return false;
		var price = parseFloat($('#tid').attr('price'));
		var count = parseInt($('#tid').attr('count'));
		var prices = $('#tid').attr('prices');
		if (i < 1) $("#num").val(1);
		if (prices != '' || prices != 'null') {
			var discount = 0;
			$.each(prices.split(','), function (index, item) {
				if (i >= parseInt(item.split('|')[0])) discount = parseFloat(item.split('|')[1]);
			});
			price = price - discount;
		}

		var mult = 1;
		$("input[act='getmulti']").each(function () {
			mult = mult * parseInt($(this).val());
		});

		price = price * i * mult;
		count = count * i;
		if (count > 1) $('#need').val('ï¿¥' + price.toFixed(2) + "å…ƒ âž  " + count + "ä¸ª");
		else $('#need').val('ï¿¥' + price.toFixed(2) + "å…ƒ");
	});

	getPoint();
});