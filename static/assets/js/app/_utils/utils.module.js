(function () {
  'use strict';

  angular
    .module('slr.utils', [
      'ark-components',
      'ark-ui-bootstrap',
      'ui.select2',
      'ui.jq'
    ])
    .config(function ($httpProvider) {
      //initialize get if not there
      if (!$httpProvider.defaults.headers.get) {
        $httpProvider.defaults.headers.get = {};
      }
      //disable IE ajax request caching
      $httpProvider.defaults.headers.get['If-Modified-Since'] = '0';
      // flask needs this to detect AJAX request (via flask.request.is_xhr)
      $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
      //register custom interceptor
      $httpProvider.interceptors.push('myHttpInterceptor');
    })
})();