var uuid = require('node-uuid');
var _ = require('underscore')._;
var http = require('http');
var unirest = require('unirest');
var Q = require('q');

var UserService = require('./server/services/users');
var PredictorService = require('./server/services/predictors');

module.exports = function (server, path, fs) {
    var io = require('socket.io').listen(server);
    var config = require('./config');
    var Room = require('./utils/room');
    var utils = require('./utils/utils');
    var purgatory = require('./utils/purge');
    var people = [];
    var rooms = {};
    var chatHistory = {};
    var chatHistoryCount = 10;
    var sessionIds = {};
    var customerInitialMessages = {};

    var Users = new UserService(config);
    var Predictors = new PredictorService(config);

    initialize();

    io.set('log level', 1);

    function initialize() {

        Users.authenticate()
            .then(function() {
                Predictors.setAuthToken(Users.getAuthToken());
                return Predictors.fetchAll();
            })
            .then(function() {
                return Users.fetchAllAgents();
            })
            .then(function() {
                io.sockets.on('connection', startSocketServer);
            })
            .catch(function(err) {
                console.log('---------- Error! (Chat server initialization) ----------');
            });
    }

    function startSocketServer(socket) {
        //on every connection count the number of people already online and broadcast message to all clients
        //console.log('CHAT SERVER HAS BEEN STARTED');
        totalPeopleOnline = _.size(people);
        utils.sendToAllConnectedClients(io, 'updatePeopleCount', {count: totalPeopleOnline});
        totalRooms = _.size(rooms);
        utils.sendToAllConnectedClients(io, 'updateRoomsCount', {count: totalRooms});

        utils.sendToSelf(socket, 'connectingToSocketServer', {status: 'online'});

        socket.on('joinSocketServer', function(data) {

            var person = _.findWhere(people, {userID: data.userID});

            if (person) {
                utils.pushUnique(person.socketIDs, socket.id);
            } else {
                var newPerson = {
                    userID: data.userID,
                    userName: data.userName,
                    userSex: data.userSex,
                    userAge: data.userAge,
                    userSegment: data.userSegment,
                    userType: data.userType,
                    socketIDs: [socket.id],
                    inroom: null,
                    owns: null
                };
                people.push(newPerson);
            }

            utils.sendToAllConnectedClients(io,'listAvailableChatRooms', _.where(rooms, {available: true}));
            utils.sendToSelf(socket, 'joinedSuccessfully'); //useragent and geolocation detection
            //utils.sendToAllConnectedClients(io, 'updateUserDetail', people);
        });

        socket.on('userDetails', function(data) {
            //update the people object with further user details
            var countryCode = data.countrycode.toLowerCase()
                , currentPerson = utils.findPersonBySocket(people, socket.id);
            if (currentPerson) {
                currentPerson.countrycode = countryCode;
                currentPerson.device = data.device;
                utils.pushUnique(currentPerson.socketIDs, socket.id);
                if (rooms[currentPerson.inroom]) {
                    utils.sendToAllClientsInRoom(io, rooms[currentPerson.inroom].name, 'updateUserDetail', _.where(people, {inroom: currentPerson.inroom}));
                }
                utils.sendToSelf(socket, 'sendUserDetail', currentPerson);
            }
        });

        socket.on('typing', function(data) {
            var currentPerson = utils.findPersonBySocket(people, socket.id);

            if (currentPerson) {

                var id = data.toRoom? data.toRoom: currentPerson.inroom;
                if (id) {
                    var roomToSend = _.findWhere(rooms, {id: id});
                    data.toRoom = id;
                    roomToSend && utils.sendToAllClientsInRoom(io, roomToSend.name, 'isTyping', data);
                }
            }
        });

        socket.on('send', function(data) {
            var currentPerson = utils.findPersonBySocket(people, socket.id);
            if (currentPerson) {
                var id = data.toRoom? data.toRoom: currentPerson.inroom;
                if (id) {
                    var roomToSend = _.findWhere(rooms, {id: id});
                    data.toRoom = id;
                    roomToSend && utils.sendToAllClientsInRoom(io, roomToSend.name, 'sendChatMessage', data); // Users might open multiple tabs for chat
                }
                if (io.sockets.manager.roomClients[socket.id]['/' + socket.room]) {
                    if (_.size(chatHistory[socket.room]) > chatHistoryCount) {
                        chatHistory[socket.room].splice(0, 1);
                    } else {
                        console.log("Data pushed to socket: ", data)
                        chatHistory[socket.room].push(data);
                    }

                } else {
                    utils.sendToSelf(socket, 'sendChatMessage', {
                        senderType: 2,
                        message: 'Please connect to a room'
                    });
                }
            }
        });

        socket.on('createRoom', function () {

            var currentPerson = utils.findPersonBySocket(people, socket.id), id;

            if (currentPerson === null || currentPerson.userType !== 'agent') {
                utils.sendToSelf(socket, 'sendChatMessage', {
                    senderType: 2,
                    message: 'No permission to create a room!'
                });
                return;
            }

            if (currentPerson.owns !== null) {
                id = currentPerson.owns;
                socket.room = rooms[id].name;
                socket.join(socket.room);
                utils.sendToSelf(socket, 'sendChatMessage', {
                    senderType: 2,
                    message: 'You are already an owner of a room.'
                });
                utils.sendToAllClientsInRoom(io, rooms[id].name, 'updateUserDetail', _.where(people, {inroom: id}));
                utils.sendToSelf(socket, 'sendChatMessageHistory', chatHistory[socket.room]);
                utils.sendToSelf(socket, 'sendUserDetail', currentPerson);
                return;
            }

            if (currentPerson.inroom !== null) {
                id = currentPerson.inroom;
                socket.room = rooms[id].name;
                socket.join(socket.room);
                utils.sendToSelf(socket, 'sendChatMessage', {
                    senderType: 2,
                    message: 'You are already in a room.'
                });
                utils.sendToSelf(socket, 'sendChatMessageHistory', chatHistory[socket.room]);
                return;
            }


            var roomName = utils.addSuffixNumber('room')
                , uniqueRoomID = uuid.v4() //guarantees uniquness of room
                , room = new Room(roomName, uniqueRoomID, currentPerson.userID);

            currentPerson.owns = uniqueRoomID; //set ownership of room
            currentPerson.inroom = uniqueRoomID; //assign user to room in people object
            currentPerson.roomname = roomName;

            room.addPerson(currentPerson);
            rooms[uniqueRoomID] = room;
            socket.room = roomName;
            socket.join(socket.room);
            totalRooms = _.size(rooms);
            utils.sendToAllConnectedClients(io, 'updateRoomsCount', {count: totalRooms});
            utils.sendToAllConnectedClients(io, 'listAvailableChatRooms', _.where(rooms, {available: true}));
            utils.sendToAllClientsInRoom(io, roomName, 'updateUserDetail', _.where(people, {inroom: uniqueRoomID}));
            utils.sendToSelf(socket, 'sendUserDetail', currentPerson);
            chatHistory[socket.room] = []; //initiate chat history

            console.log('"' + currentPerson.userName + '" has created a room [' + roomName + ']');
        });

        function getSessionId(customerId) {
            console.log("Fetching session for customer:", customerId);
            if (sessionIds[customerId]) {
                console.log("Found and returned existing session:", sessionIds[customerId]);
            } else {
                sessionIds[customerId] = customerId + Math.floor(Date.now() / 1000);
                console.log("Allocating session:", sessionIds[customerId]);
            }
            return sessionIds[customerId];
        };

        function resetSessionId(customerId) {
            delete sessionIds[customerId];
        };

        function joinRoom(roomToJoin, currentPerson, flag, cb) {
            console.log("SELECTED ROOM TO JOIN ", roomToJoin);

            if (currentPerson === null || currentPerson.userType === 'agent' || !roomToJoin) {
                if (cb) return cb('Cannot join a room!');
                return;
            }

            if (currentPerson.userID === roomToJoin.owner) {
                utils.sendToSelf(socket, 'sendChatMessage', {
                    senderType: 2,
                    message: 'You own this room, why join it? ;)'
                });
                flag = true;
            }

            if (!roomToJoin.available && currentPerson.userType != 'supervisor') {
                if (cb) return cb('Agent is currently not available!');
                return;
            }

            if (!flag) {
                socket.room = roomToJoin.name;
                socket.join(socket.room);
                roomToJoin.addPerson(currentPerson);
                roomToJoin.updateStatus(false);
                currentPerson.inroom = roomToJoin.id;
                currentPerson.roomname = roomToJoin.name;
                utils.sendToAllClientsInRoom(io, roomToJoin.name, 'updateUserDetail', _.where(people, {inroom: roomToJoin.id}));
                utils.sendToSelf(socket, 'sendUserDetail', currentPerson);
            }

            chatHistory[socket.room] = [];
            if (customerInitialMessages[currentPerson.userID]) {
                chatHistory[socket.room].push(customerInitialMessages[currentPerson.userID]['message_data']);
                console.log("PUSHING TO AGENT DATA ", customerInitialMessages[currentPerson.userID]);
                utils.sendToAllClientsInRoom(io, roomToJoin.name, 'updateInitialState',
                                             customerInitialMessages[currentPerson.userID]['event_data']);
            }

            if (socket.room && chatHistory[socket.room].length === 0) {
                utils.sendToSelf(socket, 'sendChatMessage', {
                    senderType: 2,
                    message: 'No chat history.'
                });
            } else {
                /*// filter the user related messages out of chat history
                 var messages = _.filter(chatHistory[socket.room], function(message) {
                 return (message.receiverID === currentPerson.userID || message.senderID === currentPerson.userID);
                 })
                 utils.sendToSelf(socket, 'sendChatMessageHistory', messages);*/
                utils.sendToSelf(socket, 'sendChatMessageHistory', chatHistory[socket.room]);
            }

            console.log('"' + currentPerson.userName + '" has joined to a room [' + roomToJoin.name + ']');
            utils.sendDiagnostics(io, people, rooms);
            if (cb) return cb(null, {roomId: roomToJoin.id});
        }

        socket.on('joinRoom', function (data, cb) {

            console.log("ROOMS", rooms);
            var currentPerson = utils.findPersonBySocket(people, socket.id)
                , flag = false;

            if (!currentPerson) {
                if (cb) return cb('Invalid user\'s socket');
                return;
            }

            var joinType = data['type'];
            delete data['type'];

            console.log("TRYING TO JOIN ROOM", joinType, data);
            if (joinType == 'customer') {

                Users
                    .fetchCustomerById(currentPerson.userID)

                    .then(function(res) {
                        var customer = res;
                        var agents = Users.getAllAgents();
                        var onlineAgentIds = _.pluck(rooms, 'owner');
                        agents = _.filter(agents, function(item) {
                            return onlineAgentIds.indexOf(item.id) > -1;
                        });

                        var actions = _.map(agents, function(agent) {
                            return {
                                action_id   : agent.id,
                                skill       : agent.agent_skillset,
                                age         : agent.agent_age,
                                //fluency     : 'good',
                                seniority   : agent.agent_seniority
                            }
                        });
                        var context = {
                            age         : customer.customer_age,
                            gender      : customer.customer_gender,
                            location    : customer.customer_location,
                            n_subs      : customer.customer_num_calls,
                            intention   : [],
                            seniority   : customer.customer_seniority
                        };

                        var postParams = {
                            actions: actions,
                            token: Users.getAuthToken(),
                            context: context
                        };

                        var event = customerInitialMessages[customer.id]['event_data'];
                        postParams.context.intention = event.summary.topics;

                        console.log("TRYING TO SCORE AGENTS: ", postParams);
                        return Predictors.score(postParams);
                    })

                    .then(function(scoredAgents) {
                        var sortedOwners = _.pluck(scoredAgents.list, 'id');
                        var agentAndRooms = _.map(rooms, function (room) {
                            return _.pick(room, 'owner', 'id', 'available');
                        });
                        var sortedRooms = agentAndRooms.sort(function (room) {
                            return sortedOwners.indexOf(room.owner)
                        });
                        var availableRooms = _.filter(sortedRooms, function (room) {
                            return room.available == true
                        });

                        var roomToJoin;
                        if (availableRooms.length > 0) {
                            roomToJoin = rooms[availableRooms[0]['id']];
                        } else if (sortedRooms.length > 0) {
                            roomToJoin = rooms[sortedRooms[0]['id']];
                        }
                        if (!roomToJoin) {
                            console.log("There are no open rooms.");
                        } else {
                            joinRoom(roomToJoin, currentPerson, flag, cb);
                        }
                    })

                    .catch(function(err) {
                        console.log('---------- Error! (Join Room) ----------');
                        console.log(err);
                    });
            } else {
                var roomToJoin = rooms[data['roomId']];
                joinRoom(roomToJoin, currentPerson, flag, cb);
            }

        });

        socket.on('deleteRoom', function (id) {
            var roomToDelete = rooms[id]; // find the room to remove?
            if (typeof roomToDelete !== 'undefined') {
                if (socket.id === roomToDelete.owner) { //only allow the owner to delete a room
                    purgatory.purge(socket, 'deleteRoom');
                } else {
                    utils.sendToSelf(socket, 'sendChatMessage', {
                        senderType: 2,
                        message: 'Don\'t be cheeky - you are not the owner of this room.'
                    });
                }
            }
        });

        /*socket.on('leaveRoom', function (id) {
            var roomToLeave = rooms[id];
            if (typeof roomToLeave !== 'undefined') {
                purgatory.purge(socket, 'leaveRoom');
            } else {
                utils.sendToSelf(socket, 'sendChatMessage', {
                    senderType: 2,
                    message: 'Don\'t be cheeky - you are not the owner of this room.'
                });
            }
        });*/

        socket.on('disconnect', function () {
            //purgatory.purge(socket, 'disconnect');
            var person = utils.findPersonBySocket(people, socket.id);
            if (person && rooms[person.inroom] && person.userType !== 'agent') {
                var roomToLeave = rooms[person.inroom];
                roomToLeave.updateStatus(true);
                roomToLeave.users = _.without(roomToLeave.users, _.findWhere(roomToLeave.users, {userID: person.userID}));

                // _.remove(people, {id: person.id}); // lodash
                people = _.without(people, _.findWhere(people, {userID: person.userID}));
                utils.sendToAllClientsInRoom(io, roomToLeave.name, 'updateUserDetail', _.where(people, {inroom: roomToLeave.id}));
                utils.sendToAllConnectedClients(io,'listAvailableChatRooms', _.where(rooms, {available: true}));
            }
            utils.sendDiagnostics(io, people, rooms);
        });

        socket.on('getChatBoxArticle', function (data, cb) {
            var tpl_path = path.join(__dirname, '/../../templates/chatbox/' + data.tpl + '.html');
            fs.exists(tpl_path, function (exists) {
                if (!exists)
                    fs.closeSync(fs.openSync(tpl_path, 'w'));

                fs.readFile(tpl_path, 'utf8', function (err, contents) {
                    if (err) throw err;
                    if (!contents) contents = "(empty)";
                    cb(contents);
                });
            });
        });

        socket.on('saveChatBoxArticle', function (data, cb) {
            var tpl_path = path.join(__dirname, '/../../templates/chatbox/' + data.tpl + '.html');

            fs.writeFile(tpl_path, data.contents, function (err) {

            });
        });

        socket.on('sendRatingChatbox', function(data) {
            var tpl_path = path.join(__dirname, '/../../templates/chatbox/rate_.html');
            var rate_contents = '';
            fs.exists(tpl_path, function (exists) {
                fs.readFile(tpl_path, 'utf8', function (err, contents) {
                    if (err) throw err;
                    rate_contents = contents;

                    rate_contents = eval(rate_contents);

                    for(var i=0; i<data.score.length; i++) {
                        rate_contents[i].rating[data.score[i]-1] += 1;
                        rate_contents[i].rating[10] += data.score[i];
                    }
                    fs.writeFile(tpl_path, JSON.stringify(rate_contents), function (err) {

                    });
                });
            });
        });

        socket.on('customerInitialChatMessage', function(data, cb) {
            console.log("customer initial chat data: ", data);
            var person = _.findWhere(people, {userType: 'supervisor'});
            resetSessionId(data.from);
            person && utils.sendToUserByID(io, person, 'customerInitialChatMessage', data, function(event) {
                console.log("GOT A NEW EVENT ", event.data);
                customerInitialMessages[data.from]['event_data'] = event.data.item;
                cb(true);
            });
            customerInitialMessages[data.from] = {'message_data': { senderType: 1,
                                                                    from: data.from,
                                                                    message: data.message },
                                                  'event_data': {}};
        });

        socket.on('getSessionId', function(customerId, cb) {
            cb(getSessionId(customerId));
        });

        socket.on('webClickActions', function(data) {
            console.log("actions on web clicks: ", data);
            var person = _.findWhere(people, {userType: 'supervisor'});
            person && utils.sendToUserByID(io, person, 'webClickActions', data);
        });

        socket.on('rateWebClickActions', function(data) {
            console.log("send feedback for next_best_action : ", data);
            var person = _.findWhere(people, {userType: 'supervisor'});
            person && utils.sendToUserByID(io, person, 'rateWebClickActions', data);
        })

        socket.on('offerChatToCustomer', function(data) {
            console.log('Offer chat to customer ' + data.userId)
            if (data.userId) {
                var person = utils.findPersonByID(people, data.userId);
                person && utils.sendToUserByID(io, person, 'offerChatToCustomer', data);
            }
        });

        socket.on('askToSupervisor', function(supervisorAlertData) {
            var person = utils.findPersonBySocket(people, socket.id);
            if (person) {
                console.log('askToSupervisor by ' + person.userName);
                var agentInfo = {
                    id: person.userID,
                    roomId: person.owns,
                    customer: supervisorAlertData['customer'],
                    alert_data: supervisorAlertData['alert_data']
                };
                utils.sendToAllConnectedClients(io, 'askToSupervisor', agentInfo);
            }
        });

        socket.on('notifySupervisor', function(data) {
            console.log("SU WAS NOTIFIED!", data)
            utils.sendToAllConnectedClients(io, 'notifySupervisor', data);
        })


        socket.on('leaveRoom', function(data, cb) {
            var currentUser = _.findWhere(people, {userID: data.userId});
            if (!currentUser) return cb('Failed to leave the room');

            var room = _.findWhere(rooms, {id: data.roomId});
            if (!room) return cb('Invalid room to leave');

            console.log('[LEAVE ROOM] ' + currentUser.userName);

            _.each(currentUser.socketIDs, function(id) {
                var sock = io.sockets.sockets[id];
                if (sock) {
                    sock.leave(room.name);
                }
            });

            delete customerInitialMessages[currentUser.userID];
            if (chatHistory.hasOwnProperty(room.name)) {
                chatHistory[room.name] = [];
            }

            currentUser.inroom = null;
            utils.sendToAllClientsInRoom(io, room.name, 'updateUserDetail', _.where(people, {inroom: room.id}));

            room.users = _.reject(room.users, function(e) { return e.userID == data.userId});
            room.updateStatus(true);
            return cb(null);
        })

        socket.on('resetAllCustomers', function() {
            sessionIds = {};
            chatHistory = {};
            customerInitialMessages = {};

            _.each(people, function(e) {
                if (e.userType == 'customer') {
                    e.inroom = null;
                }
            });
            //people = _.reject(people, function(person) { return person.userType === 'customer'; });

            _.each(rooms, function(room) {
                utils.sendToAllClientsInRoom(io, room.name, 'updateUserDetail', _.where(people, {inroom: room.id}));
                room.users = _.reject(room.users, function(user) { return user.userType === 'customer'; });
                room.updateStatus(true);
            });
            utils.sendToSelf(socket, 'resetFinished');
            utils.sendDiagnostics(io, people, rooms);
        });

        socket.on('sendDiagnostics', function() {
            utils.sendDiagnostics(io, people, rooms);
        })

        function createReq(paramString, method, path, cb) {

            var headers = {
              'Content-Type': 'application/json',
              'Content-Length': paramString.length
            };

            var options = {
              host: config.IP_ADDR,
              path: '/api/v2.0/' + path,
              method: method,
              headers: headers
            };

            if (config.ENV == 'development') {
                options.port = 5000;
            }

            // Setup the request.  The options parameter is
            // the object we defined above.
            var req = http.request(options, function(res) {
              res.setEncoding('utf-8');

              var responseString = '';

              res.on('data', function(data) {
                responseString += data;
              });

              res.on('end', function() {
                try {
                    var resultObject = JSON.parse(responseString);
                    cb(resultObject);
                } catch (e) {
                    console.error(e);
                }
              });
            });

            req.on('error', function(e) {
              // TODO: handle error.
            });

            req.write(paramString);
            req.end();
        }

        socket.on('getToken', function (data, cb) {
            //TODO: !!!
            var param = {
                username: 'super_user@solariat.com',
                password: 'password'
            };

            var paramString = JSON.stringify(param);

            createReq(paramString, 'POST', 'authenticate', cb);
        });

        socket.on('getChannels', function (data, cb) {

            var paramString = JSON.stringify(data);

            createReq(paramString, 'GET', 'channels/faq', cb);
        });

        socket.on('sendCSATFeedback', function (data, cb) {

            var predictor_id = Predictors.getAgentRouterId();
            if (!predictor_id) {
                return;
            }

            var url = 'predictors/' + predictor_id + '/feedback';

            Users.fetchCustomerById(data.customer)
                .then(function(customer) {
                    var agents = Users.getAllAgents();
                    var agent = _.findWhere(agents, { id: data.agent });

                    if (!agent) {
                        return;
                    }
                    var action = {
                        action_id   : agent.id,
                        skill       : agent.skill,
                        age         : agent.age,
                        fluency     : 'good',
                        seniority   : agent.seniority
                    };
                    var context = {
                        age         : customer.age,
                        gender      : customer.sex,
                        location    : customer.location,
                        n_subs      : customer.num_calls,
                        intention   : [],
                        seniority   : customer.seniority,
                    }

                    var postParams = {
                        action: action,
                        context: context,
                        token: data.token,
                        reward: data.reward,
                    };
                    var paramString = JSON.stringify(postParams);

                    console.log("CHAT SENDING CSAT FEEDBACK", postParams);
                    createReq(paramString, 'POST', url, cb);
                });
        });

        socket.on('searchFaqChannel', function (data, cb) {

            var paramString = JSON.stringify(data);

            createReq(paramString, 'POST', 'faq/search', cb);
        });

        socket.on('feedbackFaqChannel', function (data, cb) {

            var paramString = JSON.stringify(data);

            createReq(paramString, 'POST', 'faq/train', cb);
        });

    }
};