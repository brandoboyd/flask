(function () {
  'use strict';

  angular
    .module('slr.services')
    .filter('markTopics', markTopics);

  // TODO: very specific filter, should be moved out of here
  function markTopics() {
    var quote = function (str) {
      return (str + '').replace(/([.?*+^$[\]\\(){}|-])/g, "\\$1");
    };
    RegExp.escape = function (s) {
      return s.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')
    };
    return function (text, filter, sa) {
      if (filter === undefined) {
        return text;
      } else {
        var topic, topics = _.pluck(filter, "content");
        var vote = filter[0].vote;
        var label_class = vote == 0 ? 'label' : vote == 1 ? 'label-voted-up' : 'label-voted-down';
        //var escaped_text = quote(text);
        topics = _.map(topics, function (el) {
          return RegExp.escape(el)
        });
        topic = topics.join("|");

        return text.replace(new RegExp('(' + topic + ')', 'img'),
          '<span sa_id=\"' + sa.speech_act_id + '\" class=\"' + label_class + " " + sa.type + '\">$&</span>');
      }
    };
  }
})();