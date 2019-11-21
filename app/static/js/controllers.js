'use strict';
angular.module('Portal.controllers', ['Portal.services', 'Portal.configuration'])
  .controller('LoginController', ['$scope', '$location', '$http', 'Auth', 'BOSH', function ($scope, $location, $http, Auth, BOSH) {
    $scope.credentials = {email: '', password: ''};
    $scope.login = function () {
      Auth.login($scope.credentials).success(function () {
        /*$http.get('/auth/bosh-session').then(
                    function(resp){
                        if(resp.status === 200){
                            BOSH.attach(resp.data);
                        }
                    }, function(error){

                    }
                );*/
        $location.path('/organizations');

      });
    };
  }])
  .controller('HeaderController', ['$scope', '$location', 'Auth', 'BOSH', function($scope, $location, Auth, BOSH){
    $scope.isLoggedIn = Auth.isLoggedIn();
    $scope.logout = function () {
      BOSH.disconnect();
      Auth.logout().success(function () {
        $location.path('/login');
      });
    };
  }])
  .controller('OrganizationGroupsController', ['$scope', '$uibModal', function($scope, $uibModal){
    $scope.editGroup = function(size, group){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal-group-edit.html',
        controller: 'OrganizationGroupEditController',
        backdrop: 'static',
        size: size,
        resolve: {
          group: function(){
            return group;
          }
        }
      });
      modalInstance.result.then(function (group) {
        if(group){
          $scope.groups.unshift(group);
        }
      }, function () {
        // modal dismissed, do cleanup
      });
    };
  }])
  .controller('OrganizationGroupEditController', ['$scope', '$uibModalInstance', 'group', 'GridData', function($scope, $uibModalInstance, group, GridData){
    $scope.group = group;
    $scope.save = function(o){
      GridData('organization_groups').update(o, function(resp){
        $uibModalInstance.close(resp.organization_group);
      }, function(error){
        $scope.msg = error.data.message;
      });
    };
    $scope.cancel = function(){
      $uibModalInstance.dismiss('cancel');
    };
  }])
  .controller('VulnerabilityEditController', ['$scope', '$state', '$stateParams', '$filter', 'Organization', 'GridData', 'notifications', function($scope, $state, $stateParams, $filter, Organization, GridData, notifications){
    $scope.tags = [];
    Organization.query(function(resp){
      $scope.organizations = $filter('filter')(
        resp.organizations,
        function(v, idx){
          return v.group_id === 1;
        }
      );
    });
    GridData('tags').query(function(resp){
      for(var idx in resp.tags){
        $scope.tags.push(resp.tags[idx].name);
      }
    });
    if($stateParams.id !== undefined){
      $scope.vuln = GridData('vulnerabilities').get({id: $stateParams.id});
    }

    $scope.save = function(vuln){
      GridData('vulnerabilities').update(vuln, function(resp){
        notifications.showSuccess(resp);
        $state.go('vulnerabilities');
      }, function(error){
        notifications.showError(error.data);
      });
    };

    $scope.cancel = function(){
      $state.go('vulnerabilities');
    };
  }])
  .controller('OrganizationEditController', ['$scope', '$state', '$filter', '$stateParams','$uibModal', 'Organization', 'GridData', 'Auth', 'notifications', function($scope, $state, $filter, $stateParams, $uibModal, Organization, GridData, Auth, notifications){
    var groups = GridData('organization_groups').query(function(){
      $scope.groups = groups.organization_groups;
    });
    if($stateParams.id !== undefined){
      Organization.get({id: $stateParams.id}, function(resp){
        $scope.org = resp;
        $scope.fuzzed = [];
        angular.forEach(resp.fqdns, function(val, key){
          GridData('fqdns').query({'id': val}, function(resp){
            $scope.fuzzed[val] = resp.typosquats;
          });
        });
      });
    }

    $scope.toggleTyposquatsList = function(list, parent){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal-list-typosquats.html',
        controller: 'TyposquatsController',
        size: 'lg',
        resolve: {
          fqdns: function(){
            return list;
          },
          parent: function(){
            return parent;
          }
        }
      });
      modalInstance.result.then(function (resp) {
        //success
      }, function () {
        // modal dismissed, do cleanup
      });
    };

    $scope.appendItem = function(type, org){
      if(org.hasOwnProperty(type)){
        org[type].unshift('');
      }else{
        org[type] = ['']
      }
    };
    $scope.removeItem = function(type, org, val){
      org[type] = $filter('filter')(
        org[type],
        function(v){
          return v !== val;
        }
      );
    };

    $scope.cpAccess = function(org, contactEmail){
      var newAccount = {
        organization_id: org.id,
        name: org.abbreviation + ' (' + contactEmail + ')',
        email: contactEmail
      };
      Auth.registerCPAccount(newAccount).then(function(resp){
        notifications.showSuccess(resp.data);
        Organization.get({id: $stateParams.id}).$promise.then(function(resp){
          $scope.org = resp;
        });
      }, function(error){
        notifications.showError(error.data);
      });
    };
    $scope.cpRevokeAccess = function(org, contactEmail){
      var unregAccount = {
        organization_id: org.id,
        name: org.abbreviation + ' (' + contactEmail + ')',
        email: contactEmail
      };
      Auth.unregisterCPAccount(unregAccount).then(function(resp){
        notifications.showSuccess(resp.data);
        Organization.get({id: $stateParams.id}).$promise.then(function(resp){
          $scope.org = resp;
        });
      }, function(error){
        notifications.showError(error.data);
      });
    };

    $scope.save = function(o){
      Organization.update(o, function(resp){
        notifications.showSuccess(resp);
      }, function(error){
        notifications.showError(error.data);
      });
    };
    $scope.cancel = function(){
      $state.go('organizations');
    };
  }])
  .controller('TyposquatsController', ['$scope', '$uibModalInstance', 'fqdns', 'parent', function($scope, $uibModalInstance, fqdns, parent){
    $scope.fqdns = fqdns;
    $scope.parentFQDN = parent;

    $scope.exportCSV = function(){
      var header = ['typosquat', 'dns_a', 'dns_ns', 'dns_mx', 'updated'];
      var rv = [header];
      $scope.exportDate = new Date().getTime();
      angular.forEach($scope.fqdns, function(fqdn, key){
        var entry = [];
        angular.forEach(fqdn, function(v, k){
          var keyIndex = header.indexOf(k);
          if(keyIndex !== -1){
            entry[keyIndex] = v;
          }
        });
        rv.push(entry);
      });
      return rv;
    };
    $scope.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
  }])
  .controller('DeliverablesController', ['$scope', function($scope){

  }])
  .controller('DeliverableFilesController', ['$scope', '$log', '$uibModal', 'GridData', 'notifications', 'apiConfig', function($scope, $log, $uibModal, GridData, notifications, apiConfig){
    $scope.webServiceUrl = apiConfig.urlPrefix;
    $scope.uploadFiles = function(size){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal-files-upload.html',
        controller: 'DeliverableFilesUploadController',
        backdrop: 'static',
        size: size
      });
      modalInstance.result.then(function () {
        $scope.loadPage($scope.currentPage);
      }, function () {
        // modal dismissed, do cleanup
        $scope.loadPage($scope.currentPage);
      });
    };
    $scope.pageChanged = function(){
      //$log.log('Page changed to: ' + $scope.currentPage);
      $scope.loadPage($scope.currentPage);
    };
    $scope.deleteFile = function(fobj){
      GridData('files').delete({id: fobj.id}, function(resp){
        $scope.loadPage($scope.currentPage);
      }, function(error){

      });
    };
    $scope.loadPage = function(no){
      if(no === undefined){
        no = 1;
      }
      GridData('files').query({page: no}, function(resp){
        $scope.files = resp.items;
        $scope.totalItems = resp.count;
        $scope.currentPage = resp.page;
      }, function(err){
        notifications.showError(err);
      });
    };
    $scope.loadPage();

  }])
  .controller('SamplesController', ['$scope', '$uibModal', 'GridData', 'notifications', 'apiConfig', function($scope, $uibModal, GridData, notifications, apiConfig){
    $scope.webServiceUrl = apiConfig.urlPrefix;

    $scope.pageChanged = function(){
      //$log.log('Page changed to: ' + $scope.currentPage);
      $scope.loadPage($scope.currentPage);
    };
    $scope.deleteFile = function(fobj){
      GridData('files').delete({id: fobj.id}, function(resp){
        $scope.loadPage($scope.currentPage);
      }, function(error){

      });
    };
    $scope.loadPage = function(no){
      if(no === undefined){
        no = 1;
      }
      GridData('samples').query({page: no}, function(resp){
        $scope.files = resp.items;
        $scope.totalItems = resp.count;
        $scope.currentPage = resp.page;
      }, function(err){
        notifications.showError(err);
      });
    };
    $scope.loadPage();

  }])
  .controller('SamplesUploadController', ['$scope', '$timeout', '$log', '$location', 'GridData', 'notifications', function($scope, $timeout, $log, $location, GridData, notifications){

    $scope.files = [];
    $scope.submitEnvs = [];
    $scope.sampleActions = {
      av_scan: true,
      static_analysis: true,
      dynamic_analysis: {
        fireeye: {
          'win10x64m': true
        }
      }
    };

    $scope.save = function(){
      GridData('analysis/static').save({files: $scope.files});
      GridData('analysis/av').save({files: $scope.files}, function(resp){
        notifications.showSuccess(resp);
        $scope.files = [];
        $scope.$broadcast('clear-files');
        $location.path('/samples');
        //$log.debug('start scan... redirect to results page');
      }, function(error){
        notifications.showError(error.data);
      });

      var feAnalysisAvailable = $scope.sampleActions.dynamic_analysis.fireeye;
      var feEnvs = [];
      for (var k in feAnalysisAvailable){
        if(feAnalysisAvailable[k]){
          feEnvs.push(k);
        }
      }
      var dynAnalysis = {
        files: $scope.files,
        dyn_analysis: {
          fireeye: feEnvs
        }
      };

      GridData('analysis/fireeye').save(dynAnalysis,
        function(resp) {
          for(var i in resp.statuses) {
            var st = resp.statuses[i];
            if(st.hasOwnProperty('error')) {
              notifications.showError(st.error);
            } else if (st.hasOwnProperty('sha256')) {
              notifications.showSuccess(st.sha256 + ' has been submitted for dynamic analysis');
            }
          }
        },
        function(err) {
          notifications.showError(err.data);
        }
      );
    };

    $scope.$on('files-uploaded', function(event, files){
      $scope.files = $scope.files.concat(files);
      $scope.canSave = true;
    });

    $scope.$on('upload-error', function(event, error){
      $scope.msg = error;
    });

    $scope.engines = GridData('analysis/av').get({id: 'engines'});

    GridData('analysis/fireeye/environments').get(
      function(resp){
        $scope.feenvs = resp.environments;
      },
      function(err){
        notifications.showError(err.data);
      }
    );

  }])
  .controller('URLsUploadController', ['$scope', '$timeout', '$log', '$location', 'GridData', 'notifications', function($scope, $timeout, $log, $location, GridData, notifications){

    $scope.urls = '';
    $scope.urls_ = [];
    $scope.sampleActions = {
      av_scan: true,
      static_analysis: true,
      dynamic_analysis: {
        fireeye: {
          'win10x64m': true
        }
      }
    };

    $scope.save = function() {
      var feAnalysisAvailable = $scope.sampleActions.dynamic_analysis.fireeye;
      var feEnvs = [];
      for (var k in feAnalysisAvailable){
        if(feAnalysisAvailable[k]){
          feEnvs.push(k);
        }
      }

      $scope.urls_ = $scope.urls.split('\n');

      var dynAnalysis = {
        urls: $scope.urls_,
        dyn_analysis: {
          fireeye: feEnvs
        }
      };

      GridData('analysis/fireeye-url').save(dynAnalysis, function(resp) {
        for(var i in resp.statuses){
          var st = resp.statuses[i];
          if(st.hasOwnProperty('error')){
            notifications.showError(st.error);
          }else if(st.hasOwnProperty('sha256')){
            notifications.showSuccess(
              $scope.urls_[i] + ' has been submitted for dynamic analysis');
          }
        }
      }, function(error){
        notifications.showError(error.data);
      });
    };

    GridData('analysis/fireeye/environments').get(
      function(resp) {
        $scope.feenvs = resp.environments;
      },
      function(err) {
        notifications.showError(err.data);
      }
    );

  }])
  .controller('DeliverableFilesUploadController', ['$scope', '$uibModalInstance', '$timeout', 'GridData', 'notifications', function($scope, $uibModalInstance, $timeout, GridData, notifications){
    var types = GridData('deliverables').query(function(){
      $scope.types = types.deliverables;
    });
    // needs to be initialized before it can be set in the template
    $scope.deliverable = {};
    $scope.files = [];

    $scope.save = function(){
      GridData('files').save({
        deliverable_id: $scope.deliverable.selected.id,
        is_sla: $scope.deliverable.is_sla,
        files: $scope.files}, function(resp){
        $uibModalInstance.close(resp);
        notifications.showSuccess(resp);
        $scope.deliverable = {};
        $scope.files = [];
        $scope.$broadcast('clear-files');
      }, function(error){
        $scope.msg = error.data.msg;
      });
    };
    $scope.cancel = function(){
      $uibModalInstance.dismiss('cancel');
    };
    $scope.$on('files-uploaded', function(event, files){
      $scope.files = $scope.files.concat(files);
      $scope.canSave = true;
    });

  }])
  .controller('FileUploadController', ['$scope', '$timeout', 'apiConfig', 'Upload', function($scope, $timeout, apiConfig, Upload){
    $scope.uploadPath = '/upload';
    $scope.uploadFiles = function (files) {
      $scope.files = files;
      if (files && files.length) {
        $scope.upload_progress = 0;
        Upload.upload({
          url: apiConfig.urlPrefix + $scope.uploadPath,
          data: {
            files: files
          }
        }).then(function (response) {
          $timeout(function () {
            $scope.result = response.data;
            $scope.$emit('files-uploaded', response.data.files);
          });
        }, function (response) {
          if (response.status > 0) {
            $scope.msg = response.status + ': ' + response.statusText;
            $scope.$emit('upload-error', $scope.msg);
          }
        }, function (evt) {
          $scope.upload_progress =
            Math.min(100, parseInt(100.0 * evt.loaded / evt.total));
        });
      }
    };
    $scope.discardFiles = function(){
      $scope.$broadcast('clear-files');
    };
    $scope.$on('clear-files', function(event){
      delete $scope.files;
      delete $scope.upload_progress;
      $scope.$emit('files-cleared');
    });

  }])
  .controller('ListArchiveController', ['$scope', function($scope){

  }])
  .controller('ListsComposeController', ['$scope', '$filter', 'List', 'notifications', function($scope, $filter, List, notifications){
    var data = List.query(function(resp){
      $scope.lists = data.lists;
    });
    $scope.msg = {encrypted: true};
    $scope.msg.files = [];
    $scope.list = {};
    $scope.onListSelect = function(){
      $scope.msg.list_id = $scope.list.selected.id;
    };
    $scope.send = function(){
      List.post($scope.msg, function(resp){
        notifications.showSuccess(resp);
        $scope.msg = {encrypted: true};
        $scope.msg.list_id = $scope.list.selected.id;
        $scope.msg.files = [];
        $scope.$broadcast('clear-files');
      }, function(error){
        notifications.showError(error.data);
      });
    };
    $scope.$on('files-uploaded', function(event, files){
      $scope.msg.files = $scope.msg.files.concat(files);
    });
    $scope.$on('files-cleared', function(event){
      $scope.msg.files = [];
    });

    $scope.checkGPG = function(list_id){
      List.check_gpg({id: list_id}, function(resp){
        notifications.showSuccess(resp);
      }, function(error){
        notifications.showError(error.data);
        if(error.data.stderr){
          notifications.showError({
            message: error.data.stderr,
            hideDelay: 7000
          });
        }
      });
    };
  }])
  .controller('ListsController', ['$scope', '$filter', '$uibModal', 'List', 'notifications', function($scope, $filter, $uibModal, List, notifications){
    $scope.loadLists = function(){
      var data = List.query(function(resp){
        $scope.lists = data.lists;
      }, function(error){
        notifications.showError(error.data);
      });
    };
    $scope.loadLists();
    $scope.addList = function(size){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal-list-add.html',
        controller: 'ListsAddController',
        backdrop: 'static',
        size: size
      });
      modalInstance.result.then(function (resp) {
        notifications.showSuccess(resp);
        $scope.loadLists();
      }, function () {
        // modal dismissed, do cleanup
      });
    };
    $scope.toggleMembersList = function(list){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal_list_memberslist.html',
        controller: 'ListsMembersController',
        backdrop: 'static',
        size: 'lg',
        resolve: {
          list: function(){
            return list;
          }
        }
      });
      modalInstance.result.then(function (resp) {
        //success
      }, function () {
        // modal dismissed, do cleanup
      });
    };

    $scope.massSubscribe = function(list){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal-list-mass-sub-unsub.html',
        controller: 'ListMassSubscribeController',
        backdrop: 'static',
        size: 'lg',
        resolve: {
          list: function(){
            return list;
          }
        }
      });
      modalInstance.result.then(function (resp) {
        notifications.showSuccess(resp);
        $scope.loadLists();
      }, function () {
        // modal dismissed, do cleanup
      });
    };

    $scope.lists = [];
    $scope.toggleEditMode = function(l){
      l.active = !l.active;
      if(!l.active && !l.name){
        $scope.lists = $filter('filter')(
          $scope.lists,
          function(v, idx){
            return v.$$hashKey !== l.$$hashKey;
          }
        );
      }
    };
    $scope.deleteItem = function(l){
      List.delete({id: l.id}, function(resp){
        $scope.lists = $filter('filter')(
          $scope.lists,
          function(v, idx){
            return v.id !== l.id;
          }
        );
      }, function(error){
        notifications.showError(error.data);
      });
    };
  }])
  .controller('ListsAddController', ['$scope', '$uibModalInstance', 'List', function($scope, $uibModalInstance, List){
    $scope.save = function(l){
      List.update(l, function(resp){
        $uibModalInstance.close(resp);
      }, function(error){
        $scope.msg = error.data.message;
      });
    };
    $scope.cancel = function(){
      $uibModalInstance.dismiss('close');
    };
  }])
  .controller('ListEditController', ['$scope', '$stateParams', '$filter', '$uibModal', 'ErrorMapper', 'List', 'GridData', 'notifications', function($scope, $stateParams, $filter, $uibModal, ErrorMapper, List, GridData, notifications){
    $scope.list = List.get({id: $stateParams.id});
    $scope.e = {};
    $scope.list.members = [];
    $scope.loadEmails = function(){
      $scope.list.members = [];
      List.get({id: $stateParams.id}).$promise.then(function(list){
        $scope.list = list;
        return GridData('emails').query().$promise;
      })
        .then(function(resp){
          $scope.emails = resp.emails;
          var members = [];
          $scope.list.members.forEach(function(item){
            members.push(item.email);
          });
          //debugger;
          $scope.emails = $filter('filter')(
            $scope.emails,
            function(v, idx){
              return members.indexOf(v.email) === -1;
            }
          );
        });
    };
    $scope.loadEmails();
    $scope.$on('subscribers-updated', function(){
      $scope.loadEmails();
    });

    // similar to massSubscribe() from ListsController
    // see how they can be merged
    $scope.massSubscribe = function(list){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal-list-mass-sub-unsub.html',
        controller: 'ListMassSubscribeController',
        backdrop: 'static',
        size: 'lg',
        resolve: {
          list: function(){
            return list;
          }
        }
      });
      modalInstance.result.then(function (resp) {
        notifications.showSuccess(resp);
        $scope.list = List.get({id: $stateParams.id});
      }, function () {
        // modal dismissed, do cleanup
      });
    };

    $scope.submitKeyModal = function(email){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal-list-submit-key.html',
        controller: 'ListsSubmitKeyController',
        backdrop: 'static',
        size: 'lg',
        resolve: {
          email: function(){
            return email;
          }
        }
      });
      modalInstance.result.then(function (resp) {
        //success
        $scope.list = List.get({id: $stateParams.id});
      }, function () {
        // modal dismissed, do cleanup
      });
    };

    $scope.searchKeyModal = function(email){
      var modalInstance = $uibModal.open({
        templateUrl: '/static/views/modal-list-search-key.html',
        controller: 'ListsSearchKeyController',
        backdrop: 'static',
        size: 'lg',
        resolve: {
          email: function(){
            return email;
          }
        }
      });
      modalInstance.result.then(function (resp) {
        //success
        $scope.loadEmails();
      }, function () {
        // modal dismissed, do cleanup
      });
    };

    $scope.update = function(list){
      List.update(list, function(resp){
        notifications.showSuccess(resp);
      }, function(error){
        notifications.showError(error.data);
      });
    };
    /*
        subscribe & unsubscribe endpoints accept single emails or list of
        emails. Using both here for exemplification.
        */
        $scope.subscribe = function(subscriber){
            List.subscribe({id: $stateParams.id}, subscriber, function(resp){
                if($scope.list.members !== undefined){
                    $scope.list.members.unshift(subscriber);
                }else{
                    $scope.list.members = [subscriber];
                }
                $scope.$emit('subscribers-updated');


            }, function(error){
                notifications.showError(error.data);
            });
        };
        $scope.unsubscribe = function(subscribers){
            List.unsubscribe({id: $stateParams.id}, subscribers, function(resp){
                $scope.list.members = $filter('filter')(
                    $scope.list.members,
                    function(v, idx){
                        return subscribers.indexOf(v.email) === -1;
                    }
                );
                $scope.$emit('subscribers-updated');
            }, function(error){
                notifications.showError(error.data);
            });
        };
    }])
    .controller('ListSettingsController', ['$scope', '$stateParams', 'List', 'notifications', function($scope, $stateParams, List, notifications){
        $scope.list = List.get({id: $stateParams.id});
        $scope.update = function(list){
            List.update(list, function(resp){
                notifications.showSuccess(resp);
            }, function(error){
                notifications.showError(error.data);
            });
        };
    }])
    .controller('ListsSearchKeyController', ['$scope', '$uibModalInstance', '$http', 'email', function($scope, $uibModalInstance, $http, email){
        $scope.email = email;
        $http.post('/api/1.0/search-keys', {email: $scope.email})
            .then(
                function(response){
                    $scope.gpgkeys = response.data.keys;
                },
                function(error){
    // local message, displayed in the overlayed modal
                    $scope.msg = error.data.msg;
                }
            );
        $scope.importKey = function(gpgkeys){
            $http.post('/api/1.0/import-keys', {keys: gpgkeys})
                .then(
                    function(response){
                        $uibModalInstance.close(response);
                    },
                    function(error){
    // local message, displayed in the overlayed modal
                        $scope.msg = error.data.msg;
                    }
                );
        };
        $scope.close = function(){
            $uibModalInstance.dismiss('close');
        };
    }])
    .controller('ListsSubmitKeyController', ['$scope', '$uibModalInstance', '$http', function($scope, $uibModalInstance, $http){
        $scope.submitKey = function(){
            $http.put('/api/1.0/submit-key', {ascii_key: $scope.key_data})
                .then(
                    function(response){
                        $uibModalInstance.close(response);
                    },
                    function(error){
    // local message, displayed in the overlayed modal
                        $scope.msg = error.data.msg;
                    }
                );
        };
        $scope.close = function(){
            $uibModalInstance.dismiss('close');
        }
    }])
    .controller('ListsMembersController', ['$scope', '$uibModalInstance', '$filter', 'list', 'List', 'notifications', function($scope, $uibModalInstance, $filter, list, List, notifications){
        $scope.list = list;
        $scope.unsubscribe = function(list, subscribers){
            List.unsubscribe({id: list.id}, subscribers, function(resp){
                $scope.list.members = $filter('filter')(
                    $scope.list.members,
                    function(v, idx){
                        return subscribers.indexOf(v.email) === -1;
                    }
                );
            }, function(error){
                notifications.showError(error.data);
            });
        };
        $scope.cancel = function(){
            $uibModalInstance.dismiss('cancel');
        };
    }])
    .controller('ListMassSubscribeController', ['$scope', '$uibModalInstance', 'FileReader', 'list', 'List', 'ErrorMapper', function($scope, $uibModalInstance, FileReader, list, List, ErrorMapper){
        $scope.emails = "";
        $scope.list = list;
        $scope.getFile = function (file) {
            FileReader.readAsText(file, $scope)
                .then(function (result) {
                    var csv = result.split(/\r\n|\r|\n|,/g);
    //$scope.emails_arr = csv;
                    $scope.emails = csv.join('\n');
                });
        };
        $scope.bulkSubscribe = function(){
            var emails = $scope.emails.split(/\r\n|\r|\n|,/g);
            List.subscribe({id: list.id}, {'emails': emails}, function(resp){
                $uibModalInstance.close(resp);
            }, function(error){
    // local message, displayed in the overlayed modal
                if(error.data instanceof Object){
                    $scope.msg = ErrorMapper.map(error.data);
                }else {
                    $scope.msg = error.data.msg;
                }
            });
        };
        $scope.bulkUnsubscribe = function(){
            var emails = $scope.emails.split(/\r\n|\r|\n|,/g);
            List.unsubscribe({id: list.id}, emails, function(resp){
                $uibModalInstance.close(resp);
            }, function(error){
                if(error.data instanceof Object){
                    $scope.msg = ErrorMapper.map(error.data);
                }else {
                    $scope.msg = error.data.msg;
                }
            });
        };

        $scope.close = function(){
            $uibModalInstance.dismiss('close');
        };

    }])
    .controller('BulkAHProcessController', ['$scope', function($scope){

    }])
    .controller('BulkIPCheckController', ['$scope', 'FileReader', 'Organization', 'notifications', function($scope, FileReader, Organization, notifications){
        $scope.ips = "212.8.189.19\n1.2.3.4\n136.173.80.72";
        $scope.getFile = function (file) {
            $scope.fileProgress = 0;
            FileReader.readAsText(file, $scope)
                .then(function (result) {
                    var csv = result.split(/\r\n|\r|\n|,/g);
    //$scope.ips_array = csv;
                    $scope.ips = csv.join('\n');
                });
        };
        $scope.check = function(){
            $scope.showSpinner = true;
            var results = Organization.check({}, $scope.ips.trim().split('\n'), function(resp){
                $scope.responses = results.response;
                $scope.showSpinner = false;
            }, function(error){
                var msg = error.data;
                msg.hide = false;
                notifications.showError(msg);
            });
        };

  }])
    .controller('InvestigationController', ['$scope', '$rootScope', '$http', '$window', '$filter', '$uibModal', '$cookies', '$stateParams', 'QueryCache', 'DOAPI', 'FileReader', 'BOSH', 'boshConfig', 'notifications', function($scope, $rootScope, $http, $window, $filter, $uibModal, $cookies, $stateParams, QueryCache, DOAPI, FileReader, BOSH, bosh, notifications){
      /**
       * @fixme: move all BOSH stuff in the service
       * @todo: remove bosh callbacks from $rootScope
       */

    //$scope.search = 'cert.europa.eu,212.8.189.19';
      /*angular.forEach(bosh.rooms, function(val, key){
            if(val.split('@')[0] == $stateParams.room){
                $scope.currentRoom = val;
            }
        });
        console.log($scope.currentRoom);*/

    $scope.responses = [];
    $scope.responses_url = URL.createObjectURL(
      new Blob(
        [JSON.stringify(($scope.responses))],
        {type: "application/json;charset=utf-8"}
      )
    );
    var onPresence = function(presence){
      var from = $(presence).attr('from');
      if(Strophe.getBareJidFromJid(from) == bosh.rooms[0]){
        var nick = Strophe.getResourceFromJid(from);
        if(!bosh.participants[nick] && $(presence).attr('type') !== 'unavailable'){
          var user_jid = $(presence).find('item').attr('jid');
          bosh.participants[nick] = user_jid || true;
        }else if(bosh.participants[nick] && $(presence).attr('type') === 'unavailable'){
          delete bosh.participants[nick];
          $scope.$broadcast('user_left', nick);
        }
      }
      return true;
    };
    var onPublicMessage = function(msg){
      var from = $(msg).attr('from');
      var to = $(msg).attr('to');
      var nick = Strophe.getResourceFromJid(from);
      if(Strophe.getBareJidFromJid(from) == bosh.rooms[0]){
        var notice = !nick;
        //var body = $(msg).children('body').text();
        var ahevents = AHEvent.fromElements($(msg).children('event'));
        var delayed = $(msg).children("delay").length > 0  ||
          $(msg).children("x[xmlns='jabber:x:delay']").length > 0;
        if(!notice){
          //$log.debug($(msg).children('event'));
          if(!delayed){
            if(ahevents !== 'undefined' && ahevents.length > 0){
              var ahevent = ahevents[0];
              if(ahevent !== 'undefined'){
                $rootScope.$broadcast('new_response', ahevent, nick);
              }
            }
          }
        }
      }
      return true;
    };

    var joinRoom = function(room){
      console.log('Joining room '+room);
      bosh.connection.xmlOutput = function(elem){
        //BOSH.storeSessionData();
      };
      //bosh.connection.rawInput = DOAPI.logRawInput;
      //bosh.connection.rawOutput = DOAPI.logRawOutput;

      bosh.connection.nickname = bosh.connection.jid.split('/')[1];

      bosh.connection.send($pres().c('priority').t('-1'));
      bosh.connection.flush();

      bosh.connection.addHandler(onPresence, null, 'presence');
      bosh.connection.addHandler(onPublicMessage, null, 'message', 'groupchat');

      bosh.connection
        .send($pres({to: room + "/" + bosh.connection.nickname})
          .c('x', {xmlns: Strophe.NS.HTTPBIND})
        );
    };

    //if(bosh.connectionStatus === "Connected" && bosh.nickname == null){
    //    console.log('no nickname');
    //    joinRoom();
    //}

    try {
      bosh.connection.restore(bosh.connection.jid, function(){
      });
    } catch(e) {
      console.log(e);
      //if (e.name !== "StropheSessionError") { throw(e); }
      $http.get('/auth/bosh-session').then(
        function(resp){
          if(resp.status === 200){
            bosh.rooms = resp.data.rooms;
            /*angular.forEach(bosh.rooms, function(val, key){
                            if(val.split('@')[0] == $stateParams.room){
                                $scope.currentRoom = val;
                            }
                        });*/
            BOSH.attach(resp.data);
          }
        }, function(error){
          notifications.showError(error.statusText);
        }
      );
    }

    $scope.$on('new_response', function(e, event, from_nick){
      $scope.$apply(function(){
        var r = QueryCache.get(event.value('augment sha-1'));
        if(r){
          var queryHash = DOAPI.getAugmentKey(r.query);
          var existing = $filter('filter')($scope.responses, function(v, idx){
            return v.query_hash === queryHash;
          });
          //debugger;
          if(existing.length > 0){
            // append
            var reply = existing[0];
            if(reply.experts.hasOwnProperty(from_nick)){
              reply.experts[from_nick].push(event.items())
            }else{
              reply.experts[from_nick] = [event.items()];
            }
          }else{
            var reply = {
              query_hash: queryHash,
              query_string: r.query,
              experts: {}
            };
            reply.experts[from_nick] = [event.items()];
            $scope.responses.push(reply);
            $scope.responses_url = URL.createObjectURL(
              new Blob(
                [JSON.stringify(($scope.responses))],
                {type: "application/json;charset=utf-8"}
              )
            );
          }
        }

      });
    });

    $scope.$on('user_left', function(e, nick){
      console.debug('User left: ' + nick);
      //console.log(e, nick);
    });

    $rootScope.$on('bosh-connected', function(){
      console.log('bosh is connected');
    });

    $rootScope.$on('bosh-attached', function(){
      /*angular.forEach(bosh.rooms, function(val, key){
                joinRoom(val);
            });*/
      joinRoom(bosh.rooms[0]);
    });

    $scope.exportResponses = function(){
      var header = ['query', 'expert'].concat($filter('eventKeys')($scope.responses));
      var rv = [header];
      $scope.exportDate = new Date().getTime();
      angular.forEach($scope.responses, function(reply){
        angular.forEach(reply.experts, function(experts, nick){
          angular.forEach(experts, function(expert, k){
            var entry = [];
            for(var i=0;i<header.length;i++){
              entry[i] = "";
            }
            entry[0] = reply.query_string;
            entry[1] = nick;
            angular.forEach(expert, function(val, key){
              var keyIndex = header.indexOf(key);
              if(keyIndex !== -1){
                entry[keyIndex] = val.join();
              }

            });
            rv.push(entry);
          });

        });
      });
      return rv;
    };

    $scope.clearResponses = function(){
      $scope.responses = [];
    };

    $scope.getFile = function (file) {
      $scope.fileProgress = 0;
      FileReader.readAsText(file, $scope)
        .then(function (result) {
          var csv = result.split(/\r\n|\r|\n|,/g);
          $scope.search = csv.join(',');
        });
    };

    $scope.onSearch = function(){
      if(typeof $scope.search === "undefined" || $scope.search.length < 1){
        return;
      }
      $scope.responses = [];
      var values = $scope.search.split(new RegExp(",|\\s"));
      angular.forEach(values, function(v, k){
        var request = {id: DOAPI.getId()};
        var key = "host";
        var ere = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        var emailRegex = new RegExp(ere);
        var ipv4_rex = new RegExp("^([1-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])" +
          "(\.([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])){3}$");

        // /^[0-9a-f]{32}$/i  // MD5
        // /^[0-9a-f]{40}$/i  // SHA-1
        var md5Regex = new RegExp("^[0-9a-f]{32}(?:[0-9a-f]{8})?$");
        var sha1Regex = new RegExp('^[0-9a-f]{40}(?:[0-9a-f]{8})?$');
        var sha256Regex = new RegExp('^[0-9a-f]{64}(?:[0-9a-f]{8})?$');
        var sha512Regex = new RegExp('^[0-9a-f]{128}(?:[0-9a-f]{8})?$');
        if(ipv4_rex.test(v) === true){
          key = "ip";
        }else if(md5Regex.test(v.toLowerCase()) === true ||
          sha1Regex.test(v.toLowerCase()) === true ||
            sha256Regex.test(v.toLowerCase()) === true ||
            sha512Regex.test(v.toLowerCase()) === true){
              key = "hash";
            }else if(emailRegex.test(v.toLowerCase()) === true){
              key = 'email';
            }
        if(request[key]){
          request[key].push(v.toLocaleLowerCase());
        }else{
          request[key] = [v.toLocaleLowerCase()];
        }
        request[key].sort();

        var newEvent = new AHEvent(request);

        var request_str = "";
        var repr_str = "";
        var elength = newEvent._sortedAttrs().length;
        // no need to use AHEvents just for sorting
        // https://stackoverflow.com/questions/3423394/algorithm-of-javascript-sort-function
        newEvent._sortedAttrs().forEach(function(v, k){
          request_str += v + "\xc0";
          if(k % 2 == 0) {
            repr_str += v + "=";
          }else if(k == elength-1){
            repr_str += v;
          }else{
            repr_str += v + ", ";
          }

        });

        var query = {
          hash: DOAPI.getAugmentKey(request_str),
          query: request[key][0],
          id: request.id,
          timestamp: Date.now()
        };
        QueryCache.put(query.hash, query);
        var body = "!repr " + repr_str;
        bosh.connection.send(
          $msg({
            to: bosh.rooms[0],
            type: "groupchat"}).c('body').t(body)
        );
      });
    };

  }])
  .controller('PasswordController', ['$scope', '$http', 'notifications', function($scope, $http, notifications){
    $scope.change_password = function(){
      var changePassword = $http.post('/auth/change-password', $scope.credentials);
      changePassword.success(function(resp){
        notifications.showSuccess(resp);
      });
      changePassword.error(function(resp){
        notifications.showError(resp);
      });
      return changePassword;
    };
  }]);
