(function () {
  'use strict';

  angular
    .module('slr.accounts-list')
    .directive('slrAccountsList', slrAccountsList);

  /** @ngInject */
  function slrAccountsList($rootScope, AccountsService) {
    return {
      restrict: 'EA',
      scope : {
        user : '='
      },
      replace: true,
      template: '<ul class="dropdown-menu" style="overflow-y: auto; max-height: 768px">' +
                '<li role="presentation" class="dropdown-header">Actions</li>' +
                '<li ng-if="(cur_account.is_admin) || (cur_account.is_analyst) || (cur_account.is_staff) || (cur_account.is_superuser)">' +
                '<a href="/configure#/channels">Settings</a></li>' +
                '<li ng-if="cur_account.is_only_agent && !cur_account.is_superuser">' +
                  '<a href="/users/{{ user.email }}/password">Settings</a></li>' +
                '<li class="divider"></li>' +
                '<li role="presentation" class="dropdown-header">Accounts</li>' +
                '<li ng-repeat="acct in accounts | orderBy:\'name\'"' +
                    'ng-class="{active: acct.is_current}">' +
                    '<a ng-href="/accounts/switch/{{acct.id}}"' +
                    'ng-bind="acct.name"></a>' +
                '</li>' +
                '<li class="divider"></li>' +
                '<li role="presentation" class="dropdown-header">Selected app</li>' +
                '<li ng-repeat="app_name in cur_account.configured_apps" ' +
                    'ng-class="{active: cur_account.selected_app === app_name}">' +
                  '<a href="/account_app/switch/{{ app_name }}">{{ app_name }}</a>' +
                '</li></ul>',
      link: function(scope) {
        $rootScope.$on(AccountsService.ACCOUNTS_EVENT, function () {
          scope.accounts    = AccountsService.getList();
          scope.cur_account = AccountsService.getCurrent();
        });

        AccountsService.query();        
      }
    }
  }
})();