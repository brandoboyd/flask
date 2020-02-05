(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('linky2', linky2);

  function linky2() {
    var URLregex = /(\b(https?:\/\/|www\.)\S*\w)/g;
    return function (input) {
      if (!input) return input;
      return input.replace(URLregex, function (s) {
        s = (s.indexOf('://') == -1) ? 'http://' + s : s;
        return '<a href="' + s + '" target="_blank" rel="nofollow">' + s + '</a>';
      });
    };
  }
})();