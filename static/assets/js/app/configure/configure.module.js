(function () {
  'use strict';

  angular
    .module('slr.configure',
      [ 'ngRoute',
        'ngResource',
        'ngSanitize',
        'ngAnimate',
        'ng.jsoneditor',
        'ngFileUpload',
        'angular-svg-round-progress',
        'ui.select2',
        'ui.select',
        'ui.slimscroll',
        'ui.jq',
        'ark-ui-bootstrap',
        'ark-components',
        'ui.ace',
        'ui.bootstrap',
        'ui.bootstrap-slider',
        'infinite-scroll',

        'slr.components', 'mentio', 'xeditable'])
    .config(function ($routeProvider) {
      $routeProvider.otherwise({redirectTo: '/channels'});
    });
})();