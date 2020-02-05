(function () {
  'use strict';

  angular
    .module('slr.utils')
    // create the interceptor as a service, intercepts ALL angular ajax http calls
    .factory('myHttpInterceptor', myHttpInterceptor);

  /** @ngInject */
  function myHttpInterceptor($q, $log, $timeout, $rootScope, $injector) {
    var SystemAlert = function () {
        return $injector.get('SystemAlert');
      },
    //list of endpoints where we don't want to show loading message:
      exclude_loading_urls = [
        '/posts/json',
        '/posts/crosstag/json',
        '/error-messages/json',
        '/error-messages/count',
        '/smart_tags/json'
      ],
      exclude_error_urls = [
        '/twitter/users',
        '/predictors/expressions/validate',
        '/facet-filters/agent',
        '/facet-filters/customer'
      ],
      ON_JSON_BEING_FETCHED = 'onJsonBeingFetched',
      ON_JSON_FETCHED = 'onJsonFetched';

    function shouldShowErrorForUrl(url) {
      return (exclude_error_urls.indexOf(url) == -1);
    }

    function shouldShowLoadingForUrl(url) {
      return (exclude_loading_urls.indexOf(url) == -1);
    }

    function formatErrorResponse(resp) {
      var status = resp.status,
        method = resp.config.method,
        url = resp.config.url,
        params = resp.config.params || resp.config.data,
        data = resp.data;
      return [[method, url, status].join(' '), {requestParams: params, responseData: data}];
    }

    function showAlert(response) {
      var d = response.data,
        e = d.error || d.result || d.messages, // all possible error sources
        w = d.warn,
        ok = d.ok;
      if (ok === false && e) {
        var error = angular.isArray(e) ? e[0].message : e;
        if (shouldShowErrorForUrl(response.config.url)) {
          SystemAlert().error(error);
        }
        $log.error('response', formatErrorResponse(response), response);
      }
      if (ok === false && w) {
        var warn = angular.isArray(w) ? w[0].message : w;
        if (shouldShowErrorForUrl(response.config.url)) {
          SystemAlert().warn(warn);
        }
      }
      return {ok: ok, shown: (ok === false && (e || w))};
    }

    return {
      'request': function (config) {
        $rootScope.$broadcast(ON_JSON_BEING_FETCHED);
        // Don't show loading message automatically, will use explicitly
        // if (shouldShowLoadingForUrl(config.url)) {
        //   SystemAlert().showLoadingMessage();
        // }
        return config || $q.when(config);
      },

      'requestError': function (rejection) {
        $log.error('requestError', rejection);
        return $q.reject(rejection);
      },

      'response': function (response) {
        $rootScope.$broadcast(ON_JSON_FETCHED);
        $timeout(SystemAlert().hideLoadingMessage, 800);
        var alert = showAlert(response);
        return (alert.ok === false ? $q.reject(response) : response || $q.when(response));
      },

      'responseError': function (response) {
        SystemAlert().hideLoadingMessage();
        var alert = showAlert(response);
        if (response.status !== 0 && !alert.shown && shouldShowErrorForUrl(response.config.url)) {
          SystemAlert().error('Unknown error - failed to complete operation.');
        }
        if (response.status === 0 && response.data === ""
          && shouldShowErrorForUrl(response.config.url)
          && shouldShowLoadingForUrl(response.config.url)) {
          // network or cross-domain error
          var isFirefox = false;
          try { // workaround for #4010
            // Note: status=0 is also being set for cancelled requests,
            // and Firefox display those when pending ajax requests
            // are cancelled during page change.
            isFirefox = (navigator.userAgent.toLowerCase().indexOf('firefox') > -1);
          } catch (err) {
          }

          if (!isFirefox) {
            SystemAlert().error('Network error. Request has been rejected.');
          }
        }
        $log.error('responseError', response);
        return $q.reject(response);
      }
    };
  }
})();