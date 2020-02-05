/* ========================================================================
 * Bootstrap: popover.js v3.1.0
 * http://getbootstrap.com/javascript/#popovers
 * ========================================================================
 * Copyright 2011-2014 Twitter, Inc.
 * Licensed under MIT (https://github.com/twbs/bootstrap/blob/master/LICENSE)
 * ======================================================================== */


+function ($) {
  'use strict';

  // POPOVER PUBLIC CLASS DEFINITION
  // ===============================

  var Popover = function (element, options) {
    this.init('popover', element, options)
  }

  if (!$.fn.tooltip) throw new Error('Popover requires tooltip.js')

  Popover.DEFAULTS = $.extend({}, $.fn.tooltip.Constructor.DEFAULTS, {
    placement: 'right',
    trigger: 'click',
    arrow: 'top',
    content: '',
    close: 'show',
    template: '<div class="popover"><div class="arrow"></div><div class="popover-container"><span class="popover-close-btn fonticon icon-close"></span><div class="popover-body"><h3 class="popover-title"></h3><div class="popover-content"></div></div></div></div>',
    arrowOffset: 24,
    delay: 0
  })


  // NOTE: POPOVER EXTENDS tooltip.js
  // ================================

  Popover.prototype = $.extend({}, $.fn.tooltip.Constructor.prototype)

  Popover.prototype.constructor = Popover

  Popover.prototype.getDefaults = function () {
    return Popover.DEFAULTS
  }

  Popover.prototype.setContent = function () {
    var $tip    = this.tip()
    var title   = this.getTitle()
    var content = this.getContent()
    var $btn    = this

    $tip.find('.popover-title')[this.options.html ? 'html' : 'text'](title)

    this.updateCloseButton()

    //** Add close button functionality to Popover
    $tip.find('.popover-close-btn').on('click', function () {
      $btn.hide()
    })

    $tip.find('.popover-content')[ // we use append for html objects to maintain js events
      this.options.html ? (typeof content == 'string' ? 'html' : 'append') : 'text'
    ](content)

    $tip.removeClass('fade top bottom left right in')

    // IE8 doesn't accept hiding via the `:empty` pseudo selector, we have to do
    // this manually by checking the contents.
    if (!$tip.find('.popover-title').html()) $tip.find('.popover-title').hide()
  }

  Popover.prototype.hasContent = function () {
    return this.getTitle() || this.getContent()
  }

  Popover.prototype.getContent = function () {
    var $e = this.$element
    var o  = this.options

    return $e.attr('data-content')
      || (typeof o.content == 'function' ?
            o.content.call($e[0]) :
            o.content)
  }

  Popover.prototype.arrow = function () {
    return this.$arrow = this.$arrow || this.tip().find('.arrow')
  }

  Popover.prototype.tip = function () {
    if (!this.$tip) this.$tip = $(this.options.template)
    return this.$tip
  }


  // POPOVER PLUGIN DEFINITION
  // =========================

  var old = $.fn.popover

  $.fn.popover = function (option) {
    return this.each(function () {
      var $this   = $(this)
      var data    = $this.data('bs.popover')
      var options = typeof option == 'object' && option

      if (!data && option == 'destroy') return
      if (!data) $this.data('bs.popover', (data = new Popover(this, options)))
      if (typeof option == 'string') data[option]()
    })
  }

  $.fn.popover.Constructor = Popover


  // POPOVER NO CONFLICT
  // ===================

  $.fn.popover.noConflict = function () {
    $.fn.popover = old
    return this
  }

  // CUSTOM FUNCTIONS FOR POPOVER ARROW PLACEMENT
  // ============================================

  Popover.prototype.updateCloseButton = function() {
    var $closeButton = this.tip().find('.popover-close-btn')
    if (this.options.close === 'hide') {
      $closeButton.addClass('hidden')
    } else {
      $closeButton.removeClass('hidden')
    }
  }

  Popover.prototype.applyPlacement = function (offset, placement) {
    var replace
    var $tip   = this.tip()
    var width  = $tip[0].offsetWidth
    var height = $tip[0].offsetHeight

    var arrow = typeof this.options.arrow == 'function' ?
      this.options.arrow.call(this, $tip[0], this.$element[0]) :
      this.options.arrow

    // manually read margins because getBoundingClientRect includes difference
    var marginTop = parseInt($tip.css('margin-top'), 10)
    var marginLeft = parseInt($tip.css('margin-left'), 10)

    // we must check for NaN for ie 8/9
    if (isNaN(marginTop))  marginTop  = 0
    if (isNaN(marginLeft)) marginLeft = 0

    offset.top  = offset.top  + marginTop
    offset.left = offset.left + marginLeft

    // $.fn.offset doesn't round pixel values
    // so we use setOffset directly with our own function B-0
    $.offset.setOffset($tip[0], $.extend({
      using: function (props) {
        $tip.css({
          top: Math.round(props.top),
          left: Math.round(props.left)
        })
      }
    }, offset), 0)

    $tip.addClass('in')

    // check to see if placing tip in new offset caused the tip to resize itself
    var actualWidth  = $tip[0].offsetWidth
    var actualHeight = $tip[0].offsetHeight

    if (placement == 'top' && actualHeight != height) {
      replace = true
      offset.top = offset.top + height - actualHeight
    }

    if (/bottom|top/.test(placement)) {

      // find the arrow position
      arrow = arrow == 'left' || arrow == 'right' ? arrow : 'left'

      var delta = 0

      if (offset.left < 0) {
        delta       = offset.left * -2
        offset.left = 0

        $tip.offset(offset)

        actualWidth  = $tip[0].offsetWidth
        actualHeight = $tip[0].offsetHeight
      }

    } else {
      arrow = arrow == 'top' || arrow == 'bottom' ? arrow : 'top'
    }

    this.replaceArrow(arrow)

    if (replace) $tip.offset(offset)
  }

  Popover.prototype.replaceArrow = function (position) {
    this.arrow().addClass(position)
  }

  Popover.prototype.getCalculatedOffset = function (placement, pos, actualWidth, actualHeight) {

    // code copied from Tooltip
    var originalOffset = placement == 'bottom' ? { top: pos.top + pos.height,   left: pos.left + pos.width / 2 - actualWidth / 2  } :
           placement == 'top'    ? { top: pos.top - actualHeight, left: pos.left + pos.width / 2 - actualWidth / 2  } :
           placement == 'left'   ? { top: pos.top + pos.height / 2 - actualHeight / 2, left: pos.left - actualWidth } :
        /* placement == 'right' */ { top: pos.top + pos.height / 2 - actualHeight / 2, left: pos.left + pos.width   }

    var offsetValue

    var arrow = typeof this.options.arrow == 'function' ?
      this.options.arrow.call(this, $tip[0], this.$element[0]) :
      this.options.arrow

    var arrowOffset = typeof this.options.arrowOffset == 'function' ?
      this.options.arrowOffset.call(this, $tip[0], this.$element[0]) :
      this.options.arrowOffset

    if (/bottom|top/.test(placement)) {
      offsetValue = actualWidth / 2 > arrowOffset ? actualWidth / 2 - arrowOffset : 0
      originalOffset.left = arrow == 'right' ? 
        originalOffset.left - offsetValue :
        originalOffset.left + offsetValue 
    } else {
      offsetValue = actualHeight / 2 > arrowOffset ? actualHeight / 2 - arrowOffset : 0
      originalOffset.top = arrow == 'bottom' ?
        originalOffset.top - offsetValue :
        originalOffset.top + offsetValue
    }

    return originalOffset
  }
  
}(jQuery);
