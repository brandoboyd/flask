(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('postSmartTags', postSmartTags);

  /** @ngInject */
  function postSmartTags() {
    var tpl = '<select id="sel_{{ $id }}" style="width:100%" data-placeholder="Pick a tag">' +
      '<option value=""></option>' +
      '<option ng-value="item.id" ng-repeat="item in allSmartTags">{{ item.title }}</option></select>';
    return {
      template: tpl,
      replace: true
    }
  }
})();