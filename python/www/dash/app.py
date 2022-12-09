#!/usr/bin/env python3
#
# Copyright (c) 2022, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the 'Software'),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

import dash
import http
import pprint

import warnings  # supress dash_auth import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import dash_auth

from dash import dcc, Input, Output
from dash.exceptions import PreventUpdate

from config import config, print_config
from server import Server

from layout import create_grid, create_navbar, create_stream_dialog, create_model_dialog

#import os
#print(f'loaded {__file__} module from {__name__} (pid {os.getpid()})')

# create the dash app
external_scripts = ['https://webrtc.github.io/adapter/adapter-latest.js']
external_stylesheets = [] #[dbc.themes.DARKLY] #[dbc.themes.SLATE] #[dbc.themes.FLATLY] #[dbc.themes.SUPERHERO] #['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, title=config['dash']['title'],
                external_scripts=external_scripts, 
                external_stylesheets=external_stylesheets, 
                suppress_callback_exceptions=True)
                
webserver = app.server

if len(config['dash']['users']) > 0:
    auth = dash_auth.BasicAuth(app, config['dash']['users'])

app.layout = dash.html.Div([
    create_navbar(),
    create_grid(),
    create_stream_dialog(),
    create_model_dialog(),
    dcc.Store(id='server_resources'),
    dcc.Interval(id='refresh_timer', interval=config['dash']['refresh'])
])

@app.callback(Output('server_resources', 'data'),
              Input('refresh_timer', 'n_intervals'),
              Input('server_resources', 'data'))
def on_refresh(n_intervals, previous_resources):
    """
    Get the latest resources config from the server.
    This can trigger updates to the clientside nav structure.
    """
    try:
        # retry later when other longer-running RPC requests are in-flight
        server_resources = Server.instance.list_resources()
    except http.client.CannotSendRequest as error:
        print(f'[dash]   error refreshing server resources:  http.client.CannotSendRequest {error}')
        raise PreventUpdate

    if previous_resources is not None:
        if server_resources == previous_resources:
            raise PreventUpdate   # if the config hasn't changed, skip the update

    print(f'[dash]   received updated resources config from backend server:')
    pprint.pprint(server_resources, indent=4)
    return server_resources


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(epilog="see config.py or data/config.json for more settings")
    
    parser.add_argument("--host", default=None, type=str, help="interface for the webserver to use (default is all interfaces, 0.0.0.0)")
    parser.add_argument("--port", default=None, type=int, help="port used for webserver (default is 8050)")
    parser.add_argument("--ssl-cert", default=None, type=str, help="path to PEM-encoded SSL/TLS certificate file for enabling HTTPS")
    parser.add_argument("--ssl-key", default=None, type=str, help="path to PEM-encoded SSL/TLS key file for enabling HTTPS")
    parser.add_argument("--resources", default=None, type=str, help="path to JSON config file to load initial server resources from")
    
    args = parser.parse_args()

    if args.host:
        config['dash']['host'] = args.host
        
    if args.port:
        config['dash']['port'] = args.port

    if args.ssl_cert:
        config['server']['ssl_cert'] = args.ssl_cert
        
    if args.ssl_key:
        config['server']['ssl_key'] = args.ssl_key
        
    if args.resources:
        config['server']['resources'] = args.resources
        
    print_config(config)
    
    # check if HTTPS/SSL requested
    ssl_context = None
    
    if config['server']['ssl_cert'] and config['server']['ssl_key']:
        ssl_context = (config['server']['ssl_cert'], config['server']['ssl_key'])
        
    # start the backend server
    Server(**config['server']).start()

    # disable code reloading because it starts the app multiple times (https://dash.plotly.com/devtools)
    # https://community.plotly.com/t/dash-multi-page-app-functions-are-called-twice-unintentionally/46450
    app.run_server(host=config['dash']['host'], port=config['dash']['port'], ssl_context=ssl_context, debug=True, use_reloader=False)

else:
    # gunicorn instance
    # start/connect to the backend server
    Server(**config['server']).connect()