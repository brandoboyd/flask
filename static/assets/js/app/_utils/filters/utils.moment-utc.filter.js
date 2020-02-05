(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('momentutc', momentutc);

  // http://momentjs.com
  function momentutc() {
    return function (time, format) {
      if (format) {
        return moment.utc(time).format(format);
      } else {
        // returning moment object is not safe, because: moment.utc(aTimestamp) != moment.utc(aTimestamp)
        // if moment object were returned, angular will detect the returned value has changed even for same input
        // thereby recusively calling $digest cycle, eventually crashing with:
        // Error: $rootScope:infdig Infinite $digest Loop
        return moment.utc(time).toString();
      }
    };
  }
})();
