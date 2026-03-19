// Конфигурация
const WS_URL = 'ws://localhost:8001/ws';
const API_URL = 'http://localhost:8001';
const PUBLIC_URL = 'http://192.168.1.52:8082/public.html'; // ваш IP
// Состояние приложения
let board = null;
let game = new Chess();
let socket = null;
let $board = $('#board');
let $moveList = $('#moveList');
let $connectionStatus = $('#connectionStatus');
let $moveInput = $('#moveInput');
let $sendMoveBtn = $('#sendMoveBtn');
let $startNewGameBtn = $('#startNewGameBtn');
let $downloadPgnBtn = $('#downloadPgnBtn');
let $lichessLink = $('#lichessLink');
let $broadcastStatus = $('#broadcastStatus');
let broadcastUrl = null;

// Инициализация при загрузке
$(document).ready(function() {
    initBoard();
    initWebSocket();
    initEventListeners();
    generateQRCode();
    checkServerStatus();
});

// Проверка статуса сервера
function checkServerStatus() {
    fetch(`${API_URL}/`)
        .then(response => response.json())
        .then(data => {
            console.log('Сервер работает:', data);
            if (data.lichess_integration) {
                console.log('✅ Lichess интеграция доступна');
            }
        })
        .catch(error => {
            console.error('Сервер не доступен:', error);
            alert('Ошибка подключения к серверу! Убедитесь, что сервер запущен на порту 8000');
        });
}

// Инициализация шахматной доски
function initBoard() {
    var config = {
        draggable: true,
        position: 'start',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd,
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
    };
    board = Chessboard('board', config);
    
    // Адаптация размера под контейнер
    $(window).resize(board.resize);
}

// Проверка, можно ли двигать фигуры
function onDragStart(source, piece, position, orientation) {
    // Не даем двигать фигуры если игра не начата
    if (!game) return false;
    
    // Ограничиваем, чтобы двигать можно было только фигуры текущей стороны
    if (game.turn() === 'w' && piece.search(/^b/) !== -1) return false;
    if (game.turn() === 'b' && piece.search(/^w/) !== -1) return false;
    
    // Не даем двигать если игра окончена
    if (game.game_over()) return false;
}

// Обработка отпускания фигуры
function onDrop(source, target) {
    // Пытаемся сделать ход
    var move = game.move({
        from: source,
        to: target,
        promotion: 'q' // Всегда превращаем в ферзя для простоты
    });

    // Если ход нелегальный, возвращаем фигуру обратно
    if (move === null) return 'snapback';
    
    // Отправляем ход на сервер
    sendMoveToServer(source + target);
    
    // Обновляем историю ходов
    updateMoveHistory();
}

// После завершения анимации обновляем позицию
function onSnapEnd() {
    board.position(game.fen());
}

// WebSocket подключение
function initWebSocket() {
    socket = new WebSocket(WS_URL);
    
    socket.onopen = function() {
        console.log('✅ WebSocket подключен');
        updateConnectionStatus(true);
        // Отправляем ping каждые 30 секунд для поддержания соединения
        setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send('ping');
            }
        }, 30000);
    };
    
    socket.onclose = function() {
        console.log('❌ WebSocket отключен');
        updateConnectionStatus(false);
        // Пытаемся переподключиться через 3 секунды
        setTimeout(initWebSocket, 3000);
    };
    
    socket.onerror = function(error) {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
    };
    
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleIncomingMessage(data);
    };
}

// Обработка входящих сообщений
function handleIncomingMessage(data) {
    console.log('Получено сообщение:', data);
    
    switch(data.type) {
        case 'init':
            // Инициализация состояния
            game.load(data.fen);
            board.position(data.fen);
            if (data.moves) {
                updateMoveHistory(data.moves);
            }
            if (data.broadcast_url) {
                broadcastUrl = data.broadcast_url;
                updateBroadcastLink();
            }
            break;
            
        case 'move':
            // Получен новый ход от сервера
            try {
                game.move(data.move);
                board.position(game.fen());
                addMoveToHistory(data.move);
            } catch(e) {
                console.error('Error applying move:', e);
            }
            break;
            
        case 'new_game':
            // Начало новой партии
            game.reset();
            board.start();
            $moveList.empty();
            if (data.broadcast_url) {
                broadcastUrl = data.broadcast_url;
                updateBroadcastLink();
            }
            break;
    }
}

// Отправка хода на сервер (через REST API)
function sendMoveToServer(moveUci) {
    fetch(`${API_URL}/move`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            move: moveUci,
            from_camera: false 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('✅ Ход отправлен:', data);
            if (data.lichess_sent) {
                console.log('✅ Ход также отправлен в Lichess');
            }
            if (data.is_game_over) {
                setTimeout(() => {
                    alert(`Игра окончена! ${data.result || 'Ничья'}`);
                }, 100);
            }
        } else {
            console.error('❌ Ошибка:', data);
            alert('Ошибка: ' + data.message);
            // Откатываем ход на доске
            game.undo();
            board.position(game.fen());
        }
    })
    .catch(error => {
        console.error('Error sending move:', error);
        alert('Ошибка отправки хода');
        // Откатываем ход на доске
        game.undo();
        board.position(game.fen());
    });
}

