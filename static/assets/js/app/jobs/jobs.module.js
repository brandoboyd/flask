(function() {
  'use strict';

  angular.module('jobs', [
    'ui.router',
    
    'slr.services',
    'slr.utils',
    'slr.components',
    'slr.models',
  ])

  .value('uiJqConfig', {
    tooltip: {
        animation: false,
        placement: 'bottom',
        container: 'body'
    }
  });

})();