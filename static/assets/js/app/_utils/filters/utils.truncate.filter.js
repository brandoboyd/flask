(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('truncate', truncate);

  function truncate() {
    return function (text, length, end) {
      if (isNaN(length))
        length = 10;
      if (_.isUndefined(end)) {
        end = "...";
      }
      if (text && text.length <= length || text && text.length - end.length <= length) {
        return text;
      }
      else {
        return String(text).substring(0, length) + end;
      }
    };
  }
})();