(function () {
    'use strict';

    // TODO: Distribute to single services, and check on relevance
    angular
        .module('slr.services')
        .factory('StaffUsersService', StaffUsersService)
        .factory('AccountsService', AccountsService)
        .factory('AccountHelper', AccountHelper)
        .factory('ConfigureAccount', ConfigureAccount);

    /** @ngInject */
    function StaffUsersService($resource) {
        var resource = function makeResource(url, defaultParams, methods) {
            return $resource(url, defaultParams||{}, methods||{});
        };
        var r = resource('/users/staff/json', {}, {
            query: { method:'GET', isArray:false}
        });
        return r
    }

    /** @ngInject */
    function AccountsService($resource, $rootScope, ConfigureAccount) {
        var state = {
                list: [],
                current: null
            },
            service = {
                ACCOUNTS_EVENT: 'AccountsServiceEvent',
                getList: function() {
                    return state.list;
                },
                getCurrent: function() {
                    return state.current;
                },
                getCompactAccount: function() {
                    // Fetch minimum fields for dashboard use
                    var account = state.current;
                    var fields = ['id', 'name', 'selected_app', 'available_apps', 'configured_apps'];
                    if (account) {
                        return _.pick(account, fields);
                    } else {
                        return null;
                    }
                },
                switchAccountId: function(accountId, cb) {
                    //console.log(accountId);
                    if (!accountId) return;
                    var account = _.find(state.list, function(acc) { return acc.id === accountId; });
                    if (account) {
                        return this.switchAccount(account, cb);
                    }
                },
                switchAccount: function(account, cb) {
                    if (account && !account.is_current) {
                        ConfigureAccount.save({}, {account_id: account.id}, cb).$promise.then(function(){
                            _.forEach(state.list, function(acc){
                                acc.is_current = acc.id === account.id;
                                if (acc.is_current) {
                                    state.current = acc;
                                }
                            });
                            notify();
                        });
                    }
                }
            };

        function notify(params) {
            $rootScope.$emit(service.ACCOUNTS_EVENT, params);
            return params;
        }

        var AccountsResource = $resource('/accounts/:acct/json', {}, {
            query: {method:'GET', isArray:false},
            update:{method:'PUT', isArray:false},
            noAccount: {method: 'GET', params: {acct: 'no_account'}}
        });

        angular.extend(service, AccountsResource);
        service.query = function() {
            var r = AccountsResource.query.apply(AccountsResource, arguments);
            r.$promise.then(onResult);
            function onResult (res) {
                state.list = res.data;
                state.current = _.find(state.list, function(item) {return item.is_current;});
                notify();
                return res;
            }

            return r;
        };
        ['update', 'delete', 'save'].forEach(function(action){
            var originalRequest = service[action],
                wrappedRequest = function() {
                    var r = originalRequest.apply(service, arguments);
                    r.$promise.then(notify);
                    return r;
                };
            service[action] = wrappedRequest;
        });

        function findById (acc) {
            return _.find(state.list, function(a){return a.id === acc.id;});
        }

        service.accountUpdate = function(account, action) {
            if (!account || !account.id) {
                return;
            }
            var exists = findById(account);
            if (!exists) {
                // account created
                state.list.push(account);
            } else if (action == 'delete') {
                state.list.splice(state.list.indexOf(exists), 1);
            } else {
                // account updated
                angular.extend(exists, account);
            }
            notify();
        };

        return service;
    }

    /** @ngInject */
    function AccountHelper(FilterService) {
        var toOpt = function(v) {return {label: v, value: v}},
            accountTypeOptions = _.map([
                "Angel", "Native", "GSE", "HootSuite", "Salesforce", "Skunkworks", "OmniChannel"
            ], toOpt);

        return {
            // Datepicker options
            options: {
                end_date: {dateFormat:'mm/dd/yy',
                    formatDate:'mm/dd/yy',
                    minDate:new Date(+new Date()+24*60*60*1000)}
            },
            accountTypeOptions: accountTypeOptions,
            isExpired: function (account) {
                return account && account.end_date && (FilterService.getUTCDate(new Date(account.end_date)) < FilterService.getUTCDate(new Date()));
            }
        }
    }


    /** @ngInject */
    function ConfigureAccount($resource) {
        var AccountUpdateService = $resource('/configure/account_update/json', {}, {
                fetch: { method:'GET', isArray:false },
                update: { method:'POST', isArray:false }
            }),
            ConfigureAccountService = $resource('/configure/account/json'),
            ConfigureAccountUsers = $resource('/configure/account/userslist'),
            ConfigureAccountRemove = $resource('/configure/accounts/remove');

        return {
            fetch: AccountUpdateService.fetch,
            update: AccountUpdateService.update,
            save: ConfigureAccountService.save,
            removeUser: ConfigureAccountRemove.save,
            getUsers: ConfigureAccountUsers.get
        }
    };
})();
