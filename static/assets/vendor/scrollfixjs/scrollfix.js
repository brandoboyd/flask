/**
 * ScrollFix 1.0.0
 * http://www.joelambert.co.uk
 * 
 * Edit by Michele Belluco
 *
 * Copyright 2011, Joe Lambert.
 * Free to use under the MIT license.
 * http://www.opensource.org/licenses/mit-license.php
 */

;(function(){

var ScrollFix = function(elem, direction) {
	var self = this;

	if (direction == undefined)
		direction = 'vertical';

	// Variables to track inputs
	self.direction = direction;
	self.startX = 0;
	self.startY = 0;
	self.startScrollTop = 0;
	self.startScrollLeft = 0;
	self.elem = elem || document.querySelector(elem);
	
	// If there is no element, then do nothing	
	if(!self.elem)
		return;

	self.onTouchStartHandler = function() {
		ScrollFix.prototype.onTouchStart.apply(self, arguments);
	}

	// Handle the start of interactions
	elem.addEventListener('touchstart', self.onTouchStartHandler, false);
};

ScrollFix.prototype.onTouchStart = function onTouchStart(event) {
	var elem = this.elem;
	var direction = this.direction;
	var startScrollTop = this.startScrollTop;
	var startScrollLeft = this.startScrollLeft;

	if (direction == 'vertical') {
		// Y
		this.startY = event.touches[0].pageY;
		startScrollTop = elem.scrollTop;

		if (startScrollTop <= 0)
			elem.scrollTop = 1;

		if (startScrollTop + elem.offsetHeight >= elem.scrollHeight)
			elem.scrollTop = elem.scrollHeight - elem.offsetHeight - 1;

		if (elem.scrollHeight == elem.offsetHeight)
			event.preventDefault();
	}

	if (direction == 'horizontal') {
		// X
		this.startX = event.touches[0].pageX;
		startScrollLeft = elem.scrollLeft;

		if (startScrollLeft <= 0)
			elem.scrollLeft = 1;

		if (startScrollLeft + elem.offsetWidth >= elem.scrollWidth)
			elem.scrollLeft = elem.scrollWidth - elem.offsetWidth - 1;
	}
}

ScrollFix.prototype.destroy = function destroy() {
	this.elem.removeEventListener('touchstart', this.onTouchStartHandler, false);
}



// AMD / RequireJS
if (typeof define !== 'undefined' && define.amd) {
    define([], function () {
        return ScrollFix;
    });
}
// Node.js
else if (typeof module !== 'undefined' && module.exports) {
    module.exports = ScrollFix;
}
// included directly via <script> tag
else {
    window.ScrollFix = ScrollFix;
}


})();