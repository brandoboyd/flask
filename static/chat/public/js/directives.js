'use strict';
angular.module('chat.directives', []);

angular.module('chat.directives')
.directive('onFocus', function() {
  return {
    restrict: 'A',
    link: function(scope, el, attrs) {
      el.bind('focus', function() {
        scope.$apply(attrs.onFocus);
      });
    }
  };
})

.directive('onBlur', function() {
  return {
    restrict: 'A',
    link: function(scope, el, attrs) {
      el.bind('blur', function() {
        scope.$apply(attrs.onBlur);
      });
    }
  };
})

.directive('autoscroll', function () {
  return function(scope, element, attrs) {
    var pos = element[0].parentNode.parentNode.scrollHeight;
    $(element).parent().parent().animate({
      scrollTop : pos
    }, 1000);
  }
})

// Directive for dragging an element - currently used for chatbox
.directive('draggable', function() {
  return {
    restrict: 'A',
    link: function(scope, element, attrs) {
      var handler = $(element).children(attrs.draggable);
      $(element).draggable({
        containment: 'document',
        handle: handler,
        cursor: "move",
        drag: function() {
          $(element).css('height', 'auto');
          $(element).css('bottom', 'auto');
        }
      });

      // Watch window resize event
      $(window).resize(function() {
        var windowWidth = window.innerWidth,
            windowHeight = window.innerHeight,
            currentLeft = element.position().left,
            currentWidth = element.width(),
            currentTop = element.position().top,
            currentHeight = element.height();

        var right = windowWidth - (currentLeft + currentWidth),
            bottom = windowHeight - (currentTop + currentHeight);

        // If the chatbox is out of the browser window, reposition it
        if (right < 5) {
          element.css('left', 'auto');
          element.css('right', '5px');
        }
        if (bottom < 5) {
          element.css('top', 'auto');
          element.css('bottom', '5px');
        }
      });

    }
  };
})

/* Directive for collapse/expand button
  * show/hide the chatbox body on the button's click event
  * ensure the chatbox is not placed out of the browser window
  */
.directive('slideToggle', function() {
  return {
    restrict: 'A',
    scope: {
      expanded: '='
    },
    link: function(scope, element, attrs) {

      element.bind('click', function() {
        var content = $(attrs.slideToggle);
        var chatBox = content.parent();
        if(!scope.expanded) {
          content.removeClass('fading-out');
          content.addClass('fading-in');
        } else {
          content.removeClass('fading-in');
          content.addClass('fading-out');
        }

        // When user clicks collapse/expand button, check bottom css value and reposition the chatbox
        scope.$watch(function() {
            var windowHeight = window.innerHeight,
              currentTop = chatBox.position().top,
              currentHeight = chatBox.height();

            var bottom = windowHeight - (currentTop + currentHeight);
            return bottom;
          },
          function(newBottom) {
            if (newBottom < 5) {
              chatBox.css('top', 'auto');
              chatBox.css('bottom', '5px');
            }
          }
        );

      });
    }
  };
})
.directive('scrollBottom', function () {
    return {
        scope: {
            scrollBottom: "="
        },
        link: function (scope, element) {
            scope.$watchCollection('scrollBottom', function (newValue) {
                if (newValue)
                {
                    $(element).scrollTop($(element)[0].scrollHeight);
                }
            });
        }
    }
})
.directive('focusMe', function($timeout) {
    return {
        scope: { trigger: '@focusMe' },
        link: function(scope, element) {
            scope.$watch('trigger', function(value) {
                if(value === "true") {
                    $timeout(function() {
                        $(element)[0].focus();
                    });
                }
            }, true);
        }
    };
});