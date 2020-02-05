(function () {
  'use strict';

  angular
    .module('slr.services')
    .directive('intentionLabels', intentionLabels);

  // watch todo
  /** @ngInject */
  function intentionLabels($filter, popOver, $resource, FilterService) {
    var btnUp = $("<button class='btn btn-success btn-vote-up'><i class='icon-thumbs-up'></i> vote up</button>");
    var btnDown = $("<button class='btn btn-danger btn-vote-down'><i class='icon-thumbs-down'></i> vote down</button>");
    var close = "<button class='close'>&times;</button>";


    var highlight = function (node, intention, position) {
      var attr = '[intention="' + intention + '"]';
      var pos = '[position="' + position + '"]';
      var el = node.find(attr).filter(pos);
      var cl = "int-" + intention + " ilbl";
      //node.find('[intention]').removeClass();
      $(el).addClass(cl);
    };

    var deHighLight = function (textNode) {
      textNode.find('[intention]').removeClass();
    };
    var doVote = function (label, direction) {
      $(label).addClass('label-voted-' + direction);
      $(label).popover("destroy");
    };

    var Feedback = $resource('/feedback/json', {}, {
      intention: {method: 'POST', isArray: false}
    });
    return {
      restrict: 'A',
      replace: true,
      link: function (scope, element, attrs) {
        var tel, post, modal_body, intention, position;
        $(element).on('click', '.label', function (e) {
          tel = angular.element(this);
          post = tel.scope()['item']['post'] || tel.scope()['item'];
          modal_body = tel.parents("tr").next().find('.post-content');
          intention = tel.attr('intention');
          position = tel.attr('position');


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

          highlight(modal_body, intention, position);
        });

        $(element).on('click', '.close', function () {
          modal_body.find('[intention]').removeClass();
          $(popOver.get()).popover("hide");
          popOver.set(null);
        });

        $(element).on('click', '.btn-vote-down', function () {
          Feedback.intention({
            'post_id': post.id_str,
            'intention': intention,
            'speech_act_id': position,
            'vote': -1
          }, function () {
            doVote(popOver.get(), 'down');
            deHighLight(modal_body);
          }, function onError() {
            $(popOver.get()).popover("hide");
          });
        });
        $(element).on('click', '.btn-vote-up', function () {
          Feedback.intention({
            'post_id': post.id_str,
            'intention': intention,
            'speech_act_id': position,
            'vote': 1
          }, function () {
            doVote(popOver.get(), 'up');
            deHighLight(modal_body);
          }, function onError() {
            $(popOver.get()).popover("hide");
          });
        });


        scope.$watch(attrs.intentionLabels, function (newVal, oldVal) {
          var intentions = FilterService.getSelectedIntentions();
          _.each(newVal, function (v, i) {
            var el = angular.element('<span class="label"></span>');
            el.addClass(v.type);
            el.attr('position', i);
            //el.text($filter('check_label')(v.type) + " : " + v.score);
            el.text($filter('check_label')(v.type));
            el.attr('intention', v.type);
            if (intentions.length > 0 && _.contains(intentions, $filter('check_label')(v.type))) {
              el.addClass('hg');
            }

            el.popover({
              'title': '&nbsp;' + close,
              'trigger': 'manual',
              'content': function () {
                return btnUp.add(btnDown)
              },
              //'container' : 'body',
              'placement': 'top',
              'html': true,
              'index': i
            });

            if (newVal[i].vote != 0) {
              if (newVal[i].vote == -1) {
                doVote(el, "down");
              } else {
                doVote(el, "up");
              }
            }
            element.append(el);
          }); //each
        }); //watch
      } // link
    }; //return
  }
})();