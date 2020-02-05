(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('PackageDetailsMixin', PackageDetailsMixin);

  /** @ngInject */
  function PackageDetailsMixin() {
    var defaultPackageDetails = {
        'Bronze': false,
        'Silver': false,
        'Gold': false,
        'Platinum': false
      },
      mixin = {
        notInternalAccount: false,
        show_pricing_package_details: defaultPackageDetails,
        onPackageChange: onPackageChange
      };

    function onPackageChange(val) {
      if (!val) {
        return;
      }
      var self = this;
      self.notInternalAccount = val != 'Internal';
      _.forEach(self.show_pricing_package_details, function (val, key) {
        self.show_pricing_package_details[key] = false;
      });
      self.show_pricing_package_details[val] = true;
    }

    return mixin;
  }
})();