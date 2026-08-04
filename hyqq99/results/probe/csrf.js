(function() {
    'use strict';
    
    var csrfToken = '';
    if (typeof csrf_token !== 'undefined') {
        csrfToken = csrf_token;
    } else {
        console.warn('CSRF token not defined, CSRF protection may not work');
    }
    
    var noCsrfActions = ['getcount', 'getclass', 'gettool', 'gettoolnew', 'getleftcount', 'checklogin', 'getshuoshuo', 'getshareid', 'gift_start', 'query', 'order', 'cart_info', 'cart_list', 'captcha'];
    
    function shouldAddCsrfToken(url) {
        if (!url || url.indexOf('ajax.php') === -1) {
            return false;
        }
        
        var actMatch = url.match(/[?&]act=([^&]+)/);
        if (!actMatch) {
            return true;
        }
        
        var act = actMatch[1];
        return noCsrfActions.indexOf(act) === -1;
    }
    
    function addCsrfToData(data, csrfTokenValue) {
        if (!csrfTokenValue) {
            return data;
        }
        
        if (typeof data === 'string') {
            if (data.indexOf('csrf_token=') === -1) {
                var separator = (data.indexOf('?') !== -1 || data.indexOf('&') !== -1) ? '&' : '';
                data += separator + 'csrf_token=' + encodeURIComponent(csrfTokenValue);
            }
        } else if (typeof data === 'object' && data !== null) {
            if (data instanceof FormData) {
                if (!data.has('csrf_token')) {
                    data.append('csrf_token', csrfTokenValue);
                }
            } else if (data.constructor === Object) {
                if (!data.hasOwnProperty('csrf_token')) {
                    data.csrf_token = csrfTokenValue;
                }
            }
        }
        return data;
    }
    
    function interceptAjax() {
        if (typeof window.jQuery === 'undefined' || typeof window.jQuery.ajax === 'undefined') {
            if (typeof window.$ !== 'undefined' && typeof window.$.ajax !== 'undefined') {
                setupIntercept(window.$);
            } else {
                setTimeout(interceptAjax, 50);
            }
            return;
        }
        
        setupIntercept(window.jQuery);
        if (window.$ && window.$ !== window.jQuery) {
            setupIntercept(window.$);
        }
    }
    
    function setupIntercept($) {
        if ($.ajax._csrfIntercepted) {
            return;
        }
        
        var originalAjax = $.ajax;
        $.ajax = function(options) {
            if (!options) {
                options = {};
            }
            
            var url = options.url || '';
            var type = (options.type || 'GET').toUpperCase();
            var currentCsrfToken = typeof csrf_token !== 'undefined' ? csrf_token : csrfToken;
            
            if (type === 'POST' && shouldAddCsrfToken(url) && currentCsrfToken) {
                options.data = addCsrfToData(options.data, currentCsrfToken);
                
                if (!options.headers) {
                    options.headers = {};
                }
                if (!options.headers['X-CSRF-TOKEN']) {
                    options.headers['X-CSRF-TOKEN'] = currentCsrfToken;
                }
                
                var originalBeforeSend = options.beforeSend;
                options.beforeSend = function(xhr, settings) {
                    xhr.setRequestHeader('X-CSRF-TOKEN', currentCsrfToken);
                    if (originalBeforeSend) {
                        return originalBeforeSend.call(this, xhr, settings);
                    }
                };
            }
            
            return originalAjax.call(this, options);
        };
        $.ajax._csrfIntercepted = true;
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', interceptAjax);
    } else {
        interceptAjax();
    }
    
    window.addEventListener('load', function() {
        interceptAjax();
    });
    
    function initFormCsrf() {
        if (typeof $ !== 'undefined' && $.fn.on) {
            $(document).on('submit', 'form[method="post"], form:not([method])', function(e) {
                var $form = $(this);
                var action = $form.attr('action') || '';
                var method = ($form.attr('method') || 'GET').toUpperCase();
                
                if (method === 'POST' && (action.indexOf('ajax.php') !== -1 || shouldAddCsrfToken(action))) {
                    if ($form.find('input[name="csrf_token"]').length === 0) {
                        $form.append('<input type="hidden" name="csrf_token" value="' + csrf_token + '">');
                    }
                }
            });
        } else {
            setTimeout(initFormCsrf, 100);
        }
    }
    
    if (typeof $ !== 'undefined') {
        $(document).ready(initFormCsrf);
    } else {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initFormCsrf);
        } else {
            initFormCsrf();
        }
    }
})();