// Обновление статуса подключения
function updateConnectionStatus(connected) {
    const $dot = $connectionStatus.find('.dot');
    if (connected) {
        $dot.removeClass().addClass('dot connected');
        $connectionStatus.find('span:last').text(' Подключено к серверу');
    } else {
        $dot.removeClass().addClass('dot');
        $connectionStatus.find('span:last').text(' Отключено от сервера');
    }
}

// Обновление ссылки на трансляцию
function updateBroadcastLink() {
    if (broadcastUrl) {
        $lichessLink.attr('href', broadcastUrl).show();
        $broadcastStatus.text('Трансляция активна').css('color', '#28a745');
    } else {
        $lichessLink.hide();
        $broadcastStatus.text('Трансляция не создана').css('color', '#dc3545');
    }
}

// Обновление списка ходов
function updateMoveHistory(moves) {
    $moveList.empty();
    const movesToShow = moves || game.history();
    movesToShow.forEach((move, index) => {
        addMoveToHistory(move, index);
    });
}

// Добавление одного хода в историю
function addMoveToHistory(move, index) {
    const moveNumber = Math.floor(index/2) + 1;
    const isWhite = index % 2 === 0;
    
    let $moveItem = $('<div>').addClass('move-item');
    
    if (isWhite) {
        $moveItem.html(`${moveNumber}. ${move}`);
        $moveList.append($moveItem);
    } else {
        // Обновляем предыдущий пункт, добавляя черный ход
        let lastItem = $moveList.children().last();
        if (lastItem.length) {
            lastItem.html(lastItem.text() + ` ${move}`);
        } else {
            // Если почему-то нет предыдущего хода
            $moveItem.html(`... ${move}`);
            $moveList.append($moveItem);
        }
    }
    
    // Подсвечиваем новый ход
    $moveList.children().last().css('animation', 'none');
    setTimeout(() => {
        $moveList.children().last().css('animation', 'moveHighlight 1s ease-out');
    }, 10);
    
    // Прокручиваем вниз
    $moveList.scrollTop($moveList[0].scrollHeight);
}

// Генерация QR-кода
function generateQRCode() {
    const qrcodeContainer = document.getElementById('qrcode');
    if (qrcodeContainer) {
        QRCode.toCanvas(qrcodeContainer, 'https://omsk.travel', {
            width: 150,
            margin: 1,
            color: {
                dark: '#003366',
                light: '#ffffff'
            }
        }, function(error) {
            if (error) console.error('QR Code error:', error);
        });
    }
}

// Инициализация обработчиков событий
function initEventListeners() {
    // Отправка хода из текстового поля
    $sendMoveBtn.on('click', function() {
        const moveUci = $moveInput.val().trim();
        if (moveUci) {
            sendMoveToServer(moveUci);
            $moveInput.val('');
        } else {
            alert('Введите ход в формате UCI (например, e2e4)');
        }
    });
    
    // Enter в поле ввода
    $moveInput.on('keypress', function(e) {
        if (e.which === 13) {
            $sendMoveBtn.click();
        }
    });
    
    // Новая партия
    $startNewGameBtn.on('click', function() {
        const white = prompt('Имя белых (Губернатор Омской области):', 'Губернатор Омской области') || 'Губернатор Омской области';
        const black = prompt('Имя черных (Соперник):', 'Соперник') || 'Соперник';
        
        fetch(`${API_URL}/start-game`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                white: white,
                black: black,
                broadcast_name: `ПМЭФ-2026: ${white} vs ${black}`
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                game.reset();
                board.start();
                $moveList.empty();
                
                if (data.lichess_url) {
                    broadcastUrl = data.lichess_url;
                    updateBroadcastLink();
                    alert(`✅ Трансляция создана!\nСсылка: ${data.lichess_url}`);
                } else {
                    broadcastUrl = null;
                    updateBroadcastLink();
                }
            }
        })
        .catch(error => {
            console.error('Error starting game:', error);
            alert('Ошибка при создании новой партии');
        });
    });
    
    // Скачать PGN
    $downloadPgnBtn.on('click', function() {
        fetch(`${API_URL}/pgn`)
            .then(response => response.json())
            .then(data => {
                const blob = new Blob([data.pgn], { type: 'text/plain' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `omsk-chess-${new Date().toISOString().slice(0,10)}.pgn`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                console.log('PGN headers:', data.headers);
            })
            .catch(error => {
                console.error('Error downloading PGN:', error);
                alert('Ошибка при скачивании PGN');
            });
    });
    
    // Скрываем ссылку на Lichess при загрузке
    $lichessLink.hide();
}

// Добавляем обработку ошибок глобально
window.onerror = function(msg, url, line, col, error) {
    console.error('Глобальная ошибка:', {msg, url, line, col, error});
    return false;
};
