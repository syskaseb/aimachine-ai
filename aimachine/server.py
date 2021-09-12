import json
import multiprocessing
import random
from typing import Dict, List
import numpy as np

import flask
import websocket

APP = flask.Flask(__name__)

WEBSOCKET_CLIENTS: List[websocket.WebSocketApp] = []
PROCESSES: Dict[websocket.WebSocketApp, multiprocessing.Process] = {}
TICTACTOE_URL = 'ws://localhost:8080/games/tictactoe'
GAME_IDS: Dict[websocket.WebSocket, str] = {}
CLIENT_IDS: Dict[websocket.WebSocket, str] = {}
BOARDS: Dict[websocket.WebSocket, np.ndarray] = {}
BLANK_VALUE = 0


@APP.route("/")
def health_check():
    return "<h1>Greetings from Aimachine AI!</h1>", 200


def on_open(ws):
    print("client socket open")
    BOARDS[ws] = BLANK_VALUE * np.zeros((3, 3), int)


def on_message(ws: websocket.WebSocket, event: str):
    data = json.loads(event)
    event_type = data['eventType']
    event_message = data['eventMessage']
    print('event message: ' + event_message)
    if event_type == 'game_id':
        GAME_IDS[ws] = event_message
    elif event_type == 'client_id':
        CLIENT_IDS[ws] = event_message
    elif event_type == 'field_to_be_marked':
        field_data = json.loads(event_message)
        row_index = field_data['rowIndex']
        col_index = field_data['colIndex']
        field_token = field_data['fieldToken']
        print('rowIndex, colIndex: {}-{}'.format(row_index, col_index))
        BOARDS[ws][row_index, col_index] = field_token

    elif event_type == 'movement_allowed':
        if event_message == CLIENT_IDS[ws]:
            row_indices, col_indices = np.where(BOARDS[ws] == BLANK_VALUE)
            free_pairs = list(zip(row_indices, col_indices))
            field_to_click = random.choice(free_pairs)
            data_to_send = json.dumps({
                'eventType': 'field_clicked',
                'eventMessage': {
                    'gameId': GAME_IDS[ws],
                    'rowIndex': str(field_to_click[0]),
                    'colIndex': str(field_to_click[1])
                }
            })
            ws.send(data_to_send)
    elif event_type == 'server_message':
        print(event_message)
    else:
        print('unhandled message occurred')


def on_error(ws, error):
    print('error: '.format(error))


def on_close(ws, close_status_code, close_msg):
    print("client socket closed")
    PROCESSES[ws].terminate()


def create_ws(ws):
    ws.run_forever()


@APP.route("/tictactoe")
def connect_computer_player():
    websocket.enableTrace(True)
    client = websocket.WebSocketApp(TICTACTOE_URL,
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
    WEBSOCKET_CLIENTS.append(client)
    process_name = 'ws_{}'.format(WEBSOCKET_CLIENTS.index(client))
    print('process name: {}'.format(process_name))
    process = multiprocessing.Process(name=process_name, target=create_ws, args=(client,), daemon=True)
    process.start()
    PROCESSES[client] = process
    return "AI client created", 201


if __name__ == '__main__':
    APP.run(host='0.0.0.0', port=8081, debug=False)
