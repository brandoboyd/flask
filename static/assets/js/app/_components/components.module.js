(function() {
  'use strict';

  angular
    .module('slr.components', [
      'slr.services',
      'slr.analysis',
      'slr.chart',
      'slr.horizontal-timeline',
      'slr.smart-tags-modal',
      'slr.date-range-dropdown',
      'slr.accounts-list',
      'slr.widget-dialog',
      'slr.facet-panel',
      'slr.ng-confirm'
    ]);

  angular.module('components', [
    'infinite-scroll',
  ]);

})();