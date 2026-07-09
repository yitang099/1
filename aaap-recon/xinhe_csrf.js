(function() {
    'use strict';
    var noCsrfActions = ['getcount', 'getclass', 'gettool', 'gettoolnew', 'getleftcount', 'checklogin', 'getshuoshuo', 'getshareid', 'gift_start', 'query', 'order', 'cart_info', 'cart_list', 'captcha'];
    // order/query exempt from CSRF - enables unauthenticated IDOR brute force
})();
