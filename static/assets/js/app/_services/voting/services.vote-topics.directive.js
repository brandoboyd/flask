(function () {
  'use strict';

  angular
    .module('slr.services')
    .directive('voteTopics', voteTopics);

  /** @ngInject */
  function voteTopics($filter, $resource, popOver, MyTopics) {
    var Feedback = $resource('/feedback/json', {}, {
      intention: {method: 'POST', isArray: false}
    });
    var doVote = function (label, direction) {
      $(label).removeClass('label');
      $(label).addClass('label-voted-' + direction);
      $(label).popover("destroy");
    };

    var normaliseText = function (content) {
      //remove space before punctuations
      var cnt = content.replace(/\s?([,!?])\s?/g, "$1 ");
      //no spaces around apostrophe
      cnt = cnt.replace(/\s*(['’])\s*/g, "$1");
      //space before only
      cnt = cnt.replace(/\s*([@#$])\s*/g, " $1");
      return cnt
    };
    var getTopics = function (el, topics, highlight) {
      //return (str+'').replace(/([.?*+^$[\]\\(){}|-])/g, "\\$1");
      var content = $filter('linky2')(el.content);

      if (topics.length > 0 && highlight) {
        return normaliseText($filter('markTopics')(content, topics, el));
      } else {
        return normaliseText(content);
      }
    };

    var btnUp, btnDown, close;
    btnUp = $("<button class='btn btn-success topic-vote-up'><i class='icon-thumbs-up'></i> vote up</button>");
    btnDown = $("<button class='btn btn-danger topic-vote-down' style='margin-left:10px'><i class='icon-thumbs-down'></i> vote down</button>");
    close = '<button class="close">&times;</button>';

    var preparePostText = function (rawPost, selected, highlight) {
      var text = '';
      _.each(rawPost.intentions, function (el, index) {
        var topics = _.filter(rawPost.topics, function (topic) {
          return topic.speech_act_id == el.speech_act_id
        });
        if (selected) {
          //console.log(selected);
          topics = _.filter(topics, function (topic) {
            return _.find(selected, function (el) {
              return topic.content.indexOf(el.topic) != -1
            })
          });
        }
        text += '<span position=\"' + index + '\" intention=\"' + el.type + '\">'
          + getTopics(el, topics, highlight)
          + '</span>';
      });
      return text;
    };
    var voteHandler = function (vote, el, post, s_id) {
      Feedback.intention({
        'post_id': post.id_str,
        'topic': el.text(),
        'speech_act_id': s_id,
        'vote': vote
      }, function (res) {
        doVote(popOver.get(), vote == -1 ? 'down' : 'up')
      }, function onError() {
        $(popOver.get()).popover("hide");
      });
    };
    return {
      link: function (scope, element, attrs) {
        scope.$watch(attrs.voteTopics, function (oldVal, newVal) {
          var myTopics = MyTopics.getSelected();
          if (myTopics.length == 0) {
            element.html(preparePostText(newVal, null, false));
          } else {
            element.html(preparePostText(newVal, MyTopics.getSelected(), true));
          }

          element.find('.label').popover({
            'trigger': 'manual',
            'title': '&nbsp;' + close,
            'content': function () {
              return btnUp.add(btnDown)
            },
            'placement': 'top',
            'html': true
          });
          var el, post, s_id;
          element.on('click', '.label', function () {
            el = angular.element(this);
            post = el.scope()['item']['post'] || el.scope()['item'];
            s_id = el.attr('sa_id');
            if (popOver.get()) {
              if (this !== popOver.get()) {
                $('.popover .close').trigger('click');
                $(this).popover('show');
                popOver.set(this);
              }
            } else {
              $(this).popover('show');
              popOver.set(this);
            }
          });
          element.on('click', '.close', function () {
            $(popOver.get()).popover("hide");
            popOver.set(null);
          });

          /*
           var voteDown = voteHandler(-1, el, post, s_id);
           var voteUp   = voteHandler(1, el, post, s_id);
           */
          //element.on('click', '.topic-vote-down', {vote:-1,el:el,post:post,s_id:s_id}, voteHandler);
          element.on('click', '.topic-vote-down', function () {
            voteHandler(-1, el, post, s_id);
          });
          element.on('click', '.topic-vote-up', function () {
            voteHandler(1, el, post, s_id);
          });

        }); // watch
      }
    }
  }
})();