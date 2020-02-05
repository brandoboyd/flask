(function(){
  'use strict';
  angular.module('chat').controller('LandingPageCtrl',

  function ($scope,
            $rootScope,
            $q,
            $modal,
            $sce,
            socket, $http) {

    $scope.menus = [
      {
        title:'Mobile Devices',
        hasChild : true,
        target: '',
        submenus: [
          { 
            title:'Cell Phones', 
            target:'cellphones', 
            hasParent: true,
            items: [
              {
                title: 'iPhone 6',
                description: 'iPhone 6 isn t just bigger it s better in every way. A 4.7-inch Retina HD display. An A8 chip with 64-bit desktop-class architecture. A new 8MP iSight camera with Focus Pixels. The Touch ID fingerprint identity sensor. Faster LTE and Wi-Fi. Longer battery life. And iOS 8 and iCloud. All in a 6.9mm thin seamless design. The iPhone 6 comes in 16GB, 64GB & 128GB. Available in Space Gray, Silver, or Gold. (Subject to availability)',
                price: '$199.99',
                prices: [
                  {
                    plan: 'month',
                    price: '27.08',
                    sign: '$',
                    comment: 'Verizon EDGE',
                    selection: false
                  },
                  {
                    plan: 'year',
                    price: '199.99',
                    sign: '$',
                    comment: '2 Yr Contract',
                    selection: true
                  },
                  {
                    plan: 'full',
                    price: '649.99',
                    sign: '$',
                    comment: 'Full Price',
                    selection: false
                  }
                ],
                img: 'http://s7.vzw.com/is/image/VerizonWireless/apple-iphone-6-spacegray',
                thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/apple-iphone-6-spacegray?$acc-med$&fmt=jpeg'
              },
              {
                title: 'iPhone 6 Plus',
                description: 'iPhone 6 Plus isn t just bigger it s better in every way. A 5.5 inch Retina HD display. An A8 chip with 64 bit desktop class architecture. A new 8MP iSight camera with Focus Pixels and optical image stabilization. The Touch ID fingerprint identity sensor. Faster LTE and Wi Fi. Longer battery life. And iOS 8 and iCloud. All in a 7.1mm thin seamless design.  The iPhone 6 Plus comes in 16GB, 64GB & 128GB.  Available in Space Gray, Silver, or Gold.  (Subject to availability)',
                price: '$299.99',
                prices: [
                  {
                    plan: 'month',
                    price: '31.24',
                    sign: '$',
                    comment: 'Verizon EDGE',
                    selection: false
                  },
                  {
                    plan: 'year',
                    price: '299.99',
                    sign: '$',
                    comment: '2 Yr Contract',
                    selection: true
                  },
                  {
                    plan: 'full',
                    price: '749.99',
                    sign: '$',
                    comment: 'Full Price',
                    selection: false
                  }
                ],
                img: 'http://s7.vzw.com/is/image/VerizonWireless/apple-iphone-6-plus-spacegray',
                thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/apple-iphone-6-plus-spacegray?$acc-med$&fmt=jpeg'
              },
              {
                title: 'Galaxy S6',
                description: 'Reinvented from the outside in, the beautiful Samsung Galaxy S6 is more than a pretty face. Within the stunning metal and glass design, the 5.1-inch Quad HD Super AMOLED display lets content shine like never before. Quickly launch the camera by double tapping the Home button and use optical image stabilization to eliminate blurry photos and shaky videos. Hear natural-sounding calls with HD Voice/Video.* The Galaxy S6 comes in 32GB, 64GB, or 128GB and is available in Black Sapphire, White Pearl, and Gold Platinum. (Subject to Availability)',
                price: '$199.99',
                prices: [
                  {
                    plan: 'month',
                    price: '24.99',
                    sign: '$',
                    comment: 'Verizon EDGE',
                    selection: false
                  },
                  {
                    plan: 'year',
                    price: '199.99',
                    sign: '$',
                    comment: '2 Yr Contract',
                    selection: true
                  },
                  {
                    plan: 'full',
                    price: '599.99',
                    sign: '$',
                    comment: 'Full Price',
                    selection: false
                  }
                ],
                img: 'http://s7.vzw.com/is/image/VerizonWireless/Samsung_Galaxy_S6_Black',
                thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/Samsung_Galaxy_S6_Black?$acc-med$&fmt=jpeg'
              },
              {
                title: 'Nexus 6',
                description: 'There’s plenty to admire with the Nexus 6 by Motorola. Plenty of screen to see, with a 6-inch Quad HD display. Plenty of sound to hear, with dual front-facing speakers and immersive stereo sound. Plenty of power to multitask, with a fast quad-core processor. And plenty of time to do more, with long battery life and a Turbo Charger. The Nexus 6 comes in 32GB. Available in midnight blue.',
                price: '$199.99',
                prices: [
                  {
                    plan: 'month',
                    price: '24.99',
                    sign: '$',
                    comment: 'Verizon EDGE',
                    selection: false
                  },
                  {
                    plan: 'year',
                    price: '199.99',
                    sign: '$',
                    comment: '2 Yr Contract',
                    selection: true
                  },
                  {
                    plan: 'full',
                    price: '599.99',
                    sign: '$',
                    comment: 'Full Price',
                    selection: false
                  }
                ],
                img: 'http://s7.vzw.com/is/image/VerizonWireless/Motorola_Nexus_6',
                thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/Motorola_Nexus_6?$acc-med$&fmt=jpeg'
              }
            ]
          },
          { 
            title:'Tablets', 
            target:'tablets', 
            hasParent: true,
            items: [
              {
                title: 'iPad Air',
                description: 'iPad Air is 20 percent thinner and weighs just one pound, so it feels unbelievably light in your hand. It comes with a 9.7-inch Retina display, the A7 chip with 64-bit architecture, ultrafast wireless, powerful apps, and up to 10 hours of battery life. The iPad Air comes in 16GB, 32GB, 64GB & 128GB. Available in Space Gray or Silver. (Subject to availability)',
                price: '$429.99',
                prices: [
                  {
                    plan: 'month',
                    price: '22.08',
                    sign: '$',
                    comment: 'Verizon EDGE',
                    selection: false
                  },
                  {
                    plan: 'year',
                    price: '429.99',
                    sign: '$',
                    comment: '2 Yr Contract',
                    selection: true
                  },
                  {
                    plan: 'full',
                    price: '529.99',
                    sign: '$',
                    comment: 'Full Price',
                    selection: false
                  }
                ],
                img: 'http://s7.vzw.com/is/image/VerizonWireless/apple_ipad_air_spacegray',
                thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/apple_ipad_air_spacegray?$acc-med$&fmt=jpeg'
              }
            ]
          },
          { 
            title:'Accessories', 
            target:'accessories', 
            hasParent: true,
            items: [
              {
                title: 'LifeProof fre for iPhone 6 - Black',
                description: '',
                price: '$89.99',
                prices: [
                  {
                    plan: 'single',
                    price: '89.99',
                    sign: '$',
                    comment: '',
                    selection: true
                  }
                ],
                img: 'http://s7.vzw.com/is/image/VerizonWireless/lifeproof-fre-case-iphone6-black-77-50598-iset',
                thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/lifeproof-fre-case-iphone6-black-77-50598-iset?$200x200$&fmt=jpeg'
              }
            ]
          }
        ]
      },
      { 
        title:'Home Phone', 
        target:'homephone', 
        hasChild: false, 
        hasParent: false,
        items: [
          {
            title: 'Wireless Home Phone',
            description: 'Rethink your Home Phone Service. Wireless Home Phone offers you a reliable, portable, low–cost alternative to traditional home phone service using the Verizon Wireless network all while keeping your same number and home phone.',
            price: 'free',
            prices: [
              {
                plan: 'year',
                price: '0.00',
                sign: '$',
                comment: '2 Yr Contract',
                selection: true
              },
              {
                plan: 'full',
                price: '99.99',
                sign: '$',
                comment: 'Full Price',
                selection: false
              }
            ],
            img: 'http://s7.vzw.com/is/image/VerizonWireless/home_phone_connect_f256vw',
            thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/home_phone_connect_f256vw?$acc-med$&fmt=jpeg'
          }
        ]
      },
      { 
        title:'Internet', 
        target:'internet', 
        hasChild: false, 
        hasParent: false,
        items: [
          {
            title: 'Jetpack MiFi 6620L',
            description: '',
            price: '$49.99',
            prices: [
              {
                plan: 'year',
                price: '49.99',
                sign: '$',
                comment: '2 Yr Contract',
                selection: true
              },
              {
                plan: 'full',
                price: '199.99',
                sign: '$',
                comment: 'Full Price',
                selection: false
              }
            ],
            img: 'http://s7.vzw.com/is/image/VerizonWireless/Novatel_Jetpack_MiFi6620L',
            thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/Novatel_Jetpack_MiFi6620L?$acc-med$&fmt=jpeg'
          }
        ]
      },
      { 
        title:'Digital TV', 
        target:'digitaltv', 
        hasChild: false, 
        hasParent: false,
        items: [
          {
            title: 'Digital TV',
            description: '',
            price: '$429.99',
            prices: [
              {
                plan: 'month',
                price: '22.08',
                sign: '$',
                comment: 'Verizon EDGE',
                selection: false
              },
              {
                plan: 'year',
                price: '429.99',
                sign: '$',
                comment: '2 Yr Contract',
                selection: true
              },
              {
                plan: 'full',
                price: '529.99',
                sign: '$',
                comment: 'Full Price',
                selection: false
              }
            ],
            img: 'http://s7.vzw.com/is/image/VerizonWireless/Novatel_Jetpack_MiFi6620L',
            thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/Novatel_Jetpack_MiFi6620L?$acc-med$&fmt=jpeg'
          }
        ]
      },
      { 
        title:'Bundles', 
        target:'bundles', 
        hasChild: false, 
        hasParent: false,
        items: [
          {
            title: 'Verizon Qi Wireless Charging Stand',
            description: 'Cable-free charging',
            price: '$59.99',
            prices: [
              {
                plan: 'single',
                price: '59.99',
                sign: '$',
                comment: '',
                selection: true
              }
            ],
            img: 'http://s7.vzw.com/is/image/VerizonWireless/verizon-qi-wireless-charging-stand-iset-vzw3coil-wc',
            thumbnail: 'http://s7.vzw.com/is/image/VerizonWireless/verizon-qi-wireless-charging-stand-iset-vzw3coil-wc?$200x200$&fmt=jpeg'
          }
        ]
      },
      {
        title:'FAQ',
        target:'faq',
        hasChild: false,
        hasParent: false
      }
    ];

    $scope.landing = {
      config: {
        homeBanner: 'http://previews.123rf.com/images/paffy/paffy1302/paffy130200124/18162663-Closeup-of-happy-young-woman-showing-her-mobile-phone-and-gesturing-thumb-up-sign-Shallow-depth-of-f-Stock-Photo.jpg'
      }
    };

    $scope.currentMenu = 'cellphones';
    $scope.currentParentTarget = 'cellphones';
    $scope.category = null;

    $scope.tabs = [
      { title:'Product Info', url:'product-info.html' },
      { title:'Product Specification', url:'product-specification.html' },
      { title:'Product Review', url:'product-review.html' }
    ];

    $scope.searchFaqResults = [];
    $scope.queryVal = '';

    $scope.currentTab = '';

    $scope.token = null;
    $scope.channelID = '';  // FAQ channel

    $scope.isHome = true;
    $scope.isList = false;
    $scope.isFAQ = false;

    /**
     * Tab choosing
     * @param tab
     * @param $event
     */
    $scope.onClickMenu = function (menu, $event) {
      var action = "Clicked Category: '" + menu.title + "'";
      var journeyInfo = null;
      if (menu.title != 'FAQ') {
          journeyInfo = [{journey_type_name: 'Purchasing',
                          journey_stage_name: 'Inquiry'}]
      }


      $scope.sendCustomerAction(action, journeyInfo);
      if ($scope.joined) {
        socket.emit('send', {
          senderType: 2,
          from: $scope.userSession.id,
          message: action
        });
      }

      $scope.currentMenu = menu.target;

      if(menu.title === 'FAQ'){
        $scope.isFAQ = true;
      } else {
        $scope.category = menu;
        $scope.isFAQ = false;
      }

      if(menu.hasParent) {
        $scope.currentParentTarget = menu.target;
      }

      $scope.isList = true;
      $scope.isHome = false;
    };

    $scope.isActiveMenu = function(target, hasChild) {
      if(hasChild) {
        return $scope.currentMenu == $scope.currentParentTarget;
      } else {
        return target == $scope.currentMenu;
      }
    };

    /**
     * Tab choosing
     * @param tab
     * @param $event
     */
    $scope.onClickTab = function (tab, $event) {

      var action = "Clicked '" + tab.title + "'";

      $scope.sendCustomerAction(action);
      if ($scope.joined) {
        socket.emit('send', {
          senderType: 2,
          from: $scope.userSession.id,
          message: action
        });
      }

      $scope.currentTab = tab.url;
      /*
      socket.emit('getChatBoxArticle', {tpl: 'welcome'}, function(data) {
        $rootScope.articleContents = data;
      });
      */
      $rootScope.isExpanded = true;
    };

    $scope.isActiveTab = function(tabUrl) {
      return tabUrl == $scope.currentTab;
    };

    $rootScope.renderHtml = function (htmlCode) {
      return $sce.trustAsHtml('<div>' + htmlCode + '</div>');
    };

    $('.chatbox-article').on("click", "a", function(e){
      var type = $(this).data('href');

      if(type != undefined) {
        $rootScope.$apply(function(){
          socket.emit('getChatBoxArticle', {tpl: type}, function(data) {
            $rootScope.articleContents = data;
          });
        });
      }
    });

    $rootScope.showChatbox = function(){
      $rootScope.visible = true;
      $rootScope.isExpanded = true;
    };

    $scope.viewItem = function(item) {
      $scope.product = item;
      $scope.currentTab = 'product-info.html';

      $scope.isList = false;
      $scope.searchFaqResults = [];

      // set default price
      angular.forEach(item.prices, function(value, key) {
        if(value.selection) {
          $scope.product.selPricePlan = value;
        }
      });

      socket.emit('send', {
        senderType: 2,
        senderID: $scope.userSession.id,
        receiverID: $scope.agentID,
        message: "Clicked Product Page: '" + item.title + "'"
      });
    };

    $scope.toHome = function() {
      $scope.isHome = true;
      $scope.isList = false;
    };

    $scope.toList = function() {
      $scope.isHome = false;
      $scope.isList = true;
    };

    $scope.selectPricePlan = function(price) {
      $scope.product.selPricePlan = price;
    };

    $scope.findValue = function(enteredValue) {
      if(typeof enteredValue == 'undefined') {
        enteredValue = '';
      }
      if(enteredValue == '') {
        return false;
      }

      console.log("channelID :" + $scope.channelID);

      socket.emit('searchFaqChannel',
        {
          'channel': $scope.channelID,
          'token': $scope.token,
          'customer_id': $rootScope.customerId,
          'query': enteredValue
        },
        function(data) {
          console.log("GOT FAQ DATA ", data);
          $scope.searchFaqResults = data.list;

          if ($scope.searchFaqResults.length == 0) {
            socket.emit('customerInitialChatMessage', {
                          senderType: 1,
                          from: $rootScope.customerId,
                          message: enteredValue
                      }, function(done) {
                          $rootScope.startChatSession();
                          $timeout(function(){
                              $('#message').focus();
                          }, 500);
                      });
          }

          if (data.actions && data.actions.list.length > 0) {
              var bestAction = data.actions.list[0];
              if (bestAction.name !== 'Do Nothing') {
                  socket.emit('offerChatToCustomer', {
                      userId: $rootScope.customerId,
                      eventId: data.event.id,
                      actionId: bestAction.id,
                      customerId: $rootScope.customerId,
                      message: bestAction.name});
              }
          }

        }
      );

      var action = "Searched '" + enteredValue + "'";

      $scope.sendCustomerAction(action);
      if ($scope.joined) { // $rootScope variable
        socket.emit('send', {
          senderType: 2,
          from: $scope.userSession.id,
          message: action
        });
      }

      $scope.queryVal = enteredValue;

    };

    $scope.feedbackFaq = function(faqId, feedback, e) {
      socket.emit('feedbackFaqChannel',
        {
          'token': $scope.token,
          'faq_id': faqId,
          'query': $scope.queryVal,
          'value': feedback
        },
        function(data) {
          $(e.target).parents("li").remove();
        }
      );

      socket.emit('send', {
        senderType: 2,
        from: $scope.userSession.id,
        message: "Feedback: '" + $scope.queryVal + "' - " + feedback
      });
    };

    $scope.addToCart = function(product) {
      socket.emit('send', {
        senderType: 2,
        senderID: $scope.userSession.id,
        receiverID: $scope.agentID,
        message: "Clicked 'Add to cart': " + product.title
      });
    };

    $scope.showAccessories = function() {
      socket.emit('send', {
        senderType: 2,
        senderID: $scope.userSession.id,
        receiverID: $scope.agentID,
        message: "Clicked Accessories"
      });
    };

    $scope.showBundles = function() {
      socket.emit('send', {
        senderType: 2,
        senderID: $scope.userSession.id,
        receiverID: $scope.agentID,
        message: "Clicked Bundles"
      });
    };

    $scope.sendCustomerAction = function(action, journeyInfo) {
      socket.emit('webClickActions', {
        userId: $scope.userSession.id,
        action: action,
        journeyInfo: journeyInfo,
        userAcceptedChat: $scope.acceptedChat, // $rootScope variable
        isAnonymous: $rootScope.isAnonymous
      });
    }

    $scope.init = function() {
      $scope.category = $scope.menus[0].submenus[0];

      socket.emit('getToken', {}, function(data) {
        $scope.token = data.token;

        socket.emit('getChannels', {token: $scope.token}, function(data) {
          $scope.channelID = data.list[0].id;
        });
      });
    };

    $scope.init();

  })
    .controller('ChatAppCtrl',
        function ($scope,
                  $rootScope,
                  $window,
                  $http,
                  $q,
                  $modal,
                  $timeout,
                  socket,
                  useragent,
                  geolocation, AuthService, CustomerService) {
          $rootScope.customerId = $window.customerId;
          $rootScope.isAnonymous = $window.isAnonymous;
          $rootScope.messages = [];

          $scope.user = {}; //holds information about the current user
          $scope.rooms = []; //holds information about all rooms
          $rootScope.chat_offer_message = "Looking for help? Do you want to chat with an agent?";
          $rootScope.agentID = null; // holds socketId of the agent
          $scope.error = {};
          $scope.username = '';
          $rootScope.joined = false;
          $rootScope.acceptedChat = false;
          $rootScope.inviteModalShown = false;
          $rootScope.visible = false;
          $rootScope.collapsed = true;
          $scope.actions = [];

          var typing = false;
          var timeout  = undefined;
          var userNames = {
            0: 'Agent',
            1: 'Me',
            2: 'ChatBot',
            3: 'Supervisor'
          };

          $rootScope.surveyModalInstance = null;


          $scope.toggleChatbox = function() {
            $rootScope.isExpanded = !$rootScope.isExpanded;
          };

          $scope.toggleChatboxToExpand = function() {
            $rootScope.isExpanded = true;
          };

          $scope.endChatbox = function() {
            $rootScope.visible = false;

            var  myMessages = _.filter($scope.messages, {sender: 'Me'});
            if (myMessages.length >= 1) { // If the customer has not started chat yet, don't show survey modal.
              $rootScope.surveyModalInstance = $modal.open({
                templateUrl: 'app/templates/surveyModal.html',
                controller: 'surveyModalCtrl',
                size: ""
              });
            }

            socket.emit('leaveRoom', {
              userId: $scope.userSession.id,
              roomId: $scope.user.inroom
            }, function(err) {
              if (err) {
                console.log('[LEAVE ROOM] ERR! - ' + err);
              } else {
                console.log('[LEAVE ROOM] SUCCESS!');
                $scope.user.inroom = null;
                $rootScope.acceptedChat = false;
                $rootScope.joined = false;
              }
            });
          };

          socket.on('disconnect', function(){
            $scope.status = 'offline';
          });

          socket.on('connectingToSocketServer', function(data) {
            console.log('connectingToSocketServer');

            if ($scope.isAnonymous) {
              $rootScope.userSession = {
                id: $scope.customerId,
                name: 'Anonymous',
                sex: 'N/A',
                age: 'N/A',
                segment: 'N/A'
              }
              $scope.username = 'Anonymous';

              $scope.joinServer();
              $scope.status = "online";

            } else {
              $http.get('/customers/' + $scope.customerId)
                  .success(function (user) {
                    $rootScope.userSession = user;
                    $scope.username = user.name;
                    console.log('landing success');

                    $scope.joinServer();
                    $scope.status = data.status;
                  }).error(function () {
                    console.log('landing error');
                  });
            }
          });

          $scope.joinServer = function() {
            $scope.user.name = this.username;
            socket.emit('joinSocketServer', {
              userID: $rootScope.userSession.id,
              userName: $rootScope.userSession.customer_full_name,
              userSex: $rootScope.userSession.customer_gender,
              userAge: $rootScope.userSession.customer_age,
              userSegment: $rootScope.userSession.customer_segments,
              userType: 'customer'
            });
            $scope.error.join = '';
          };

          $scope.focus = function(bool) {
            $scope.focussed = bool;
          };

          $scope.typing = function(event, room) {
            function timeoutFunction() {
              typing = false;
              socket.emit('typing', {
                senderType: 1,
                isTyping: false,
                from: $rootScope.userSession.id,
                toRoom: room
              });
            }

            if (event.which !== 13) {
              if (typing === false && $scope.focussed && room !== null) {
                typing = true;
                socket.emit('typing', {
                  senderType: 1,
                  isTyping: true,
                  from: $rootScope.userSession.id,
                  toRoom: room
                });
                clearTimeout(timeout);
                timeout = setTimeout(timeoutFunction, 500);
              }
            }
          };

          socket.on('isTyping', function(data) {
            if (data.from != $rootScope.userSession.id) {
              $scope.typer = userNames[data.senderType];
              $scope.isTyping = data.isTyping;
            }
          });

          $scope.send = function() {
            if (typeof this.message === 'undefined' || (typeof this.message === 'string' && this.message.length === 0)) {
              $scope.error.send = 'Please enter a message';
            } else {
              socket.emit('send', {
                senderType: 1,
                from: this.userSession.id,
                message: this.message
              });
              $scope.message = '';
              $scope.error.send = '';
            }
          };

          $rootScope.startChatSession = function() {
            $scope.showChatbox();
            if (!$scope.joined) {
              $scope.joinRoom();
            }
          };

          $scope.joinRoom = function() {
            $rootScope.messages = [];
            $scope.error.create = '';
            $scope.message = '';
            socket.emit('joinRoom', {type: 'customer', token: $scope.token}, function(err, response) {
              if (err) {
                // Show error message while joining a room
              } else {
                $rootScope.joined = true;
                $scope.user.inroom = response.roomId;
              }
            });
          };

          socket.on('sendUserDetail', function(data) {
            console.log(data);
            $scope.user = data;
          });

          socket.on('listAvailableChatRooms', function(data) {
            console.log("AVAILABLE ROOMS", data);
            $scope.rooms.length = 0;
            angular.forEach(data, function(room, key) {
              $scope.rooms.push({name: room.name, id: room.id});
            });
            if ($scope.rooms.length > 0 && $rootScope.visible && !$rootScope.joined) {
              $scope.joinRoom();
            }
          });

          socket.on('sendChatMessage', function(data) {
            var message = {
                sender  : userNames[data.senderType],
                //from    : data.from,
                body    : data.message
            };
            if (data.senderType !== 2 || message.sender !== "ChatBot") {
              $scope.messages.push(message);
            }
          });

          socket.on('updateUserDetail', function(data) {
            console.log("USERS DETAILS!!!", data);

            angular.forEach(data, function(person) {
              if (person.userType === 'agent') {
                $rootScope.agentID = person.userID;
              }
            });

            var me = _.findWhere(data, {userID: $scope.customerId});
            if (!me) {
              $scope.user.inroom = null;
              $rootScope.joined = false;
              $rootScope.acceptedChat = false;
            }
          });

          socket.on('joinedSuccessfully', function() {
            var payload = {
              countrycode: '',
              device: ''
            };
            geolocation.getLocation().then(function(position) {
              return geolocation.getCountryCode(position);
            }).then(function(countryCode) {
              payload.countrycode = countryCode;
              return useragent.getUserAgent();
            }).then(function(ua) {
              return useragent.getIcon(ua);
            }).then(function(device) {
              payload.device = device;
              socket.emit('userDetails', payload);
            });
          });

          socket.on('sendChatMessageHistory', function(data) {
              angular.forEach(data, function (m) {
                var message = {
                  sender: userNames[m.senderType],
                  //from    : m.from,
                  body: m.message
                };
                //don't let ChatBot messages appear in Chat Box History
                if (data.senderType !== 2 || message.sender != "ChatBot") {
                  $scope.messages.push(message);
                }
              });
          });

          $rootScope.popupChatInvitation = function(message, isFeedback, feedbackData) {
              if($scope.acceptedChat || $rootScope.inviteModalShown) return;

              var modalInstance = $modal.open({
                  templateUrl: 'app/templates/offerChatModal.html',
                  controller: 'OfferChatModalCtrl'
              });
              $rootScope.chat_offer_message = message;
              $rootScope.inviteModalShown = true;
              modalInstance.result.then(function (modalData) {
                  var hasAccepted = modalData.accepted;
                  var initialMessage = modalData.message;
                  $rootScope.inviteModalShown = false;
                  $rootScope.acceptedChat = hasAccepted;
                  if (hasAccepted) {
                      socket.emit('customerInitialChatMessage', {
                          senderType: 1,
                          from: $scope.customerId,
                          message: initialMessage
                      }, function(done) {
                          $scope.startChatSession();
                          $timeout(function(){
                              $('#message').focus();
                          }, 500);
                      });
                  }
                  if (isFeedback) {
                      feedbackData.score = (hasAccepted) ? 1 : 0;
                      socket.emit('rateWebClickActions', feedbackData);
                  }
              }, function() {
                  $rootScope.inviteModalShown = false;
              });
          };


          socket.on('offerChatToCustomer', function(data) {
              if (data.userId === $scope.customerId && !$rootScope.visible) {
                 $scope.popupChatInvitation(data.message, true, data);
              }
          });

        })
    .controller('surveyModalCtrl', function ($scope, $rootScope, socket) {
          $scope.surveyModalInstance = $rootScope.surveyModalInstance;

          $scope.itemRates = [];

          $scope.surveys = {
            selVal: [],
            comment: ""
          };

          $scope.colorpicker = {
            options: {
              orientation: 'horizontal',
              range: 'min',
              start: function (event, ui) { },
              stop: function (event, ui) {
                var isRated = true;
                angular.forEach($scope.surveys.selVal, function(val, key) {
                  if(parseInt(val) < 0) {
                    isRated = false;
                  }
                });

                if(isRated) {
                  $scope.slidedRate = false;
                } else {
                  $scope.slidedRate = true;
                }

                $scope.$apply();
              }
            }
          };
          $scope.slidedRate = true;


          $scope.init = function() {

            var type = 'rate_';

            socket.emit('getToken', {}, function(data) {
                $scope.token = data.token;
              });

            socket.emit('getChatBoxArticle', {tpl: type}, function(data) {
              //$rootScope.articleContents = data;
              var html = '';
              data = eval(data);
              $scope.itemRates = [];

              angular.forEach(data, function(rate, key) {
                $scope.itemRates.push(rate);
                $scope.surveys.selVal.push(-1);
              });
            });
          };

          $scope.rateChatbox = function(){
            if($scope.surveys.selVal.length > 0) {
              socket.emit('sendRatingChatbox', {score: $scope.surveys.selVal}, function(data) {

              });

              var averageScore = 0;

              angular.forEach($scope.surveys.selVal, function(score, key){
                averageScore += score;
              });

              averageScore = Math.round(averageScore / $scope.surveys.selVal.length);

              var feedbackData = {
                reward: averageScore / 10,
                customer: $scope.userSession.id,
                agent: $scope.agentID,
                token: $scope.token
              };
              console.log("Sending CSAT feedback", feedbackData);
              socket.emit('sendCSATFeedback', feedbackData);

            }

            $rootScope.visible = false;

            $scope.surveyModalInstance.close();
          };

          $scope.cancel = function () {
            $scope.surveyModalInstance.dismiss('cancel');
          };

          $scope.init();
        })
    .controller('OfferChatModalCtrl', ['$scope', '$rootScope', '$modalInstance',
        function ($scope, $rootScope, $modalInstance) {
            $scope.close = function(hasAccepted, customerInitialMessage) {
                var data = {accepted: hasAccepted, message: customerInitialMessage}
                $modalInstance.close(data);
            }
        }]);

}());