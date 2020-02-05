(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .filter('getJourneyTagName', function () {
      return function (tag_ids, tagsList) {
        var arr = [];

        _.each(_.uniq(tag_ids), function (id) {
          var found = _.find(tagsList, {id: id});

          if (found) {
            arr.push(found.display_name);
          }
        });

        return arr.join(', ').toString();
      }
    })
})();