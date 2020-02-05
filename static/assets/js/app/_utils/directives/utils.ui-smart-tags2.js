(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiSmartTags2', uiSmartTags2);

  /** @ngInject */
  function uiSmartTags2($compile, $timeout, $rootScope,
                        SmartTag, SmartTags, SmartTagForm, SystemAlert, ChannelsService) {
    return {
      template: '<a href="" ng-click="showTags()" class="hide-action"><i class="icon-tag-stat-add"></i> Add Tag</a>',
      replace: true,
      scope: {
        item: "="
        //channelId  : "@"
      },

      link: function (scope, elm) {
        scope.allSmartTags = [];
        scope.isTagsShown = false;
        scope.channelId = ChannelsService.getSelectedId();
        var channel = ChannelsService.getSelected();
        var post_id = scope.item.id_str;
        var el = null;
        var el_id = "sel_" + scope.$id;
        var stags = angular.element(elm).parent().next('.stags');
        var updateAvailableTags = function () {
          return SmartTags.fetch(scope.channelId, true).then(function (all_tags) {
            all_tags = _.filter(all_tags, function (tag) {
              return channel.type === tag.direction || tag.direction == 'any'
            });
            if (scope.item.smart_tags.length > 0) {
              scope.allSmartTags = _.filter(all_tags, function (el1) {
                return !_.find(scope.item.smart_tags, function (el2) {
                  return el1.id == el2.id
                });
              });
            } else {
              scope.allSmartTags = all_tags
            }
          });
        };

        elm.on("click", function (e) {
          e.stopPropagation();
        });

        // needed to be able to click through select2 drop mask
        $(document).on('mousedown', '#select2-drop-mask', function (e) {
          $('.dropdown.open').removeClass('open');
        });

        scope.$watch('item.smart_tags.length', function (nVal, oVal) {
          if (nVal != oVal) {
            updateAvailableTags();
          }
        });
        var addSmartTag = function (added_tag) {
          SmartTag.lru_tag = added_tag[0];
          $rootScope.$broadcast(SmartTag.LRU_TAG_CHANGED);
          SmartTags.addPostTags(scope.channelId, post_id, [added_tag[0].id]).then(function (res) {
            //scope.appliedTags.push(added_tag[0]);
            scope.item.smart_tags.push(added_tag[0]);
          });
        };
        var createAndApplyTag = function (new_tag) {

          if (new_tag.length > 17) {
            SystemAlert.warn("Sorry! You only get 17 characters to name your tag.");
            return null;
          }

          var defaults = SmartTagForm.getSmartTagDefaults();
          defaults.title = new_tag;
          defaults.description = new_tag;
          defaults.channel = scope.channelId;
          //defaults.keywords    = ['_XX_'];
          var tagItem = new SmartTag();
          tagItem = angular.extend(tagItem, defaults);

          //create a new tag
          return SmartTag.update(tagItem, function (res) {
            //update the list of available tags
            scope.$root.$broadcast(SmartTag.ON_SMARTTAG_UPDATE);
            //add the new tag to the post
            addSmartTag([res.item]);
          });
        };

        var s2_settings = {
          maximumInputLength: 17,
          formatNoMatches: function () {
            return "No smart tags available"
          }
        }
        scope.showTags = function () {
          var tagsTitles = _.pluck(scope.allSmartTags, 'title')
          updateAvailableTags();
          if (el == null) {
            el = $compile("<div post-smart-tags></div>")(scope);
            stags.append(el).ready(function () {
              $timeout(function () {
                angular.element('#' + el_id).select2(s2_settings);
                angular.element('#' + el_id).select2('open');
                angular.element('#' + el_id).on("change", function (e) {
                  var added_tag = _.filter(scope.allSmartTags, function (el) {
                      return el.id == e.val
                    }
                  );
                  if (added_tag.length > 0) {
                    addSmartTag(added_tag);
                  }
                  scope.$apply();
                  stags.hide();
                  scope.isTagsShown = false;
                });

                jQuery('input.select2-input').on('keydown', function (e) {
                  var oldValue = _.contains(tagsTitles, e.target.value);
                  if (e.keyCode == 13 && !oldValue && !(/^\s*$/).test(e.target.value)) {
                    //createAndApplyTag(e.target.value.trim());
                    angular.element('#' + el_id).select2('close');
                    stags.hide();
                    scope.isTagsShown = false;
                  } else {
                    return
                  }
                });
                angular.element("#select2-drop-mask").on("mousedown", function (e) {
                  angular.element('#' + el_id).select2("close");
                  stags.hide();
                  scope.isTagsShown = false;
                });
              }, 600, false);
            });
          }
          if (scope.isTagsShown) {
            angular.element('#' + el_id).select2('close');
            stags.hide();
            scope.isTagsShown = false;

          } else {
            updateAvailableTags().then(function () {
              stags.show(0, function () {
                angular.element('#' + el_id).select2('val', '');
                //angular.element('#' + el_id).select2(s2_settings);
                angular.element('#' + el_id).select2('open');
              });
              scope.isTagsShown = true;
            })
          }
        };
      }
    };
  }
})();